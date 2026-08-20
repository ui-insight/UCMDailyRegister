"""Tests for AI edit task handling and failure behavior."""

import asyncio
from datetime import date

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edit_history import EditVersion
from app.models.style_rule import StyleRule
from app.models.submission import Submission
from app.services.ai.editor import AIEditor
from tests.conftest import TestSession, make_submission_data


@pytest.fixture(autouse=True)
def configure_ai_edit_tasks(monkeypatch: pytest.MonkeyPatch):
    from app.api.v1 import ai_edits

    ai_edits._ai_edit_tasks.clear()
    monkeypatch.setattr(ai_edits, "async_session_factory", TestSession)
    yield
    ai_edits._ai_edit_tasks.clear()


class SuccessfulProvider:
    model = "test-model"
    last_user_prompt = ""
    last_system_prompt = ""

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        SuccessfulProvider.last_user_prompt = kwargs.get("user_prompt", "")
        SuccessfulProvider.last_system_prompt = kwargs.get("system_prompt", "")
        return {
            "edited_headline": "Edited headline",
            "edited_body": "Edited body.",
            "changes_made": ["Shortened headline"],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.95,
        }


class FailingProvider:
    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        raise RuntimeError("provider unavailable")


class ProperNounProvider:
    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        return {
            "edited_headline": "Attend Elizabeth Bradfield reading from SoFar",
            "edited_body": "Elizabeth Bradfield will read from SoFar.",
            "changes_made": ["Rewrote the headline in sentence case"],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.95,
        }


class SemicolonProvider:
    model = "test-model"
    last_system_prompt = ""

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        SemicolonProvider.last_system_prompt = kwargs.get("system_prompt", "")
        return {
            "edited_headline": "Read the update",
            "edited_body": (
                "The first idea is complete; the second idea links to "
                '<a href="https://example.com/path?a=1;b=2">news &amp; features</a>.'
            ),
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.95,
        }


async def wait_for_task(
    client: AsyncClient,
    task_id: str,
    staff_headers: dict[str, str],
) -> dict:
    for _ in range(10):
        resp = await client.get(f"/api/v1/ai-edits/tasks/{task_id}", headers=staff_headers)
        assert resp.status_code == 200
        task = resp.json()
        if task["Status"] in {"succeeded", "failed"}:
            return task
        await asyncio.sleep(0)
    raise AssertionError("AI edit task did not finish")


