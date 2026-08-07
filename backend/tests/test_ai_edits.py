"""Tests for AI edit task handling and failure behavior."""

import asyncio

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edit_history import EditVersion
from app.models.style_rule import StyleRule
from app.models.submission import Submission
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
