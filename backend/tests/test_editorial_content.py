"""Tests for the authoritative-revision rules (#405).

The Editor, newsletter assembly and Word export must all use the revision
staff approved, regardless of version timestamps or later scheduling changes.
"""

import io
from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa
from docx import Document
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edit_history import EditVersion
from app.models.section import NewsletterSection
from app.models.submission import Submission
from app.services.editorial_content import publishable_text, working_revision
from tests.conftest import TestSession, make_submission_data
from tests.test_ai_edits import SuccessfulProvider, wait_for_task

T0 = datetime(2026, 10, 1, 9, 0, 0)


def _version(id_: str, version_type: str, minutes: int = 0) -> EditVersion:
    return EditVersion(
        Id=id_,
        Version_Type=version_type,
        Headline=f"{id_} headline",
        Body=f"{id_} body",
        Created_At=T0 + timedelta(minutes=minutes),
    )


def _submission(*versions: EditVersion, approved: str | None = None) -> Submission:
    submission = Submission(
        Original_Headline="Submitted headline",
        Original_Body="Submitted body",
        Approved_Version_Id=approved,
    )
    submission.Edit_Versions = list(versions)
    return submission


class TestWorkingRevision:
    def test_no_versions_publishes_the_submitted_text(self):
        submission = _submission()
        assert working_revision(submission) is None
        assert publishable_text(submission) == ("Submitted headline", "Submitted body", None)

    def test_approved_revision_beats_newer_finals_and_ai(self):
        submission = _submission(
            _version("approved", "editor_final", minutes=1),
            _version("newer-final", "editor_final", minutes=2),
            _version("newer-ai", "ai_suggested", minutes=3),
            approved="approved",
        )
        assert working_revision(submission).Id == "approved"
        assert publishable_text(submission) == ("approved headline", "approved body", "approved")

    def test_staff_final_beats_newer_ai_suggestion(self):
        submission = _submission(
            _version("final", "editor_final", minutes=1),
            _version("ai", "ai_suggested", minutes=5),
        )
        assert working_revision(submission).Id == "final"

    def test_newest_final_wins_regardless_of_list_order(self):
        submission = _submission(
            _version("newest", "editor_final", minutes=9),
            _version("older", "editor_final", minutes=1),
        )
        assert working_revision(submission).Id == "newest"

    def test_timestamp_tie_is_deterministic(self):
        a = _version("a", "editor_final")
        b = _version("b", "editor_final")
        assert working_revision(_submission(a, b)).Id == "b"
        assert working_revision(_submission(b, a)).Id == "b"

    def test_falls_back_to_ai_then_original(self):
        assert working_revision(_submission(_version("orig", "original"))).Id == "orig"
        assert (
            working_revision(
                _submission(_version("orig", "original"), _version("ai", "ai_suggested", 1))
            ).Id
            == "ai"
        )

    def test_dangling_approval_falls_back_to_drafts(self):
        submission = _submission(_version("final", "editor_final"), approved="deleted")
        assert working_revision(submission).Id == "final"


async def _create_submission(client: AsyncClient, staff_headers: dict[str, str], **overrides):
    resp = await client.post(
        "/api/v1/submissions/", json=make_submission_data(**overrides), headers=staff_headers
    )
    assert resp.status_code == 201
    return resp.json()["Id"]


async def _finalize(
    client: AsyncClient,
    staff_headers: dict[str, str],
    submission_id: str,
    text: str,
    approve: bool,
) -> dict:
    resp = await client.post(
        f"/api/v1/ai-edits/{submission_id}/finalize",
        json={
            "Headline": f"{text} headline",
            "Body": f"{text} body",
            "Approve_For_Newsletter": approve,
        },
        headers=staff_headers,
    )
    assert resp.status_code == 200
    return resp.json()


async def _get_submission(client: AsyncClient, staff_headers: dict[str, str], submission_id: str):
    resp = await client.get(f"/api/v1/submissions/{submission_id}", headers=staff_headers)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
