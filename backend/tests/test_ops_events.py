"""Tests for the Event Services (ops) triage lens over harvested events."""

from datetime import date, datetime, time, timedelta

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.harvested_event import HarvestedEvent
from app.services import harvested_event_service
from app.services.harvested_event_service import set_review_status
from app.services.ops_event_service import list_ops_events

from tests.test_harvested_events import make_feed_entry, patch_feed


def entry(event_id: int, days_ahead: int, **overrides) -> dict:
    start = datetime.combine(date.today() + timedelta(days=days_ahead), time(15, 0))
    fields: dict = {
        "eventID": event_id,
        "seriesID": None,
        "startDateTime": start.isoformat(),
        "endDateTime": (start + timedelta(hours=2)).isoformat(),
    }
    fields.update(overrides)
    return make_feed_entry(**fields)


async def harvest(db: AsyncSession, monkeypatch, payload: list[dict]) -> None:
    patch_feed(monkeypatch, payload)
    await harvested_event_service.harvest_trumba_events(db)


async def get_event(db: AsyncSession, source_id: str) -> HarvestedEvent:
    return (
        await db.execute(
            sa.select(HarvestedEvent).where(HarvestedEvent.Source_Id == source_id)
        )
    ).scalar_one()


class TestOpsEndpointAuthorization:
    @pytest.mark.parametrize("headers_fixture", ["ops_headers", "staff_headers"])
    async def test_allows_ops_and_staff(
        self, client: AsyncClient, request, headers_fixture: str
    ):
        headers = request.getfixturevalue(headers_fixture)
        response = await client.get("/api/v1/ops/harvested-events", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"Items": [], "Total": 0}

    async def test_rejects_public(self, client: AsyncClient):
        response = await client.get("/api/v1/ops/harvested-events")
        assert response.status_code == 403

    async def test_rejects_slc_role(self, client: AsyncClient, slc_headers):
        response = await client.get(
            "/api/v1/ops/harvested-events", headers=slc_headers
        )
        assert response.status_code == 403

    async def test_rejects_ops_role_on_slc_endpoint(
        self, client: AsyncClient, ops_headers
    ):
        response = await client.get(
            "/api/v1/slc/harvested-events", headers=ops_headers
        )
        assert response.status_code == 403


