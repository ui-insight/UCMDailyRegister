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
