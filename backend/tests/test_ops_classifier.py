"""Tests for the ops needs classifier and the classify-pending step.

The classifier is exercised through a fake provider only — no test calls
MindRouter.
"""

import httpx
import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allowed_value import AllowedValue
from app.models.ops_need_assessment import OpsNeedAssessment
from app.services import harvested_event_service
from app.services.ai.ops_needs_classifier import assess_event
from app.services.ai.provider import LLMProvider
from app.services.ops_event_service import classify_pending_ops_events

from tests.test_harvested_events import patch_feed
from tests.test_ops_events import entry, get_event

NEED_CODES = ["catering", "alcohol_service", "room_setup", "tabling", "outdoor_space"]


class FakeClassifierProvider(LLMProvider):
    """Returns canned payloads (or raises canned exceptions) in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system_prompt, user_prompt, temperature=0.3, max_tokens=2000):
        raise NotImplementedError

    async def complete_json(self, system_prompt, user_prompt, temperature=0.2, max_tokens=2000):
        self.calls.append((system_prompt, user_prompt))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def suggestion(need="catering", confidence="high", rationale="Says 'reception to follow'."):
    return {"need": need, "confidence": confidence, "rationale": rationale}


@pytest.fixture
async def ops_need_vocabulary(db: AsyncSession):
    db.add_all(
        [
            AllowedValue(
                Value_Group="Ops_Need_Type",
                Code=code,
                Label=code.replace("_", " ").title(),
                Display_Order=(index + 1) * 10,
                Visibility_Role="ops",
            )
            for index, code in enumerate(NEED_CODES)
        ]
    )
    await db.commit()


class TestAssessEvent:
    async def assess(self, provider, **overrides):
        fields = {
            "title": "Alumni Awards Reception",
            "description": "Reception to follow with hosted bar.",
            "location": "Vandal Ballroom",
            "category_path": "Alumni Relations",
            "need_codes": NEED_CODES,
        }
        fields.update(overrides)
        return await assess_event(provider, **fields)

    async def test_returns_validated_suggestions(self):
        provider = FakeClassifierProvider(
            [{"needs": [suggestion(), suggestion(need="alcohol_service", confidence="medium")]}]
        )
        result = await self.assess(provider)
        assert [(s.need, s.confidence) for s in result] == [
            ("catering", "high"),
            ("alcohol_service", "medium"),
        ]
        assert result[0].rationale == "Says 'reception to follow'."

    async def test_prompt_carries_vocabulary_and_event_fields(self):
        provider = FakeClassifierProvider([{"needs": []}])
        await self.assess(provider)
        system_prompt, user_prompt = provider.calls[0]
        for code in NEED_CODES:
            assert code in system_prompt
        assert "Alumni Awards Reception" in user_prompt
        assert "Vandal Ballroom" in user_prompt
        assert "Alumni Relations" in user_prompt

    async def test_drops_unknown_needs_and_dedupes(self):
        provider = FakeClassifierProvider(
            [
                {
                    "needs": [
                        suggestion(need="fireworks"),
                        suggestion(),
                        suggestion(confidence="low", rationale="Second mention."),
                    ]
                }
            ]
        )
        result = await self.assess(provider)
        assert len(result) == 1
        assert result[0].need == "catering"

    async def test_empty_needs_is_valid(self):
        provider = FakeClassifierProvider([{"needs": []}])
        assert await self.assess(provider) == []

    async def test_clamps_overlong_rationales(self):
        provider = FakeClassifierProvider(
            [{"needs": [suggestion(rationale="x" * 1000)]}]
        )
        result = await self.assess(provider)
        assert len(result[0].rationale) == 300

    @pytest.mark.parametrize(
        "payload",
        [
            {"wrong": []},
            {"needs": "catering"},
            {"needs": ["catering"]},
            {"needs": [{"need": "catering", "confidence": "definitely", "rationale": "r"}]},
            {"needs": [{"need": "catering", "confidence": "high"}]},
        ],
    )
    async def test_malformed_payloads_raise(self, payload):
        provider = FakeClassifierProvider([payload])
        with pytest.raises(ValueError):
            await self.assess(provider)


class TestClassifyPendingOpsEvents:
    async def harvest(self, db, monkeypatch, payload):
        patch_feed(monkeypatch, payload)
        await harvested_event_service.harvest_trumba_events(db)

    async def test_assesses_pending_events_once_per_content_version(
        self, db: AsyncSession, monkeypatch, ops_need_vocabulary
    ):
        await self.harvest(db, monkeypatch, [entry(1, 10), entry(2, 12)])
        provider = FakeClassifierProvider(
            [{"needs": [suggestion()]}, {"needs": []}]
        )

        summary = await classify_pending_ops_events(db, provider=provider)
        assert summary.assessed == 2
        assert summary.failed == 0
        assert summary.pending == 0

        first = await get_event(db, "1")
        assert [need.Need for need in first.Ops_Needs_Rel] == ["catering"]
        assert first.Ops_Assessed_Content_Hash == first.Content_Hash

        # Nothing pending: a second run must not call the model at all.
        summary = await classify_pending_ops_events(db, provider=provider)
        assert summary.assessed == 0
        assert len(provider.calls) == 2

    async def test_content_change_triggers_reassessment_replacing_rows(
        self, db: AsyncSession, monkeypatch, ops_need_vocabulary
    ):
        await self.harvest(db, monkeypatch, [entry(1, 10)])
        provider = FakeClassifierProvider([{"needs": [suggestion()]}])
        await classify_pending_ops_events(db, provider=provider)

        await self.harvest(
            db, monkeypatch, [entry(1, 10, description="Now with a hosted bar.")]
        )
        provider = FakeClassifierProvider(
            [{"needs": [suggestion(need="alcohol_service")]}]
        )
        summary = await classify_pending_ops_events(db, provider=provider)
        assert summary.assessed == 1

        event = await get_event(db, "1")
        assert [need.Need for need in event.Ops_Needs_Rel] == ["alcohol_service"]
        rows = (
            await db.execute(sa.select(sa.func.count()).select_from(OpsNeedAssessment))
        ).scalar_one()
        assert rows == 1

    async def test_resuggested_need_updates_in_place(
        self, db: AsyncSession, monkeypatch, ops_need_vocabulary
    ):
        """Re-suggesting a still-suggested need must not trip the unique key."""
        await self.harvest(db, monkeypatch, [entry(1, 10)])
        provider = FakeClassifierProvider([{"needs": [suggestion()]}])
        await classify_pending_ops_events(db, provider=provider)

        await self.harvest(
            db, monkeypatch, [entry(1, 10, description="Catered lunch, room TBD.")]
        )
        provider = FakeClassifierProvider(
            [{"needs": [suggestion(confidence="medium", rationale="Catered lunch.")]}]
        )
        summary = await classify_pending_ops_events(db, provider=provider)
        assert summary.assessed == 1

        event = await get_event(db, "1")
        (row,) = event.Ops_Needs_Rel
        assert row.Need == "catering"
        assert row.Confidence == "medium"
        assert row.Rationale == "Catered lunch."
        assert row.Verdict == "suggested"

    async def test_connectivity_failure_aborts_and_marks_nothing(
        self, db: AsyncSession, monkeypatch, ops_need_vocabulary
    ):
        await self.harvest(db, monkeypatch, [entry(1, 10), entry(2, 12)])
        provider = FakeClassifierProvider([httpx.ConnectError("down")])

        summary = await classify_pending_ops_events(db, provider=provider)
        assert summary.assessed == 0
        assert summary.pending == 2
        assert len(provider.calls) == 1

        event = await get_event(db, "1")
        assert event.Ops_Assessed_Content_Hash is None
        assert event.Ops_Needs_Rel == []

    async def test_malformed_output_skips_only_that_event(
        self, db: AsyncSession, monkeypatch, ops_need_vocabulary
    ):
        await self.harvest(db, monkeypatch, [entry(1, 10), entry(2, 12)])
        provider = FakeClassifierProvider(
            [{"wrong": True}, {"needs": [suggestion()]}]
        )

        summary = await classify_pending_ops_events(db, provider=provider)
        assert summary.assessed == 1
        assert summary.failed == 1
        assert summary.pending == 1

    async def test_empty_vocabulary_is_a_noop(
        self, db: AsyncSession, monkeypatch
    ):
        await self.harvest(db, monkeypatch, [entry(1, 10)])
        provider = FakeClassifierProvider([])

        summary = await classify_pending_ops_events(db, provider=provider)
        assert summary.assessed == 0
        assert summary.pending == 1
        assert provider.calls == []


class TestNeedVerdicts:
    async def seed_assessed_event(self, db, monkeypatch, needs):
        patch_feed(monkeypatch, [entry(1, 10)])
        await harvested_event_service.harvest_trumba_events(db)
        provider = FakeClassifierProvider([{"needs": needs}])
        await classify_pending_ops_events(db, provider=provider)
        return await get_event(db, "1")

    async def test_confirm_reject_and_undo(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch,
        ops_need_vocabulary,
    ):
        event = await self.seed_assessed_event(
            db, monkeypatch,
            [suggestion(), suggestion(need="tabling", confidence="low")],
        )

        response = await client.patch(
            f"/api/v1/ops/harvested-events/{event.Id}/needs/catering",
            headers=ops_headers,
            json={"Verdict": "confirmed"},
        )
        assert response.status_code == 200
        needs = {n["Need"]: n for n in response.json()["Needs"]}
        assert needs["catering"]["Verdict"] == "confirmed"
        assert needs["catering"]["Source"] == "ai"
        assert needs["tabling"]["Verdict"] == "suggested"

        response = await client.patch(
            f"/api/v1/ops/harvested-events/{event.Id}/needs/tabling",
            headers=ops_headers,
            json={"Verdict": "rejected"},
        )
        needs = {n["Need"]: n for n in response.json()["Needs"]}
        assert needs["tabling"]["Verdict"] == "rejected"

        response = await client.patch(
            f"/api/v1/ops/harvested-events/{event.Id}/needs/tabling",
            headers=ops_headers,
            json={"Verdict": "suggested"},
        )
        assert response.json()["Needs"][1]["Verdict"] == "suggested"

    async def test_add_staff_need_and_remove_it(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch,
        ops_need_vocabulary,
    ):
        event = await self.seed_assessed_event(db, monkeypatch, [])

        response = await client.post(
            f"/api/v1/ops/harvested-events/{event.Id}/needs",
            headers=ops_headers,
            json={"Need": "alcohol_service"},
        )
        assert response.status_code == 200
        (need,) = response.json()["Needs"]
        assert need["Need"] == "alcohol_service"
        assert need["Verdict"] == "confirmed"
        assert need["Source"] == "staff"
        assert need["Confidence"] is None

        response = await client.delete(
            f"/api/v1/ops/harvested-events/{event.Id}/needs/alcohol_service",
            headers=ops_headers,
        )
        assert response.status_code == 200
        assert response.json()["Needs"] == []

    async def test_adding_an_ai_suggested_need_confirms_it(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch,
        ops_need_vocabulary,
    ):
        event = await self.seed_assessed_event(db, monkeypatch, [suggestion()])

        response = await client.post(
            f"/api/v1/ops/harvested-events/{event.Id}/needs",
            headers=ops_headers,
            json={"Need": "catering"},
        )
        (need,) = response.json()["Needs"]
        assert need["Verdict"] == "confirmed"
        assert need["Source"] == "ai"  # still the AI's suggestion, now confirmed

    async def test_ai_suggestions_cannot_be_removed(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch,
        ops_need_vocabulary,
    ):
        event = await self.seed_assessed_event(db, monkeypatch, [suggestion()])

        response = await client.delete(
            f"/api/v1/ops/harvested-events/{event.Id}/needs/catering",
            headers=ops_headers,
        )
        assert response.status_code == 400

    async def test_unknown_need_type_is_rejected(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch,
        ops_need_vocabulary,
    ):
        event = await self.seed_assessed_event(db, monkeypatch, [])
        response = await client.post(
            f"/api/v1/ops/harvested-events/{event.Id}/needs",
            headers=ops_headers,
            json={"Need": "fireworks"},
        )
        assert response.status_code == 422

    async def test_missing_rows_return_404_and_slc_role_403(
        self, client: AsyncClient, ops_headers, slc_headers, db: AsyncSession,
        monkeypatch, ops_need_vocabulary,
    ):
        event = await self.seed_assessed_event(db, monkeypatch, [])
        response = await client.patch(
            f"/api/v1/ops/harvested-events/{event.Id}/needs/catering",
            headers=ops_headers,
            json={"Verdict": "confirmed"},
        )
        assert response.status_code == 404

        response = await client.post(
            f"/api/v1/ops/harvested-events/{event.Id}/needs",
            headers=slc_headers,
            json={"Need": "catering"},
        )
        assert response.status_code == 403

    async def test_reclassification_preserves_staff_verdicts(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch,
        ops_need_vocabulary,
    ):
        event = await self.seed_assessed_event(
            db, monkeypatch,
            [
                suggestion(),  # catering — will be confirmed
                suggestion(need="tabling", confidence="low"),  # will be rejected
                suggestion(need="room_setup", confidence="low"),  # stays suggested
            ],
        )
        for need, verdict in (("catering", "confirmed"), ("tabling", "rejected")):
            await client.patch(
                f"/api/v1/ops/harvested-events/{event.Id}/needs/{need}",
                headers=ops_headers,
                json={"Verdict": verdict},
            )
        await client.post(
            f"/api/v1/ops/harvested-events/{event.Id}/needs",
            headers=ops_headers,
            json={"Need": "outdoor_space"},
        )

        # Upstream content change re-queues the event; the new assessment
        # suggests tabling again (already rejected) and alcohol (new).
        patch_feed(monkeypatch, [entry(1, 10, description="Now with a hosted bar.")])
        await harvested_event_service.harvest_trumba_events(db)
        # The verdicts above were written through the API's own session;
        # expire so this session sees them, as a fresh classify session would.
        db.expire_all()
        provider = FakeClassifierProvider(
            [
                {
                    "needs": [
                        suggestion(need="tabling"),
                        suggestion(need="alcohol_service"),
                    ]
                }
            ]
        )
        summary = await classify_pending_ops_events(db, provider=provider)
        assert summary.assessed == 1

        await db.refresh(event)
        by_need = {row.Need: row for row in event.Ops_Needs_Rel}
        assert set(by_need) == {"catering", "tabling", "outdoor_space", "alcohol_service"}
        assert by_need["catering"].Verdict == "confirmed"
        assert by_need["tabling"].Verdict == "rejected"  # not resurrected
        assert by_need["outdoor_space"].Source == "staff"
        assert by_need["alcohol_service"].Verdict == "suggested"
        assert "room_setup" not in by_need  # unjudged suggestion was replaced

    async def test_need_filter_excludes_rejected(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch,
        ops_need_vocabulary,
    ):
        patch_feed(monkeypatch, [entry(1, 10), entry(2, 12), entry(3, 14)])
        await harvested_event_service.harvest_trumba_events(db)
        provider = FakeClassifierProvider(
            [
                {"needs": [suggestion()]},  # event 1: catering suggested
                {"needs": [suggestion(confidence="low")]},  # event 2: catering
                {"needs": []},  # event 3: nothing
            ]
        )
        await classify_pending_ops_events(db, provider=provider)
        second = await get_event(db, "2")
        await client.patch(
            f"/api/v1/ops/harvested-events/{second.Id}/needs/catering",
            headers=ops_headers,
            json={"Verdict": "rejected"},
        )

        response = await client.get(
            "/api/v1/ops/harvested-events?need=catering", headers=ops_headers
        )
        assert [item["Source_Id"] for item in response.json()["Items"]] == ["1"]


class TestNeedsInOpsListing:
    async def test_listing_carries_needs_and_assessment_state(
        self,
        client: AsyncClient,
        ops_headers,
        db: AsyncSession,
        monkeypatch,
        ops_need_vocabulary,
    ):
        patch_feed(monkeypatch, [entry(1, 10), entry(2, 12)])
        await harvested_event_service.harvest_trumba_events(db)
        provider = FakeClassifierProvider(
            [
                {
                    "needs": [
                        suggestion(),
                        suggestion(need="outdoor_space", confidence="medium",
                                   rationale="Held on the Tower Lawn."),
                    ]
                },
                httpx.ConnectError("down"),
            ]
        )
        await classify_pending_ops_events(db, provider=provider)

        response = await client.get(
            "/api/v1/ops/harvested-events", headers=ops_headers
        )
        items = {item["Source_Id"]: item for item in response.json()["Items"]}

        assessed = items["1"]
        assert assessed["Needs_Assessed"] is True
        assert [(n["Need"], n["Confidence"]) for n in assessed["Needs"]] == [
            ("catering", "high"),
            ("outdoor_space", "medium"),
        ]
        assert assessed["Needs"][1]["Rationale"] == "Held on the Tower Lawn."

        unassessed = items["2"]
        assert unassessed["Needs_Assessed"] is False
        assert unassessed["Needs"] == []