class TestListOpsEvents:
    async def test_lists_events_with_default_ops_status(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch
    ):
        await harvest(db, monkeypatch, [entry(1, 10), entry(2, 3)])

        response = await client.get(
            "/api/v1/ops/harvested-events", headers=ops_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["Total"] == 2
        assert [item["Source_Id"] for item in body["Items"]] == ["2", "1"]
        assert all(item["Ops_Review_Status"] == "new" for item in body["Items"])

    async def test_response_excludes_slc_lens_fields(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch
    ):
        await harvest(db, monkeypatch, [entry(1, 10)])

        response = await client.get(
            "/api/v1/ops/harvested-events", headers=ops_headers
        )
        item = response.json()["Items"][0]
        assert "SLC_Review_Status" not in item
        assert "Promoted_Submission_Id" not in item
        assert "Upstream_Changed_At" not in item

    async def test_date_and_category_filters(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch
    ):
        await harvest(
            db,
            monkeypatch,
            [
                entry(1, 3),
                entry(2, 40, categoryCalendar="Alumni Relations"),
            ],
        )

        horizon = (date.today() + timedelta(days=30)).isoformat()
        response = await client.get(
            f"/api/v1/ops/harvested-events?date_from={date.today().isoformat()}"
            f"&date_to={horizon}",
            headers=ops_headers,
        )
        assert [item["Source_Id"] for item in response.json()["Items"]] == ["1"]

        response = await client.get(
            "/api/v1/ops/harvested-events?category=Alumni Relations",
            headers=ops_headers,
        )
        assert [item["Source_Id"] for item in response.json()["Items"]] == ["2"]

    async def test_ops_lens_ignores_slc_review_state(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch
    ):
        """SLC dismissing or flagging an event must not change the ops queue."""
        await harvest(db, monkeypatch, [entry(1, 10), entry(2, 12)])
        first = await get_event(db, "1")
        second = await get_event(db, "2")
        await set_review_status(db, first.Id, status="dismissed")
        await set_review_status(db, second.Id, status="flagged")

        response = await client.get(
            "/api/v1/ops/harvested-events", headers=ops_headers
        )
        body = response.json()
        assert body["Total"] == 2
        assert {item["Source_Id"] for item in body["Items"]} == {"1", "2"}
        assert all(item["Ops_Review_Status"] == "new" for item in body["Items"])

    async def test_default_listing_excludes_ops_dismissed(
        self, db: AsyncSession, monkeypatch
    ):
        await harvest(db, monkeypatch, [entry(1, 10), entry(2, 12)])
        event = await get_event(db, "1")
        event.Ops_Review_Status = "dismissed"
        await db.commit()

        items, total = await list_ops_events(db)
        assert total == 1
        assert [item.Source_Id for item in items] == ["2"]

        items, total = await list_ops_events(db, review_status="dismissed")
        assert total == 1
        assert [item.Source_Id for item in items] == ["1"]

    async def test_ops_status_survives_reharvest(
        self, db: AsyncSession, monkeypatch
    ):
        await harvest(db, monkeypatch, [entry(1, 10)])
        event = await get_event(db, "1")
        event.Ops_Review_Status = "reviewed"
        await db.commit()

        await harvest(db, monkeypatch, [entry(1, 10, title="Movie Night (moved)")])

        await db.refresh(event)
        assert event.Ops_Review_Status == "reviewed"


class TestOpsUpstreamBadges:
    async def reviewed_event(self, client, ops_headers, db, monkeypatch, **entry_kwargs):
        """Harvest one event, mark it ops-reviewed, and return its id."""
        await harvest(db, monkeypatch, [entry(1, 10, **entry_kwargs)])
        event_id = (await get_event(db, "1")).Id
        await client.patch(
            f"/api/v1/ops/harvested-events/{event_id}",
            headers=ops_headers,
            json={"Ops_Review_Status": "reviewed"},
        )
        db.expire_all()
        return event_id

    async def test_content_change_badges_reviewed_events_only(
        self, client, ops_headers, db: AsyncSession, monkeypatch
    ):
        await self.reviewed_event(client, ops_headers, db, monkeypatch)
        await harvest(db, monkeypatch, [entry(1, 10, title="Movie Night (moved)"), entry(2, 12)])
        await harvest(db, monkeypatch, [entry(1, 10, title="Movie Night (moved)"), entry(2, 12, title="Second (edited)")])

        first = await get_event(db, "1")
        second = await get_event(db, "2")
        assert first.Ops_Upstream_Changed_At is not None
        assert first.Upstream_Changed_At is None  # SLC lens untouched
        assert second.Ops_Upstream_Changed_At is None  # not reviewed

    async def test_feed_cancellation_badges_reviewed_event(
        self, client, ops_headers, db: AsyncSession, monkeypatch
    ):
        await self.reviewed_event(client, ops_headers, db, monkeypatch)
        await harvest(db, monkeypatch, [entry(1, 10, canceled=True)])

        event = await get_event(db, "1")
        assert event.Is_Canceled is True
        assert event.Ops_Upstream_Changed_At is not None

    async def test_disappearance_cancels_and_badges_ops_reviewed_event(
        self, client, ops_headers, db: AsyncSession, monkeypatch
    ):
        """A reviewed (but not SLC-flagged) event vanishing inside coverage."""
        await self.reviewed_event(client, ops_headers, db, monkeypatch)
        await harvest(db, monkeypatch, [entry(2, 15)])

        event = await get_event(db, "1")
        assert event.Is_Canceled is True
        assert event.Ops_Upstream_Changed_At is not None
        assert event.Upstream_Changed_At is None  # SLC never watched it

    async def test_acknowledgment_is_independent_per_lens(
        self, client, ops_headers, slc_headers, db: AsyncSession, monkeypatch
    ):
        event_id = await self.reviewed_event(client, ops_headers, db, monkeypatch)
        await set_review_status(db, event_id, status="flagged")
        await harvest(db, monkeypatch, [entry(1, 10, title="Movie Night (moved)")])

        event = await get_event(db, "1")
        assert event.Upstream_Changed_At is not None
        assert event.Ops_Upstream_Changed_At is not None

        response = await client.post(
            f"/api/v1/ops/harvested-events/{event_id}/acknowledge-upstream",
            headers=ops_headers,
        )
        assert response.status_code == 200
        assert response.json()["Ops_Upstream_Changed_At"] is None
        await db.refresh(event)
        assert event.Upstream_Changed_At is not None  # SLC badge survives

        response = await client.post(
            f"/api/v1/slc/harvested-events/{event_id}/acknowledge-upstream",
            headers=slc_headers,
        )
        assert response.status_code == 200
        await db.refresh(event)
        assert event.Upstream_Changed_At is None
        assert event.Ops_Upstream_Changed_At is None  # already cleared, untouched

    async def test_unreview_clears_ops_badge(
        self, client, ops_headers, db: AsyncSession, monkeypatch
    ):
        event_id = await self.reviewed_event(client, ops_headers, db, monkeypatch)
        await harvest(db, monkeypatch, [entry(1, 10, title="Movie Night (moved)")])

        response = await client.patch(
            f"/api/v1/ops/harvested-events/{event_id}",
            headers=ops_headers,
            json={"Ops_Review_Status": "new"},
        )
        assert response.json()["Ops_Upstream_Changed_At"] is None

    async def test_acknowledge_requires_ops_or_staff(
        self, client, slc_headers, ops_headers, db: AsyncSession, monkeypatch
    ):
        event_id = await self.reviewed_event(client, ops_headers, db, monkeypatch)
        response = await client.post(
            f"/api/v1/ops/harvested-events/{event_id}/acknowledge-upstream",
            headers=slc_headers,
        )
        assert response.status_code == 403


class TestUpdateOpsEvent:
    async def patch_status(
        self, client: AsyncClient, headers, event_id: str, status: str
    ):
        return await client.patch(
            f"/api/v1/ops/harvested-events/{event_id}",
            headers=headers,
            json={"Ops_Review_Status": status},
        )

    async def test_review_dismiss_and_restore(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch
    ):
        await harvest(db, monkeypatch, [entry(1, 10)])
        event = await get_event(db, "1")

        response = await self.patch_status(client, ops_headers, event.Id, "reviewed")
        assert response.status_code == 200
        assert response.json()["Ops_Review_Status"] == "reviewed"

        response = await self.patch_status(client, ops_headers, event.Id, "dismissed")
        assert response.json()["Ops_Review_Status"] == "dismissed"

        listed = await client.get("/api/v1/ops/harvested-events", headers=ops_headers)
        assert listed.json()["Total"] == 0

        response = await self.patch_status(client, ops_headers, event.Id, "new")
        assert response.json()["Ops_Review_Status"] == "new"

        listed = await client.get("/api/v1/ops/harvested-events", headers=ops_headers)
        assert listed.json()["Total"] == 1

    async def test_rejects_unknown_status(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch
    ):
        await harvest(db, monkeypatch, [entry(1, 10)])
        event = await get_event(db, "1")
        response = await self.patch_status(client, ops_headers, event.Id, "flagged")
        assert response.status_code == 422

    async def test_missing_event_returns_404(
        self, client: AsyncClient, ops_headers
    ):
        response = await self.patch_status(client, ops_headers, "no-such-id", "reviewed")
        assert response.status_code == 404

    async def test_requires_ops_or_staff_role(
        self, client: AsyncClient, slc_headers, db: AsyncSession, monkeypatch
    ):
        await harvest(db, monkeypatch, [entry(1, 10)])
        event = await get_event(db, "1")

        response = await client.patch(
            f"/api/v1/ops/harvested-events/{event.Id}",
            json={"Ops_Review_Status": "reviewed"},
        )
        assert response.status_code == 403

        response = await self.patch_status(client, slc_headers, event.Id, "reviewed")
        assert response.status_code == 403

    async def test_ops_transitions_leave_slc_state_untouched(
        self, client: AsyncClient, ops_headers, db: AsyncSession, monkeypatch
    ):
        """Dismissing on the ops lens must not withdraw an SLC promotion."""
        await harvest(db, monkeypatch, [entry(1, 10)])
        event = await get_event(db, "1")
        await set_review_status(db, event.Id, status="flagged")
        await db.refresh(event)
        promoted_id = event.Promoted_Submission_Id
        assert promoted_id is not None

        await self.patch_status(client, ops_headers, event.Id, "dismissed")

        await db.refresh(event)
        assert event.SLC_Review_Status == "flagged"
        assert event.Promoted_Submission_Id == promoted_id
        assert event.Ops_Review_Status == "dismissed"