class TestApproval:
    async def test_new_submission_has_no_revisions(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission_id = await _create_submission(client, staff_headers)
        detail = await _get_submission(client, staff_headers, submission_id)
        assert detail["Approved_Version_Id"] is None
        assert detail["Working_Version_Id"] is None

    async def test_approving_records_that_exact_revision(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission_id = await _create_submission(client, staff_headers)
        final = await _finalize(client, staff_headers, submission_id, "approved", approve=True)

        detail = await _get_submission(client, staff_headers, submission_id)
        assert detail["Status"] == "approved"
        assert detail["Approved_Version_Id"] == final["Id"]
        assert detail["Working_Version_Id"] == final["Id"]

    async def test_saving_a_draft_after_approval_clears_the_approval(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission_id = await _create_submission(client, staff_headers)
        await _finalize(client, staff_headers, submission_id, "approved", approve=True)
        draft = await _finalize(client, staff_headers, submission_id, "draft", approve=False)

        detail = await _get_submission(client, staff_headers, submission_id)
        assert detail["Status"] == "in_review"
        assert detail["Approved_Version_Id"] is None
        assert detail["Working_Version_Id"] == draft["Id"]


@pytest.fixture
def background_ai_tasks(monkeypatch: pytest.MonkeyPatch):
    from app.services import ai_edit_service as ai_edits

    monkeypatch.setattr(ai_edits, "async_session_factory", TestSession)
    yield


@pytest.mark.asyncio
@pytest.mark.usefixtures("background_ai_tasks")
class TestApprovedRevisionReachesTheWordFile:
    async def test_original_two_edits_approval_builder_and_docx(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        db.add(
            NewsletterSection(
                Newsletter_Type="tdr",
                Name="Employee News",
                Slug="employee-news",
                Display_Order=1,
                Is_Active=True,
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.services.ai_edit_service.get_llm_provider", lambda settings: SuccessfulProvider()
        )

        submission_id = await _create_submission(
            client,
            staff_headers,
            Original_Headline="Submitted headline",
            Original_Body="Submitted body",
            Schedule_Requests=[{"Requested_Date": "2026-03-16"}],
        )

        # AI suggestion, then two staff finals; only the second is approved.
        resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        first = await _finalize(client, staff_headers, submission_id, "First final", approve=False)
        second = await _finalize(client, staff_headers, submission_id, "Second final", approve=True)

        # Make the unapproved final look newest: approval, not timestamps, decides.
        await db.execute(
            sa.update(EditVersion)
            .where(EditVersion.Id == first["Id"])
            .values(Created_At=datetime(2030, 1, 1))
        )
        await db.commit()

        detail = await _get_submission(client, staff_headers, submission_id)
        assert detail["Working_Version_Id"] == second["Id"]

        async def assemble(publish_date: str) -> dict:
            resp = await client.post(
                "/api/v1/newsletters/assemble",
                json={"Newsletter_Type": "tdr", "Publish_Date": publish_date},
                headers=staff_headers,
            )
            assert resp.status_code == 200
            (item,) = [i for i in resp.json()["Items"] if i["Submission_Id"] == submission_id]
            return {"newsletter_id": resp.json()["Id"], **item}

        item = await assemble("2026-03-16")
        assert item["Final_Headline"] == "Second final headline"
        assert item["Final_Body"] == "Second final body"
        assert item["Source_Version_Id"] == second["Id"]

        # Move the run date and widen the target newsletter; reassembly on the
        # new date must still carry the approved revision.
        resp = await client.post(
            f"/api/v1/submissions/{submission_id}/schedule",
            json={"Requested_Date": "2026-03-18"},
            headers=staff_headers,
        )
        assert resp.status_code == 201
        resp = await client.patch(
            f"/api/v1/submissions/{submission_id}",
            json={"Target_Newsletter": "both"},
            headers=staff_headers,
        )
        assert resp.status_code == 200

        moved = await assemble("2026-03-18")
        assert moved["Final_Body"] == "Second final body"
        assert moved["Source_Version_Id"] == second["Id"]

        resp = await client.get(
            f"/api/v1/newsletters/{moved['newsletter_id']}/export", headers=staff_headers
        )
        assert resp.status_code == 200
        text = "\n".join(p.text for p in Document(io.BytesIO(resp.content)).paragraphs)
        assert "Second final body" in text
        assert "First final body" not in text
        assert "Edited body." not in text
        assert "Submitted body" not in text

        newsletter = await client.get(
            f"/api/v1/newsletters/{moved['newsletter_id']}", headers=staff_headers
        )
        (exported_item,) = [
            i for i in newsletter.json()["Items"] if i["Submission_Id"] == submission_id
        ]
        assert exported_item["Source_Version_Id"] == second["Id"]
