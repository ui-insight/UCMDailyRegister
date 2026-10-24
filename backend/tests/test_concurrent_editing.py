"""Tests for stale saves and late AI results (#406).

Two editors can work from the same view, and an AI edit can finish long after
it started. Neither may silently replace newer staff work or an approval.
"""

import asyncio

import pytest
from httpx import AsyncClient

from tests.conftest import TestSession, make_submission_data
from tests.test_ai_edits import SuccessfulProvider


async def _new_submission(client: AsyncClient, headers: dict[str, str]) -> str:
    resp = await client.post("/api/v1/submissions/", json=make_submission_data(), headers=headers)
    assert resp.status_code == 201
    return resp.json()["Id"]


async def _detail(client: AsyncClient, headers: dict[str, str], submission_id: str) -> dict:
    return (await client.get(f"/api/v1/submissions/{submission_id}", headers=headers)).json()


async def _save(
    client: AsyncClient,
    headers: dict[str, str],
    submission_id: str,
    text: str,
    base: str | None,
    approve: bool = False,
):
    return await client.post(
        f"/api/v1/ai-edits/{submission_id}/finalize",
        json={
            "Headline": f"{text} headline",
            "Body": f"{text} body",
            "Approve_For_Newsletter": approve,
            "Base_Staff_Revision_Id": base,
        },
        headers=headers,
    )


async def _versions(client: AsyncClient, headers: dict[str, str], submission_id: str) -> list[dict]:
    return (await client.get(f"/api/v1/ai-edits/{submission_id}/versions", headers=headers)).json()


@pytest.mark.asyncio
class TestStaleSaves:
    async def test_second_editor_saving_from_an_old_view_gets_a_conflict(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission_id = await _new_submission(client, staff_headers)
        loaded = (await _detail(client, staff_headers, submission_id))["Staff_Revision_Id"]
        assert loaded is None

        first = await _save(client, staff_headers, submission_id, "Editor A", base=loaded)
        assert first.status_code == 200

        stale = await _save(client, staff_headers, submission_id, "Editor B", base=loaded)
        assert stale.status_code == 409
        detail = stale.json()["detail"]
        assert detail["Current_Revision"] == {
            "Id": first.json()["Id"],
            "Headline": "Editor A headline",
            "Body": "Editor A body",
            "Approved": False,
        }
        bodies = [v["Body"] for v in await _versions(client, staff_headers, submission_id)]
        assert "Editor B body" not in bodies

        # After reloading, Editor B can deliberately save over A's revision.
        reloaded = (await _detail(client, staff_headers, submission_id))["Staff_Revision_Id"]
        assert reloaded == first.json()["Id"]
        retry = await _save(client, staff_headers, submission_id, "Editor B", base=reloaded)
        assert retry.status_code == 200

    async def test_stale_draft_cannot_clear_a_newer_approval(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission_id = await _new_submission(client, staff_headers)
        approved = await _save(client, staff_headers, submission_id, "Approved", base=None, approve=True)
        assert approved.status_code == 200

        stale = await _save(client, staff_headers, submission_id, "Old view draft", base=None)
        assert stale.status_code == 409
        assert stale.json()["detail"]["Current_Revision"]["Approved"] is True

        detail = await _detail(client, staff_headers, submission_id)
        assert detail["Status"] == "approved"
        assert detail["Approved_Version_Id"] == approved.json()["Id"]

    async def test_clients_that_send_no_base_are_not_checked(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission_id = await _new_submission(client, staff_headers)
        for text in ("One", "Two"):
            resp = await client.post(
                f"/api/v1/ai-edits/{submission_id}/finalize",
                json={"Headline": text, "Body": f"{text} body"},
                headers=staff_headers,
            )
            assert resp.status_code == 200


class BlockingProvider(SuccessfulProvider):
    """Holds the first model call until the test releases it."""

    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def complete_json(self, *args, **kwargs):
        self.started.set()
        await self.release.wait()
        return await super().complete_json(*args, **kwargs)


async def _run_ai_in_background(submission_id: str, provider: BlockingProvider, monkeypatch):
    from app.services import ai_edit_service as ai_edits

    monkeypatch.setattr(ai_edits, "get_llm_provider", lambda settings: provider)

    async def run():
        async with TestSession() as session:
            return await ai_edits.run_edit(session, submission_id, "tdr")

    task = asyncio.create_task(run())
    await asyncio.wait_for(provider.started.wait(), timeout=5)
    return task


@pytest.mark.asyncio
class TestLateAIResults:
    async def test_ai_finishing_after_approval_keeps_the_approval(
        self, client: AsyncClient, staff_headers: dict[str, str], monkeypatch
    ):
        submission_id = await _new_submission(client, staff_headers)
        provider = BlockingProvider()
        ai_task = await _run_ai_in_background(submission_id, provider, monkeypatch)

        approved = await _save(client, staff_headers, submission_id, "Approved", base=None, approve=True)
        assert approved.status_code == 200
        provider.release.set()
        result = await asyncio.wait_for(ai_task, timeout=5)

        detail = await _detail(client, staff_headers, submission_id)
        assert detail["Status"] == "approved"
        assert detail["Approved_Version_Id"] == approved.json()["Id"]
        assert detail["Working_Version_Id"] == approved.json()["Id"]
        types = [v["Version_Type"] for v in await _versions(client, staff_headers, submission_id)]
        assert "ai_suggested" in types  # the suggestion is kept as history
        assert result.Edit_Version_Id != approved.json()["Id"]

    async def test_ai_finishing_after_a_draft_keeps_the_item_in_review(
        self, client: AsyncClient, staff_headers: dict[str, str], monkeypatch
    ):
        submission_id = await _new_submission(client, staff_headers)
        provider = BlockingProvider()
        ai_task = await _run_ai_in_background(submission_id, provider, monkeypatch)

        draft = await _save(client, staff_headers, submission_id, "Draft", base=None)
        assert draft.status_code == 200
        provider.release.set()
        await asyncio.wait_for(ai_task, timeout=5)

        detail = await _detail(client, staff_headers, submission_id)
        assert detail["Status"] == "in_review"
        assert detail["Staff_Revision_Id"] == draft.json()["Id"]

    async def test_ai_on_a_new_submission_still_marks_it_ai_edited(
        self, client: AsyncClient, staff_headers: dict[str, str], monkeypatch
    ):
        submission_id = await _new_submission(client, staff_headers)
        provider = BlockingProvider()
        ai_task = await _run_ai_in_background(submission_id, provider, monkeypatch)
        provider.release.set()
        await asyncio.wait_for(ai_task, timeout=5)

        assert (await _detail(client, staff_headers, submission_id))["Status"] == "ai_edited"

    async def test_ai_result_does_not_change_the_staff_revision_token(
        self, client: AsyncClient, staff_headers: dict[str, str], monkeypatch
    ):
        submission_id = await _new_submission(client, staff_headers)
        draft = await _save(client, staff_headers, submission_id, "Draft", base=None)
        provider = BlockingProvider()
        ai_task = await _run_ai_in_background(submission_id, provider, monkeypatch)
        provider.release.set()
        await asyncio.wait_for(ai_task, timeout=5)

        # An editor who loaded before the AI result can still save normally.
        resp = await _save(client, staff_headers, submission_id, "Next", base=draft.json()["Id"])
        assert resp.status_code == 200