@pytest.mark.asyncio
class TestAIEditTasks:
    async def test_staff_ai_edit_runs_as_task_and_saves_successful_result(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )

        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert task["Result"]["Edited_Headline"] == "Edited headline"
        assert task["Result"]["Edit_Version_Id"]

        versions_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions",
            headers=staff_headers,
        )
        assert versions_resp.status_code == 200
        assert [version["Version_Type"] for version in versions_resp.json()] == [
            "original",
            "ai_suggested",
        ]

        submission_detail_resp = await client.get(
            f"/api/v1/submissions/{submission_id}",
            headers=staff_headers,
        )
        assert submission_detail_resp.status_code == 200
        assert submission_detail_resp.json()["Status"] == "ai_edited"

    async def test_staff_ai_edit_includes_editor_feedback_in_prompt(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_user_prompt = ""
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={
                "Newsletter_Type": "tdr",
                "Editor_Instructions": "Tighten the first sentence.",
            },
            headers=staff_headers,
        )

        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert "Editor Feedback for This Revision" in SuccessfulProvider.last_user_prompt
        assert "Tighten the first sentence." in SuccessfulProvider.last_user_prompt

        versions_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions",
            headers=staff_headers,
        )
        assert versions_resp.status_code == 200
        ai_version = versions_resp.json()[-1]
        assert ai_version["Version_Type"] == "ai_suggested"
        assert ai_version["Editor_Instructions"] == "Tighten the first sentence."

    async def test_staff_ai_edit_applies_mandatory_event_and_vandal_gear_rules(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add_all(
            [
                StyleRule(
                    Rule_Set="shared",
                    Category="formatting",
                    Rule_Key="event_detail_ordering",
                    Rule_Text=(
                        "Order event details as: time, day, date, location. "
                        "Do not reorder these elements."
                    ),
                    Severity="error",
                ),
                StyleRule(
                    Rule_Set="shared",
                    Category="terminology",
                    Rule_Key="vandal_gear_capitalization",
                    Rule_Text=(
                        "Always write 'Vandal Gear' as two capitalized words."
                    ),
                    Severity="error",
                ),
            ]
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Body=(
                    "The VandalGear reception is Thursday, Aug. 20 at 5 p.m. "
                    "in the Seed Potato Germplasm Laboratory."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert "[MUST] Order event details as: time, day, date, location" in (
            SuccessfulProvider.last_system_prompt
        )
        assert "[MUST] Always write 'Vandal Gear' as two capitalized words" in (
            SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_receives_contact_line_format_rule(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add(
            StyleRule(
                Rule_Set="shared",
                Category="formatting",
                Rule_Key="contact_line_format",
                Rule_Text=(
                    "Never repeat the contact's name in place of contact "
                    "information. Hyperlink the contact's name with a provided "
                    "email address instead of displaying the address."
                ),
                Severity="error",
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Body=(
                    "The safety fair runs 9-11 a.m. Friday, Aug. 21, in the "
                    "Pitman Center. For questions, please contact Paul Rowley "
                    "(prowley@uidaho.edu)."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert "[MUST] Never repeat the contact's name in place of contact" in (
            SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_receives_date_continuation_comma_rule(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add(
            StyleRule(
                Rule_Set="shared",
                Category="formatting",
                Rule_Key="ap_style_dates",
                Rule_Text=(
                    "Use AP style for dates. When a month-and-day date appears "
                    "mid-sentence, place a comma after the date if the sentence "
                    "continues."
                ),
                Severity="warning",
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Body=(
                    "The conference will take place on Monday, Oct. 31 and "
                    "Tuesday, Nov. 1 in the Pitman Center."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert (
            "[SHOULD] Use AP style for dates. When a month-and-day date appears"
            in SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_receives_deadline_preservation_rule(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add(
            StyleRule(
                Rule_Set="shared",
                Category="content_filtering",
                Rule_Key="preserve_action_deadlines",
                Rule_Text=(
                    "Preserve every deadline and actionable date from the "
                    "original submission. Never replace a specific deadline "
                    "with a generic call to action."
                ),
                Severity="error",
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Body=(
                    "Registration deadline: Oct. 23. Abstract submission "
                    "deadline: Oct. 16. Join the microbiology meeting."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert (
            "[MUST] Preserve every deadline and actionable date"
            in SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_receives_cta_filler_ban(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add(
            StyleRule(
                Rule_Set="shared",
                Category="voice",
                Rule_Key="cta_structure",
                Rule_Text=(
                    "Never build a call to action on filler words: no CTA may "
                    "contain 'here' or 'click here'. Link the action verb or "
                    "the object of the action instead."
                ),
                Severity="warning",
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Body="Employees can sign up here for the newsletter.",
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert (
            "[SHOULD] Never build a call to action on filler words"
            in SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_receives_distinct_headline_rule(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add(
            StyleRule(
                Rule_Set="shared",
                Category="headlines",
                Rule_Key="headline_distinct_from_lead",
                Rule_Text=(
                    "The headline must not be the first sentence of the body "
                    "or a minor rewording of it."
                ),
                Severity="warning",
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Headline="Sign up for sustainability newsletter",
                Original_Body=(
                    "Sign up for the sustainability newsletter. A monthly "
                    "issue starts in September."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert (
            "[SHOULD] The headline must not be the first sentence of the body"
            in SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_receives_event_context_preservation_rule(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add(
            StyleRule(
                Rule_Set="shared",
                Category="content_filtering",
                Rule_Key="preserve_event_context",
                Rule_Text=(
                    "When condensing, distinguish unnecessary repetition from "
                    "meaningful context. Preserve traditions, participant "
                    "activities, routes and event logistics."
                ),
                Severity="warning",
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Body=(
                    "The sororities will open bids at 11:15 and promptly run "
                    "home to their chapters down Idaho Avenue."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert (
            "[SHOULD] When condensing, distinguish unnecessary repetition"
            in SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_receives_event_name_precedence_rules(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add_all(
            [
                StyleRule(
                    Rule_Set="shared",
                    Category="formatting",
                    Rule_Key="preserve_event_title_case",
                    Rule_Text=(
                        "Do not change event titles. Preserving their official "
                        "capitalization takes precedence over sentence-casing."
                    ),
                    Severity="error",
                ),
                StyleRule(
                    Rule_Set="tdr",
                    Category="headlines",
                    Rule_Key="sentence_case",
                    Rule_Text=(
                        "Headlines must be sentence case. Official event, "
                        "program and organization names also count as proper "
                        "nouns and keep their official capitalization."
                    ),
                    Severity="error",
                ),
            ]
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Headline="Fraternity and Sorority Life Bid Day",
                Original_Body=(
                    "Fraternity and Sorority Life Bid Day is Saturday, "
                    "Aug. 22, on Idaho Avenue."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert (
            "takes precedence over sentence-casing"
            in SuccessfulProvider.last_system_prompt
        )
        assert (
            "keep their official capitalization"
            in SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_receives_jobs_single_line_rule(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SuccessfulProvider.last_system_prompt = ""
        db.add(
            StyleRule(
                Rule_Set="tdr",
                Category="formatting",
                Rule_Key="job_posting_format",
                Rule_Text=(
                    "Format every Jobs-category submission as a single-line "
                    "listing, not a news item: job title (sentence case), "
                    "department or unit, location."
                ),
                Severity="error",
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Category="job_opportunity",
                Original_Headline="Administrative Specialist III",
                Original_Body=(
                    "Department: College of Engineering. Location: Moscow. "
                    "Apply using the linked posting."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert (
            "[MUST] Format every Jobs-category submission as a single-line"
            in SuccessfulProvider.last_system_prompt
        )

    async def test_staff_ai_edit_enforces_short_sentences_and_safe_semicolon_cleanup(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        SemicolonProvider.last_system_prompt = ""
        db.add(
            StyleRule(
                Rule_Set="shared",
                Category="voice",
                Rule_Key="short_sentences",
                Rule_Text=(
                    "Use short, complete sentences. Each sentence should communicate "
                    "one main idea. Do not use semicolons."
                ),
                Severity="error",
            )
        )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SemicolonProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Body=(
                    "The first idea is complete; the second idea includes more detail."
                ),
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)

        assert task["Status"] == "succeeded"
        assert "Each sentence should communicate one main idea" in (
            SemicolonProvider.last_system_prompt
        )
        assert "Do not use semicolons" in SemicolonProvider.last_system_prompt
        assert task["Result"]["Edited_Body"] == (
            "The first idea is complete. The second idea links to "
            '<a href="https://example.com/path?a=1;b=2">news &amp; features</a>.'
        )
        assert task["Result"]["Changes_Made"] == [
            "Replaced semicolons with periods to enforce the short-sentence rule"
        ]

    async def test_ai_edit_preserves_proper_nouns_in_sentence_case_headline(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Do not undo correct proper-noun casing returned by the model.

        This is the exact failure pattern from Joy's feedback: a model can return
        sentence case with a correctly capitalized name, but deterministic
        post-processing must not lowercase that name afterward.
        """
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: ProperNounProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Headline="ELIZABETH BRADFIELD READING FROM SOFAR",
            ),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )

        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert (
            task["Result"]["Edited_Headline"]
            == "Attend Elizabeth Bradfield reading from SoFar"
        )

    async def test_provider_failure_does_not_save_ai_version_or_mark_ai_edited(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: FailingProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )

        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "failed"
        assert task["Result"] is None
        assert "provider unavailable" in task["Error_Message"]

        versions = (
            await db.execute(
                sa.select(EditVersion).where(EditVersion.Submission_Id == submission_id)
            )
        ).scalars().all()
        assert versions == []

        submission = (
            await db.execute(sa.select(Submission).where(Submission.Id == submission_id))
        ).scalar_one()
        assert submission.Status == "new"

    async def test_public_cannot_access_ai_edit_task_or_version_endpoints(
        self,
        client: AsyncClient,
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        task_resp = await client.get("/api/v1/ai-edits/tasks/not-a-task")
        assert task_resp.status_code == 403

        versions_resp = await client.get(f"/api/v1/ai-edits/{submission_id}/versions")
        assert versions_resp.status_code == 403

        version_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions/not-a-version"
        )
        assert version_resp.status_code == 403

        finalize_resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/finalize",
            json={"Headline": "Final", "Body": "Final body."},
        )
        assert finalize_resp.status_code == 403


@pytest.mark.asyncio
class TestFinalizePreservesOriginal:
    async def test_finalize_allows_body_only_jobs_but_not_body_only_news(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        job_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(Category="job_opportunity"),
        )
        job_id = job_resp.json()["Id"]

        finalize_job = await client.post(
            f"/api/v1/ai-edits/{job_id}/finalize",
            json={
                "Headline": "This headline must not be published",
                "Body": "Administrative specialist III, College of Engineering",
                "Approve_For_Newsletter": True,
            },
            headers=staff_headers,
        )

        assert finalize_job.status_code == 200
        assert finalize_job.json()["Headline"] == ""
        job_detail = await client.get(
            f"/api/v1/submissions/{job_id}",
            headers=staff_headers,
        )
        assert job_detail.json()["Status"] == "approved"

        news_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(Category="faculty_staff"),
        )
        finalize_news = await client.post(
            f"/api/v1/ai-edits/{news_resp.json()['Id']}/finalize",
            json={"Headline": "", "Body": "Body-only news item."},
            headers=staff_headers,
        )

        assert finalize_news.status_code == 422

    async def test_finalize_replaces_links_with_validated_editor_links(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Links=[{"Url": "https://old.example.com", "Anchor_Text": "Old link"}],
            ),
        )
        submission_id = submission_resp.json()["Id"]

        finalize_resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/finalize",
            json={
                "Headline": "Editor headline",
                "Body": 'Contact <a href="mailto:questions@uidaho.edu">UCM</a>.',
                "Links": [
                    {
                        "Url": "questions@uidaho.edu",
                        "Anchor_Text": "UCM",
                    }
                ],
            },
            headers=staff_headers,
        )

        assert finalize_resp.status_code == 200
        detail_resp = await client.get(
            f"/api/v1/submissions/{submission_id}",
            headers=staff_headers,
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["Links"] == [
            {
                "Id": detail_resp.json()["Links"][0]["Id"],
                "Url": "mailto:questions@uidaho.edu",
                "Anchor_Text": "UCM",
                "Display_Order": 0,
            }
        ]

    async def test_finalize_without_prior_ai_edit_keeps_original_and_snapshots_it(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        created = submission_resp.json()
        submission_id = created["Id"]
        original_headline = created["Original_Headline"]
        original_body = created["Original_Body"]

        finalize_resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/finalize",
            json={"Headline": "Editor headline", "Body": "Editor body."},
            headers=staff_headers,
        )
        assert finalize_resp.status_code == 200
        assert finalize_resp.json()["Version_Type"] == "editor_final"

        detail_resp = await client.get(
            f"/api/v1/submissions/{submission_id}",
            headers=staff_headers,
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["Original_Headline"] == original_headline
        assert detail["Original_Body"] == original_body
        assert detail["Status"] == "in_review"

        versions_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions",
            headers=staff_headers,
        )
        assert versions_resp.status_code == 200
        versions = versions_resp.json()
        assert [v["Version_Type"] for v in versions] == ["original", "editor_final"]
        assert versions[0]["Headline"] == original_headline
        assert versions[0]["Body"] == original_body
        assert versions[1]["Headline"] == "Editor headline"
        assert versions[1]["Body"] == "Editor body."

    async def test_repeated_finalize_keeps_single_original_snapshot(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        created = submission_resp.json()
        submission_id = created["Id"]

        # AI edit first (creates the 'original' snapshot), then finalize twice
        edit_resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert edit_resp.status_code == 202
        task = await wait_for_task(client, edit_resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"

        for headline in ("First final", "Second final"):
            finalize_resp = await client.post(
                f"/api/v1/ai-edits/{submission_id}/finalize",
                json={"Headline": headline, "Body": f"{headline} body."},
                headers=staff_headers,
            )
            assert finalize_resp.status_code == 200

        detail_resp = await client.get(
            f"/api/v1/submissions/{submission_id}",
            headers=staff_headers,
        )
        assert detail_resp.json()["Original_Headline"] == created["Original_Headline"]

        versions_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions",
            headers=staff_headers,
        )
        version_types = [v["Version_Type"] for v in versions_resp.json()]
        assert version_types.count("original") == 1
        assert version_types.count("editor_final") == 2

    async def test_finalize_and_approve_is_atomic_and_preserves_original(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        created = submission_resp.json()
        submission_id = created["Id"]

        finalize_resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/finalize",
            json={
                "Headline": "Approved editor headline",
                "Body": "Approved editor body.",
                "Approve_For_Newsletter": True,
            },
            headers=staff_headers,
        )

        assert finalize_resp.status_code == 200
        assert finalize_resp.json()["Version_Type"] == "editor_final"

        detail_resp = await client.get(
            f"/api/v1/submissions/{submission_id}",
            headers=staff_headers,
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["Status"] == "approved"
        assert detail["Original_Headline"] == created["Original_Headline"]
        assert detail["Original_Body"] == created["Original_Body"]

        versions_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions",
            headers=staff_headers,
        )
        assert [version["Version_Type"] for version in versions_resp.json()] == [
            "original",
            "editor_final",
        ]


class NoncompliantProvider:
    """Returns output that violates several active [MUST] rules at once."""

    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        return {
            "edited_headline": "NNSA briefing set",
            "edited_body": (
                "The NNSA briefing is at 9 AM Wednesday, October 2, via Zoom. "
                "Register for the briefing. Space is limited, so register soon."
            ),
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


class CompliantProvider:
    """Returns output that satisfies every deterministically checked rule."""

    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        return {
            "edited_headline": "NNSA briefing set",
            "edited_body": (
                "The National Nuclear Security Administration (NNSA) briefing "
                "is at 9 a.m. Friday, Oct. 2, 2026, online. Register for the briefing."
            ),
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


class SingleLineJobsProvider:
    """Returns a Jobs listing that wrongly retains the Moscow location."""

    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        return {
            "edited_headline": "Laboratory manager",
            "edited_body": (
                "Laboratory manager, Image and Data Acquisition Core, Institute "
                "for Modeling Collaboration and Innovation, Moscow"
            ),
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


class SourceFidelityRegressionProvider:
    """Reproduces Joy's contact, branded-name and weekday regressions."""

    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        return {
            "edited_headline": "Join U of I Dance Ensemble auditions",
            "edited_body": (
                "Contact Melanie Meenan at melanie@example.com or 208-555-0199 "
                "about auditions at 3 p.m. "
                "Thursday, Aug. 25, 2026."
            ),
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


class SourceFidelityCompliantProvider:
    """Preserves source contacts/names and uses the correct weekday."""

    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        return {
            "edited_headline": "Join UIdaho Dance Ensemble auditions",
            "edited_body": (
                "The UIdaho Dance Ensemble holds auditions at 3 p.m. "
                "Tuesday, Aug. 25, 2026. Contact the "
                '<a href="mailto:dance@uidaho.edu">dance program</a>.'
            ),
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


CHECKED_RULES = [
    ("shared", "formatting", "ap_style_dates", "error"),
    ("shared", "formatting", "ap_style_times", "error"),
    ("shared", "formatting", "online_not_platform", "error"),
    ("shared", "formatting", "spell_out_acronyms", "error"),
    ("shared", "voice", "single_cta", "error"),
]


@pytest.mark.asyncio
class TestDeterministicPostValidation:
    """An active rule the model ignores must surface as a flag (issue #300)."""

    async def _run_edit(self, client, db, staff_headers, monkeypatch, provider, **overrides):
        for rule_set, category, rule_key, severity in CHECKED_RULES:
            db.add(
                StyleRule(
                    Rule_Set=rule_set,
                    Category=category,
                    Rule_Key=rule_key,
                    Rule_Text=f"Managed rule {rule_key}.",
                    Severity=severity,
                )
            )
        await db.commit()
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: provider,
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(**overrides),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"

        versions_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions",
            headers=staff_headers,
        )
        assert versions_resp.status_code == 200
        ai_version = next(
            version
            for version in versions_resp.json()
            if version["Version_Type"] == "ai_suggested"
        )
        return ai_version["Flags"] or []

    async def test_ignored_must_rules_are_flagged_on_the_ai_version(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        flags = await self._run_edit(
            client, db, staff_headers, monkeypatch, NoncompliantProvider()
        )
        flagged_rules = {flag["rule_key"] for flag in flags}

        assert "ap_style_dates" in flagged_rules  # October 2
        assert "ap_style_times" in flagged_rules  # 9 AM
        assert "online_not_platform" in flagged_rules  # Zoom
        assert "spell_out_acronyms" in flagged_rules  # undefined NNSA
        assert "single_cta" in flagged_rules  # register twice

        by_rule = {flag["rule_key"]: flag for flag in flags}
        assert by_rule["ap_style_dates"]["type"] == "error"
        assert by_rule["online_not_platform"]["type"] == "warning"

    async def test_missing_weekday_on_near_term_deadline_is_flagged(self):
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Enroll for a meal plan",
            "Enroll by Aug. 22 for a chance to win.",
            "faculty_staff",
            [
                {
                    "category": "formatting",
                    "rule_key": "day_of_week_with_dates",
                    "rule_text": "Managed near-term weekday rule.",
                    "severity": "error",
                }
            ],
            reference_date=date(2026, 8, 17),
        )

        assert flags == [
            {
                "type": "error",
                "rule_key": "day_of_week_with_dates",
                "message": "Near-term date is missing its weekday: 'Aug. 22'",
            }
        ]

    async def test_missing_accreditor_from_reported_edit_is_flagged(self):
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Explore campus sustainability resources",
            (
                "Visit the Office of Sustainability's Inside U of I homepage to "
                "explore sustainable solutions at the U of I. Discover the "
                "initiatives that make the institution a STARS Gold-rated university."
            ),
            "faculty_staff",
            [
                {
                    "category": "content_filtering",
                    "rule_key": "preserve_organizational_context",
                    "rule_text": "Managed organizational-context rule.",
                    "severity": "error",
                }
            ],
            source_text=(
                "Learn More About Sustainability on Campus\n"
                "Visit the Office of Sustainability's Inside U of I homepage and "
                "explore sustainable solutions at the University of Idaho. Discover "
                "the initiatives that make our institution an Association for "
                "Advancement in Sustainability in Higher Education STARS Gold rated "
                "university in sustainability excellence."
            ),
            source_body=(
                "Visit the Office of Sustainability's Inside U of I homepage and "
                "explore sustainable solutions at the University of Idaho. Discover "
                "the initiatives that make our institution an Association for "
                "Advancement in Sustainability in Higher Education STARS Gold rated "
                "university in sustainability excellence."
            ),
        )

        assert flags == [
            {
                "type": "error",
                "rule_key": "preserve_organizational_context",
                "message": (
                    "Source organization missing from AI-edited body: "
                    "'Association for Advancement in Sustainability in Higher Education'"
                ),
            }
        ]

    async def test_reported_edit_flags_sponsor_and_contact_titles_only(self):
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Earn money for nonprofit with Idaho Eats",
            (
                "Nonprofit organizations can earn money for their cause by volunteering "
                "at concessions during sporting events and concerts on campus. Volunteers "
                "receive a donation equal to a percentage of net sales, which varies by "
                "event type and attendance. Opportunities are available throughout the "
                "school year and offer flexibility. Orientation and training are provided. "
                "In Idaho, cashiers serving alcohol must be 21 or older and TIPS certified. "
                "To sign up, contact <a href=\"mailto:dconklin@uidaho.edu\">Danny "
                "Conklin</a> or <a href=\"mailto:pwenzel@uidaho.edu\">Perry Wenzel</a> "
                "with the number of group members over 21 and a representative's contact "
                "information."
            ),
            "faculty_staff",
            [
                {
                    "category": "content_filtering",
                    "rule_key": "preserve_organizational_context",
                    "rule_text": "Managed organizational-context rule.",
                    "severity": "error",
                },
                {
                    "category": "formatting",
                    "rule_key": "preserve_purpose_contact_titles",
                    "rule_text": "Managed contact-title rule.",
                    "severity": "error",
                },
                {
                    "category": "content_filtering",
                    "rule_key": "preserve_action_deadlines",
                    "rule_text": "Managed requirement rule.",
                    "severity": "error",
                },
            ],
            source_text=(
                "Non-Profit Organization Opportunity with Idaho Eats\n"
                "Idaho Eats offers an opportunity for non-profit organizations to earn "
                "money for their cause through volunteer events on campus. Volunteers "
                "assist in concessions operations during sporting events and concerts for "
                "a donation equal to a percentage of net sales. Orientation and training "
                "will be provided. In Idaho, all cashiers serving alcohol must be 21+ and "
                "TIPS certified. Contact Danny Conklin (Concessions Manager) at "
                "dconklin@uidaho.edu or Perry Wenzel (Director of Retail Dining) at "
                "pwenzel@uidaho.edu."
            ),
            source_body=(
                "Idaho Eats offers an opportunity for non-profit organizations to earn "
                "money for their cause through volunteer events on campus. Volunteers "
                "assist in concessions operations during sporting events and concerts for "
                "a donation equal to a percentage of net sales. Orientation and training "
                "will be provided. In Idaho, all cashiers serving alcohol must be 21+ and "
                "TIPS certified. Contact Danny Conklin (Concessions Manager) at "
                "dconklin@uidaho.edu or Perry Wenzel (Director of Retail Dining) at "
                "pwenzel@uidaho.edu."
            ),
        )

        assert {flag["rule_key"] for flag in flags} == {
            "preserve_organizational_context",
            "preserve_purpose_contact_titles",
        }
        assert [
            flag["message"]
            for flag in flags
            if flag["rule_key"] == "preserve_organizational_context"
        ] == ["Source organization missing from AI-edited body: 'Idaho Eats'"]
        assert any("Danny Conklin, concessions manager" in flag["message"] for flag in flags)
        assert any("Perry Wenzel, director of retail dining" in flag["message"] for flag in flags)

    async def test_removed_information_option_and_requirement_are_flagged(self):
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Apply for the program",
            "Sign up by emailing the program office.",
            "faculty_staff",
            [
                {
                    "category": "content_filtering",
                    "rule_key": "preserve_information_options",
                    "rule_text": "Managed information-option rule.",
                    "severity": "error",
                },
                {
                    "category": "content_filtering",
                    "rule_key": "preserve_action_deadlines",
                    "rule_text": "Managed requirement rule.",
                    "severity": "error",
                },
            ],
            source_text=(
                "Sign up or learn more by emailing the program office. "
                "Applicants must have a 3.0 GPA."
            ),
        )

        assert {flag["rule_key"] for flag in flags} == {
            "preserve_information_options",
            "preserve_action_deadlines",
        }

    async def test_reported_promotional_edit_flags_weak_lead_and_cta_problems(self):
        source_body = (
            "Last week to get your commuter parking permit reimbursed in full through "
            "IdahoEats. Enroll in a qualifying meal plan by August 22 to enter the random "
            "drawing for one faculty or staff winner. Enroll here before the window "
            "closes. Terms and conditions apply, see landing page for full details."
        )
        edited_body = (
            "The last week to have a commuter parking permit reimbursed in full through "
            "IdahoEats is this week. Employees who enroll in a qualifying meal plan by "
            "Aug. 22 will be entered in a random drawing for one faculty or staff winner. "
            "<a href='https://example.com/promotion'>Enroll now</a>. Terms and conditions "
            "apply. See the landing page for full details."
        )
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Buy early and park for free",
            edited_body,
            "faculty_staff",
            [
                {
                    "category": "voice",
                    "rule_key": "promotional_action_benefit_lead",
                    "rule_text": "Managed promotional-lead rule.",
                    "severity": "error",
                },
                {
                    "category": "voice",
                    "rule_key": "cta_structure",
                    "rule_text": "Managed CTA structure rule.",
                    "severity": "error",
                },
                {
                    "category": "voice",
                    "rule_key": "single_cta",
                    "rule_text": "Managed single-CTA rule.",
                    "severity": "error",
                },
            ],
            source_text=source_body,
            source_body=source_body,
        )

        assert {flag["rule_key"] for flag in flags} == {
            "promotional_action_benefit_lead",
            "cta_structure",
            "single_cta",
        }
        assert any("landing page" in flag["message"] for flag in flags)
        assert any("'enroll'" in flag["message"] for flag in flags)

    async def test_reported_research_edit_flags_generic_lead_and_indirect_contact(self):
        source_body = (
            "Researchers at the Margaret Ritchie School of Family and Consumer Sciences "
            "are currently seeking lactating women interested in donating milk for a "
            "research project at the University of Idaho. Participants must be between "
            "the ages of 18 and 50 and currently breastfeeding or pumping for an infant "
            "at least 2 weeks old. Each participant is requested to donate up to 10 oz of "
            "milk and will receive a $25 gift card for every 2 oz donated. If you are "
            "interested, please contact Betsy Church at betsychurch@uidaho.edu for more "
            "information."
        )
        edited_body = (
            "Researchers are recruiting participants for a study on human milk composition "
            "at the Margaret Ritchie School of Family and Consumer Sciences, U of I. "
            "Participants must be 18 to 50 years old and currently breastfeeding or pumping "
            "for an infant at least two weeks old. Each donor may provide up to 10 oz of "
            "milk and will receive a $25 gift card for every 2 oz donated. Interested "
            "participants should contact <a href='mailto:betsychurch@uidaho.edu'>Betsy "
            "Church</a> for more information."
        )
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Participate in human milk composition study",
            edited_body,
            "faculty_staff",
            [
                {
                    "category": "content_filtering",
                    "rule_key": "preserve_audience_scope",
                    "rule_text": "Managed audience rule.",
                    "severity": "error",
                },
                {
                    "category": "voice",
                    "rule_key": "cta_structure",
                    "rule_text": "Managed CTA structure rule.",
                    "severity": "error",
                },
            ],
            source_text=source_body,
            source_body=source_body,
        )

        assert {flag["rule_key"] for flag in flags} == {
            "preserve_audience_scope",
            "cta_structure",
        }
        assert any("breastfeeding/lactating women" in flag["message"] for flag in flags)
        assert any("ages 18-50" in flag["message"] for flag in flags)
        assert any("Interested participants should contact" in flag["message"] for flag in flags)

    async def test_channel_derived_employee_audience_is_flagged(self):
        source_body = (
            "Looking for a job on campus or in Moscow? U of I departments and local "
            "businesses will recruit freshman through graduate students."
        )
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Attend the job fair",
            "Employees seeking on-campus or Moscow employment can attend the job fair.",
            "faculty_staff",
            [
                {
                    "category": "content_filtering",
                    "rule_key": "preserve_audience_scope",
                    "rule_text": "Managed audience rule.",
                    "severity": "error",
                }
            ],
            source_text=source_body,
            source_body=source_body,
        )

        assert {flag["rule_key"] for flag in flags} == {"preserve_audience_scope"}
        assert "employees" in flags[0]["message"].lower()

    async def test_disallowed_ampersand_is_flagged(self):
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Attend the Campus & Community Job Fair",
            "Attend the Campus & Community Job Fair.",
            "faculty_staff",
            [
                {
                    "category": "formatting",
                    "rule_key": "ampersand_to_and",
                    "rule_text": "Managed ampersand rule.",
                    "severity": "error",
                }
            ],
        )

        assert {flag["rule_key"] for flag in flags} == {"ampersand_to_and"}

    async def test_event_order_and_cross_period_hyphen_are_flagged(self):
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Attend the job fair",
            (
                "Attend the fair on Thursday, Aug. 27, from 11 a.m.-2 p.m. "
                "in the ISUB Summit Conference Center."
            ),
            "faculty_staff",
            [
                {
                    "category": "formatting",
                    "rule_key": "event_detail_ordering",
                    "rule_text": "Managed event order rule.",
                    "severity": "error",
                },
                {
                    "category": "formatting",
                    "rule_key": "ap_style_times",
                    "rule_text": "Managed time rule.",
                    "severity": "error",
                },
            ],
        )

        assert {flag["rule_key"] for flag in flags} == {
            "event_detail_ordering",
            "ap_style_times",
        }

    async def test_relative_word_cannot_replace_source_calendar_date(self):
        source_body = (
            "Regular business hours of 8 a.m. to 5 p.m. resume today, Aug. 24."
        )
        flags = AIEditor(SuccessfulProvider()).post_analyze(
            "Regular hours resume today",
            "Regular business hours of 8 a.m. to 5 p.m. resume today.",
            "faculty_staff",
            [
                {
                    "category": "formatting",
                    "rule_key": "today_tomorrow",
                    "rule_text": "Managed relative-date rule.",
                    "severity": "error",
                }
            ],
            source_text=source_body,
            source_body=source_body,
        )

        assert {flag["rule_key"] for flag in flags} == {"today_tomorrow"}
        assert "Aug. 24" in flags[0]["message"]

    async def test_compliant_output_produces_no_post_validation_flags(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        flags = await self._run_edit(
            client, db, staff_headers, monkeypatch, CompliantProvider()
        )
        checked = {rule_key for _, _, rule_key, _ in CHECKED_RULES}

        assert not [flag for flag in flags if flag["rule_key"] in checked]

    async def test_jobs_listing_that_keeps_moscow_is_flagged(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        db.add(
            StyleRule(
                Rule_Set="tdr",
                Category="formatting",
                Rule_Key="job_posting_format",
                Rule_Text="Managed Jobs rule.",
                Severity="error",
            )
        )
        await db.commit()
        flags = await self._run_edit(
            client,
            db,
            staff_headers,
            monkeypatch,
            SingleLineJobsProvider(),
            Category="job_opportunity",
        )
        jobs_flags = [flag for flag in flags if flag["rule_key"] == "job_posting_format"]

        assert jobs_flags
        assert all(flag["type"] == "error" for flag in jobs_flags)
        assert any("headline" in flag["message"] for flag in jobs_flags)
        assert any("Moscow" in flag["message"] for flag in jobs_flags)

    @pytest.mark.parametrize(
        "provider,expected",
        [
            (
                SourceFidelityRegressionProvider(),
                {
                    "no_fabricated_content",
                    "preserve_purpose_contact_titles",
                    "preserve_event_title_case",
                    "ap_style_dates",
                },
            ),
            (SourceFidelityCompliantProvider(), set()),
        ],
    )
    async def test_source_fidelity_and_calendar_validation(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
        provider,
        expected: set[str],
    ):
        for category, rule_key in (
            ("content_filtering", "no_fabricated_content"),
            ("formatting", "preserve_purpose_contact_titles"),
            ("formatting", "preserve_event_title_case"),
        ):
            db.add(
                StyleRule(
                    Rule_Set="shared",
                    Category=category,
                    Rule_Key=rule_key,
                    Rule_Text=f"Managed rule {rule_key}.",
                    Severity="error",
                )
            )
        await db.commit()

        flags = await self._run_edit(
            client,
            db,
            staff_headers,
            monkeypatch,
            provider,
            Original_Headline="UIdaho Dance Ensemble auditions",
            Original_Body=(
                "UIdaho Dance Ensemble auditions are at 3 p.m. Aug. 25, 2026. "
                "Email dance@uidaho.edu for alternate audition options."
            ),
        )
        relevant = {
            flag["rule_key"]
            for flag in flags
            if flag["rule_key"]
            in {
                "no_fabricated_content",
                "preserve_purpose_contact_titles",
                "preserve_event_title_case",
                "ap_style_dates",
            }
        }

        assert relevant == expected
