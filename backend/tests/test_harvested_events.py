"""Tests for the Trumba harvest service and SLC triage endpoints."""

from datetime import date, datetime, time, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.harvested_event import HarvestedEvent
from app.models.submission import Submission
from app.services import harvested_event_service
from app.services.harvested_event_service import (
    DESCRIPTION_MAX_CHARS,
    TRUMBA_SOURCE_TYPE,
    _flatten_description,
    harvest_trumba_events,
    list_harvested_events,
    parse_trumba_feed,
    plan_trumba_harvest,
    set_review_status,
)


def make_feed_entry(**overrides) -> dict:
    """Return a valid Trumba JSON feed entry with sensible defaults."""
    entry = {
        "eventID": 204106464,
        "seriesID": 204106400,
        "title": "Screen on the Green",
        "description": "<p>Bring your <b>blankets</b> for a movie night.</p>",
        "location": "Tower Lawn - Theophilus Tower - Main Campus",
        "locationType": "In-Person",
        "webLink": "",
        "startDateTime": "2026-09-04T20:30:00",
        "endDateTime": "2026-09-04T22:30:00",
        "allDay": False,
        "canceled": False,
        "permaLinkUrl": "https://www.uidaho.edu/events?trumbaEmbed=view%3Devent%26eventid%3D204106464",
        "categoryCalendar": "Student Affairs|Dept. of Student Involvement",
    }
    entry.update(overrides)
    return entry


def patch_feed(monkeypatch: pytest.MonkeyPatch, payload: list[dict]) -> None:
    """Replace the live feed fetch with a canned payload."""

    async def fake_fetch() -> list[dict]:
        return payload

    monkeypatch.setattr(harvested_event_service, "fetch_trumba_feed", fake_fetch)


class TestParseTrumbaFeed:
    def test_parses_valid_entry(self):
        events, skipped = parse_trumba_feed([make_feed_entry()])
        assert skipped == 0
        assert len(events) == 1
        event = events[0]
        assert event.source_id == "204106464"
        assert event.series_id == "204106400"
        assert event.title == "Screen on the Green"
        assert event.description == "Bring your blankets for a movie night."
        assert event.location == "Tower Lawn - Theophilus Tower - Main Campus"
        assert event.event_start == datetime(2026, 9, 4, 20, 30)
        assert event.event_end == datetime(2026, 9, 4, 22, 30)
        assert event.category_path == "Student Affairs|Dept. of Student Involvement"
        assert event.url and "204106464" in event.url
        assert event.canceled is False
        assert event.all_day is False

    def test_skips_entries_missing_required_fields(self):
        payload = [
            make_feed_entry(eventID=None),
            make_feed_entry(title="   "),
            make_feed_entry(startDateTime="not-a-date"),
            make_feed_entry(startDateTime=None),
            make_feed_entry(eventID=999),
        ]
        events, skipped = parse_trumba_feed(payload)
        assert skipped == 4
        assert [event.source_id for event in events] == ["999"]

    def test_collapses_duplicate_event_ids(self):
        payload = [
            make_feed_entry(title="First copy"),
            make_feed_entry(title="Second copy"),
        ]
        events, skipped = parse_trumba_feed(payload)
        assert skipped == 0
        assert len(events) == 1
        assert events[0].title == "Second copy"

    def test_canceled_and_all_day_flags(self):
        events, _ = parse_trumba_feed(
            [make_feed_entry(canceled=True, allDay=True, endDateTime=None)]
        )
        assert events[0].canceled is True
        assert events[0].all_day is True
        assert events[0].event_end is None

    def test_truncates_overlong_location(self):
        events, _ = parse_trumba_feed([make_feed_entry(location="x" * 300)])
        assert events[0].location is not None
        assert len(events[0].location) == 255

    def test_unescapes_html_entities_in_title(self):
        events, _ = parse_trumba_feed(
            [make_feed_entry(title="Screen on the Green: &#39;Project  Hail Mary&#39;")]
        )
        assert events[0].title == "Screen on the Green: 'Project Hail Mary'"

    def test_strips_html_from_location(self):
        events, _ = parse_trumba_feed(
            [
                make_feed_entry(
                    location='<a href="https://maps.example.com">Bruce Pitman Center</a>'
                )
            ]
        )
        assert events[0].location == "Bruce Pitman Center"


class TestHarvestUpsert:
    async def test_harvest_is_idempotent(self, db: AsyncSession, monkeypatch):
        payload = [
            make_feed_entry(),
            make_feed_entry(eventID=111, title="Volleyball vs. WSU", seriesID=None),
        ]
        patch_feed(monkeypatch, payload)

        first = await harvest_trumba_events(db)
        assert first.fetched == 2
        assert first.created == 2
        assert first.updated == 0

        second = await harvest_trumba_events(db)
        assert second.created == 0
        assert second.updated == 0
        assert second.unchanged == 2

        total = (
            await db.execute(sa.select(sa.func.count()).select_from(HarvestedEvent))
        ).scalar_one()
        assert total == 2

    async def test_upstream_change_updates_row_and_preserves_review_status(
        self, db: AsyncSession, monkeypatch
    ):
        patch_feed(monkeypatch, [make_feed_entry()])
        await harvest_trumba_events(db)

        row = (await db.execute(sa.select(HarvestedEvent))).scalar_one()
        row.SLC_Review_Status = "flagged"
        await db.commit()
        original_hash = row.Content_Hash

        patch_feed(
            monkeypatch,
            [make_feed_entry(location="Moved to the Kibbie Dome", canceled=True)],
        )
        summary = await harvest_trumba_events(db)
        assert summary.updated == 1
        assert summary.created == 0

        row = (await db.execute(sa.select(HarvestedEvent))).scalar_one()
        assert row.Location == "Moved to the Kibbie Dome"
        assert row.Is_Canceled is True
        assert row.Content_Hash != original_hash
        assert row.SLC_Review_Status == "flagged"

    async def test_skipped_entries_are_counted(self, db: AsyncSession, monkeypatch):
        patch_feed(monkeypatch, [make_feed_entry(), make_feed_entry(eventID=None)])
        summary = await harvest_trumba_events(db)
        assert summary.fetched == 2
        assert summary.created == 1
        assert summary.skipped == 1


class TestListHarvestedEvents:
    async def seed_events(self, db: AsyncSession) -> None:
        db.add_all(
            [
                HarvestedEvent(
                    Source_Type=TRUMBA_SOURCE_TYPE,
                    Source_Id="1",
                    Title="Intramural Kickoff",
                    Description="Sports.",
                    Event_Start=datetime(2026, 9, 1, 17, 0),
                    Category_Path="Student Affairs|Campus Recreation|Intramurals",
                    Content_Hash="a" * 64,
                ),
                HarvestedEvent(
                    Source_Type=TRUMBA_SOURCE_TYPE,
                    Source_Id="2",
                    Title="Chamber Music Series",
                    Description="Music.",
                    Event_Start=datetime(2026, 9, 17, 19, 30),
                    Category_Path="University of Idaho - CLASS",
                    Content_Hash="b" * 64,
                    SLC_Review_Status="flagged",
                ),
                HarvestedEvent(
                    Source_Type=TRUMBA_SOURCE_TYPE,
                    Source_Id="3",
                    Title="Student Affairs Open House",
                    Description="Open house.",
                    Event_Start=datetime(2026, 10, 2, 10, 0),
                    Category_Path="Student Affairs",
                    Content_Hash="c" * 64,
                ),
            ]
        )
        await db.commit()

    async def test_date_range_filter(self, db: AsyncSession):
        await self.seed_events(db)
        items, total = await list_harvested_events(
            db, date_from=datetime(2026, 9, 1).date(), date_to=datetime(2026, 9, 30).date()
        )
        assert total == 2
        assert [item.Source_Id for item in items] == ["1", "2"]

    async def test_category_filter_matches_branch(self, db: AsyncSession):
        await self.seed_events(db)
        items, total = await list_harvested_events(db, category="Student Affairs")
        assert total == 2
        assert {item.Source_Id for item in items} == {"1", "3"}

    async def test_review_status_filter(self, db: AsyncSession):
        await self.seed_events(db)
        items, total = await list_harvested_events(db, review_status="flagged")
        assert total == 1
        assert items[0].Source_Id == "2"

    async def test_default_listing_excludes_dismissed(self, db: AsyncSession):
        await self.seed_events(db)
        db.add(
            HarvestedEvent(
                Source_Type=TRUMBA_SOURCE_TYPE,
                Source_Id="4",
                Title="Dismissed Event",
                Description="Not for SLC.",
                Event_Start=datetime(2026, 9, 5, 9, 0),
                Content_Hash="d" * 64,
                SLC_Review_Status="dismissed",
            )
        )
        await db.commit()

        _, total_default = await list_harvested_events(db)
        assert total_default == 3

        items, total_dismissed = await list_harvested_events(
            db, review_status="dismissed"
        )
        assert total_dismissed == 1
        assert items[0].Source_Id == "4"


class TestSLCEndpointAuthorization:
    async def test_public_cannot_list_or_harvest(self, client):
        list_response = await client.get("/api/v1/slc/harvested-events")
        assert list_response.status_code == 403
        harvest_response = await client.post("/api/v1/slc/harvest")
        assert harvest_response.status_code == 403

    @pytest.mark.parametrize("headers_fixture", ["slc_headers", "staff_headers"])
    async def test_slc_and_staff_can_list(self, client, request, headers_fixture):
        headers = request.getfixturevalue(headers_fixture)
        response = await client.get("/api/v1/slc/harvested-events", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body == {"Items": [], "Total": 0}

    async def test_harvest_endpoint_returns_summary(
        self, client, slc_headers, monkeypatch
    ):
        patch_feed(monkeypatch, [make_feed_entry()])
        response = await client.post("/api/v1/slc/harvest", headers=slc_headers)
        assert response.status_code == 200
        assert response.json() == {
            "Fetched": 1,
            "Created": 1,
            "Updated": 0,
            "Unchanged": 0,
            "Skipped": 0,
            "Canceled": 0,
        }

        listed = await client.get("/api/v1/slc/harvested-events", headers=slc_headers)
        assert listed.status_code == 200
        body = listed.json()
        assert body["Total"] == 1
        assert body["Items"][0]["Title"] == "Screen on the Green"
        assert body["Items"][0]["SLC_Review_Status"] == "new"

    async def test_harvest_feed_failure_returns_502(
        self, client, slc_headers, monkeypatch
    ):
        async def failing_fetch() -> list[dict]:
            raise ValueError("Trumba feed did not return a JSON array of events.")

        monkeypatch.setattr(
            harvested_event_service, "fetch_trumba_feed", failing_fetch
        )
        response = await client.post("/api/v1/slc/harvest", headers=slc_headers)
        assert response.status_code == 502


class TestFlattenDescription:
    def test_collapses_newlines_and_whitespace(self):
        assert (
            _flatten_description("Line one.\n\nLine  two.\tEnd.")
            == "Line one. Line two. End."
        )

    def test_short_description_is_unchanged(self):
        assert _flatten_description("A short blurb.") == "A short blurb."

    def test_caps_overlong_description_at_a_word_boundary(self):
        flat = _flatten_description("word " * 300)
        assert len(flat) <= DESCRIPTION_MAX_CHARS + 1
        assert flat.endswith("word…")


FUTURE_DATE = date.today() + timedelta(days=30)


async def seed_harvested_event(db: AsyncSession, **overrides) -> HarvestedEvent:
    """Insert one harvested event with sensible defaults and return it."""
    values = {
        "Source_Type": TRUMBA_SOURCE_TYPE,
        "Source_Id": "204106464",
        "Source_Url": "https://www.uidaho.edu/events?trumbaEmbed=view%3Devent%26eventid%3D204106464",
        "Title": "Screen on the Green",
        "Description": "A free, family-friendly outdoor movie night.",
        "Location": "Tower Lawn",
        "Event_Start": datetime.combine(FUTURE_DATE, time(20, 30)),
        "Event_End": datetime.combine(FUTURE_DATE, time(22, 30)),
        "Category_Path": "Student Affairs|Dept. of Student Involvement",
        "Content_Hash": "a" * 64,
    }
    values.update(overrides)
    event = HarvestedEvent(**values)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


class TestTriageActions:
    async def patch_status(
        self, client, headers, event_id: str, status: str, classification=None
    ):
        payload = {"SLC_Review_Status": status}
        if classification is not None:
            payload["Event_Classification"] = classification
        return await client.patch(
            f"/api/v1/slc/harvested-events/{event_id}", headers=headers, json=payload
        )

    async def count_submissions(self, db: AsyncSession) -> int:
        return (
            await db.execute(sa.select(sa.func.count()).select_from(Submission))
        ).scalar_one()

    async def test_flag_promotes_event_onto_slc_calendar(
        self, client, slc_headers, db: AsyncSession
    ):
        event = await seed_harvested_event(db)
        response = await self.patch_status(
            client, slc_headers, event.Id, "flagged", "strategic"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["SLC_Review_Status"] == "flagged"
        assert body["Promoted_Submission_Id"]
        assert body["Promoted_Classification"] == "strategic"

        calendar = await client.get(
            "/api/v1/submissions/",
            headers=slc_headers,
            params={
                "slc_calendar_only": "true",
                "date_from": FUTURE_DATE.isoformat(),
                "date_to": FUTURE_DATE.isoformat(),
            },
        )
        assert calendar.status_code == 200
        items = calendar.json()["Items"]
        assert len(items) == 1
        promoted = items[0]
        assert promoted["Original_Headline"] == "Screen on the Green"
        assert promoted["Event_Classification"] == "strategic"
        assert promoted["Occurrence_Dates"] == [FUTURE_DATE.isoformat()]
        assert "Location: Tower Lawn" in promoted["Original_Body"]
        assert (
            "Description: A free, family-friendly outdoor movie night."
            in promoted["Original_Body"]
        )
        assert "Event page: https://www.uidaho.edu/events" in promoted["Original_Body"]

    async def test_multi_day_event_promotes_as_date_range(
        self, client, slc_headers, db: AsyncSession
    ):
        end_date = FUTURE_DATE + timedelta(days=2)
        event = await seed_harvested_event(
            db, Event_End=datetime.combine(end_date, time(17, 0))
        )
        response = await self.patch_status(client, slc_headers, event.Id, "flagged")
        assert response.status_code == 200

        calendar = await client.get(
            "/api/v1/submissions/",
            headers=slc_headers,
            params={
                "slc_calendar_only": "true",
                "date_from": FUTURE_DATE.isoformat(),
                "date_to": end_date.isoformat(),
            },
        )
        items = calendar.json()["Items"]
        assert len(items) == 1
        assert items[0]["Occurrence_Dates"] == [
            (FUTURE_DATE + timedelta(days=offset)).isoformat() for offset in range(3)
        ]

    async def test_flagging_is_idempotent(self, client, slc_headers, db: AsyncSession):
        event = await seed_harvested_event(db)
        first = await self.patch_status(client, slc_headers, event.Id, "flagged")
        second = await self.patch_status(
            client, slc_headers, event.Id, "flagged", "signature"
        )
        assert second.status_code == 200
        assert (
            second.json()["Promoted_Submission_Id"]
            == first.json()["Promoted_Submission_Id"]
        )
        assert second.json()["Promoted_Classification"] == "signature"
        assert await self.count_submissions(db) == 1

        submission_id = second.json()["Promoted_Submission_Id"]
        submission = await db.get(Submission, submission_id)
        assert submission is not None
        assert submission.Event_Classification == "signature"

    async def test_reflag_refreshes_promoted_body(
        self, client, slc_headers, db: AsyncSession
    ):
        event = await seed_harvested_event(db)
        first = await self.patch_status(client, slc_headers, event.Id, "flagged")
        assert first.status_code == 200

        event.Description = "Now featuring a live band before the movie."
        await db.commit()

        second = await self.patch_status(
            client, slc_headers, event.Id, "flagged", "strategic"
        )
        assert second.status_code == 200
        submission = await db.get(
            Submission, second.json()["Promoted_Submission_Id"]
        )
        assert submission is not None
        assert (
            "Description: Now featuring a live band before the movie."
            in submission.Original_Body
        )

    async def test_reharvest_preserves_promotion(
        self, client, slc_headers, db: AsyncSession, monkeypatch
    ):
        start = datetime.combine(FUTURE_DATE, time(20, 30))
        patch_feed(
            monkeypatch,
            [make_feed_entry(startDateTime=start.isoformat(), endDateTime=None)],
        )
        await client.post("/api/v1/slc/harvest", headers=slc_headers)
        event = (await db.execute(sa.select(HarvestedEvent))).scalar_one()
        await self.patch_status(client, slc_headers, event.Id, "flagged")

        patch_feed(
            monkeypatch,
            [
                make_feed_entry(
                    startDateTime=start.isoformat(),
                    endDateTime=None,
                    location="Moved to the Kibbie Dome",
                )
            ],
        )
        await client.post("/api/v1/slc/harvest", headers=slc_headers)

        listed = await client.get(
            "/api/v1/slc/harvested-events", headers=slc_headers
        )
        items = listed.json()["Items"]
        assert len(items) == 1
        assert items[0]["SLC_Review_Status"] == "flagged"
        assert items[0]["Promoted_Submission_Id"]
        assert await self.count_submissions(db) == 1

    async def test_unflag_withdraws_promoted_submission(
        self, client, slc_headers, db: AsyncSession
    ):
        event = await seed_harvested_event(db)
        flagged = await self.patch_status(client, slc_headers, event.Id, "flagged")
        submission_id = flagged.json()["Promoted_Submission_Id"]

        response = await self.patch_status(client, slc_headers, event.Id, "new")
        assert response.status_code == 200
        assert response.json()["SLC_Review_Status"] == "new"
        assert response.json()["Promoted_Submission_Id"] is None
        assert await db.get(Submission, submission_id) is None

    async def test_dismiss_from_flagged_withdraws_and_hides(
        self, client, slc_headers, db: AsyncSession
    ):
        event = await seed_harvested_event(db)
        await self.patch_status(client, slc_headers, event.Id, "flagged")

        response = await self.patch_status(client, slc_headers, event.Id, "dismissed")
        assert response.status_code == 200
        assert response.json()["Promoted_Submission_Id"] is None
        assert await self.count_submissions(db) == 0

        default_list = await client.get(
            "/api/v1/slc/harvested-events", headers=slc_headers
        )
        assert default_list.json()["Total"] == 0

        dismissed_list = await client.get(
            "/api/v1/slc/harvested-events",
            headers=slc_headers,
            params={"review_status": "dismissed"},
        )
        assert dismissed_list.json()["Total"] == 1

    async def test_invalid_status_rejected(self, client, slc_headers, db: AsyncSession):
        event = await seed_harvested_event(db)
        response = await self.patch_status(client, slc_headers, event.Id, "archived")
        assert response.status_code == 422

    async def test_patch_requires_slc_or_staff(self, client, db: AsyncSession):
        event = await seed_harvested_event(db)
        response = await client.patch(
            f"/api/v1/slc/harvested-events/{event.Id}",
            json={"SLC_Review_Status": "flagged"},
        )
        assert response.status_code == 403

    async def test_patch_unknown_event_returns_404(self, client, slc_headers):
        response = await self.patch_status(
            client, slc_headers, "does-not-exist", "flagged"
        )
        assert response.status_code == 404


class TestUpstreamChangeDetection:
    def entry(self, event_id: int, days_ahead: int, **overrides) -> dict:
        """A feed entry with a dynamic future date, so coverage math holds."""
        start = datetime.combine(
            date.today() + timedelta(days=days_ahead), time(15, 0)
        )
        fields: dict = {
            "eventID": event_id,
            "seriesID": None,
            "startDateTime": start.isoformat(),
            "endDateTime": (start + timedelta(hours=2)).isoformat(),
        }
        fields.update(overrides)
        return make_feed_entry(**fields)

    async def harvest(self, client, slc_headers, monkeypatch, payload) -> dict:
        patch_feed(monkeypatch, payload)
        response = await client.post("/api/v1/slc/harvest", headers=slc_headers)
        assert response.status_code == 200
        return response.json()

    async def get_event(self, client, slc_headers, source_id: str) -> dict:
        response = await client.get(
            "/api/v1/slc/harvested-events",
            headers=slc_headers,
            params={"limit": 500},
        )
        assert response.status_code == 200
        for item in response.json()["Items"]:
            if item["Source_Id"] == source_id:
                return item
        raise AssertionError(f"source id {source_id} not in listing")

    async def flag(self, client, slc_headers, source_id: str) -> dict:
        event = await self.get_event(client, slc_headers, source_id)
        response = await client.patch(
            f"/api/v1/slc/harvested-events/{event['Id']}",
            headers=slc_headers,
            json={"SLC_Review_Status": "flagged"},
        )
        assert response.status_code == 200
        return response.json()

    async def test_upstream_edit_badges_and_resyncs_promoted_submission(
        self, client, slc_headers, db: AsyncSession, monkeypatch
    ):
        await self.harvest(client, slc_headers, monkeypatch, [self.entry(1, 10)])
        flagged = await self.flag(client, slc_headers, "1")
        assert flagged["Upstream_Changed_At"] is None

        await self.harvest(
            client,
            slc_headers,
            monkeypatch,
            [
                self.entry(
                    1,
                    12,
                    title="Screen on the Green (moved)",
                    description="<p>Now at the Kibbie Dome.</p>",
                )
            ],
        )

        event = await self.get_event(client, slc_headers, "1")
        assert event["Upstream_Changed_At"] is not None
        assert event["Is_Canceled"] is False

        submission = await db.get(Submission, event["Promoted_Submission_Id"])
        assert submission is not None
        assert submission.Original_Headline == "Screen on the Green (moved)"
        assert "Description: Now at the Kibbie Dome." in submission.Original_Body
        assert submission.Schedule_Requests[0].Requested_Date == (
            date.today() + timedelta(days=12)
        )

    async def test_feed_cancellation_badges_and_marks_promoted_body(
        self, client, slc_headers, db: AsyncSession, monkeypatch
    ):
        await self.harvest(client, slc_headers, monkeypatch, [self.entry(1, 10)])
        await self.flag(client, slc_headers, "1")

        summary = await self.harvest(
            client, slc_headers, monkeypatch, [self.entry(1, 10, canceled=True)]
        )
        assert summary["Canceled"] == 1

        event = await self.get_event(client, slc_headers, "1")
        assert event["Is_Canceled"] is True
        assert event["Upstream_Changed_At"] is not None
        submission = await db.get(Submission, event["Promoted_Submission_Id"])
        assert submission is not None
        assert "Canceled: yes" in submission.Original_Body

    async def test_flagged_event_missing_from_feed_is_canceled(
        self, client, slc_headers, monkeypatch
    ):
        await self.harvest(
            client,
            slc_headers,
            monkeypatch,
            [self.entry(1, 10), self.entry(2, 15), self.entry(3, 12)],
        )
        await self.flag(client, slc_headers, "1")

        summary = await self.harvest(
            client, slc_headers, monkeypatch, [self.entry(2, 15)]
        )
        assert summary["Updated"] == 1
        assert summary["Canceled"] == 1

        event = await self.get_event(client, slc_headers, "1")
        assert event["Is_Canceled"] is True
        assert event["Upstream_Changed_At"] is not None
        # Disappearance only matters for flagged events.
        other = await self.get_event(client, slc_headers, "3")
        assert other["Is_Canceled"] is False
        assert other["Upstream_Changed_At"] is None

    async def test_event_beyond_feed_coverage_is_not_canceled(
        self, client, slc_headers, monkeypatch
    ):
        await self.harvest(
            client, slc_headers, monkeypatch, [self.entry(1, 15), self.entry(2, 5)]
        )
        await self.flag(client, slc_headers, "1")

        # The new fetch only covers +5 days; event 1 at +15 days is beyond it.
        await self.harvest(client, slc_headers, monkeypatch, [self.entry(2, 5)])

        event = await self.get_event(client, slc_headers, "1")
        assert event["Is_Canceled"] is False
        assert event["Upstream_Changed_At"] is None

    async def test_reappearing_event_is_restored(
        self, client, slc_headers, db: AsyncSession, monkeypatch
    ):
        both = [self.entry(1, 10), self.entry(2, 15)]
        await self.harvest(client, slc_headers, monkeypatch, both)
        await self.flag(client, slc_headers, "1")
        await self.harvest(client, slc_headers, monkeypatch, [self.entry(2, 15)])
        await self.harvest(client, slc_headers, monkeypatch, both)

        event = await self.get_event(client, slc_headers, "1")
        assert event["Is_Canceled"] is False
        assert event["Upstream_Changed_At"] is not None
        submission = await db.get(Submission, event["Promoted_Submission_Id"])
        assert submission is not None
        assert "Canceled: yes" not in submission.Original_Body

    async def test_harvest_resyncs_stale_promoted_body(
        self, client, slc_headers, db: AsyncSession, monkeypatch
    ):
        await self.harvest(client, slc_headers, monkeypatch, [self.entry(1, 10)])
        flagged = await self.flag(client, slc_headers, "1")

        submission = await db.get(Submission, flagged["Promoted_Submission_Id"])
        assert submission is not None
        submission.Original_Headline = "Stale title"
        submission.Original_Body = "stale"
        await db.commit()

        summary = await self.harvest(
            client, slc_headers, monkeypatch, [self.entry(1, 10)]
        )
        assert summary["Unchanged"] == 1

        await db.refresh(submission)
        assert submission.Original_Headline == "Screen on the Green"
        assert "Description:" in submission.Original_Body
        # A resync alone is not an upstream change; no badge.
        event = await self.get_event(client, slc_headers, "1")
        assert event["Upstream_Changed_At"] is None

    async def test_acknowledge_clears_badge(
        self, client, slc_headers, monkeypatch
    ):
        await self.harvest(client, slc_headers, monkeypatch, [self.entry(1, 10)])
        await self.flag(client, slc_headers, "1")
        await self.harvest(
            client, slc_headers, monkeypatch, [self.entry(1, 10, title="New title")]
        )
        event = await self.get_event(client, slc_headers, "1")
        assert event["Upstream_Changed_At"] is not None

        response = await client.post(
            f"/api/v1/slc/harvested-events/{event['Id']}/acknowledge-upstream",
            headers=slc_headers,
        )
        assert response.status_code == 200
        assert response.json()["Upstream_Changed_At"] is None

    async def test_unflag_clears_badge(self, client, slc_headers, monkeypatch):
        await self.harvest(client, slc_headers, monkeypatch, [self.entry(1, 10)])
        await self.flag(client, slc_headers, "1")
        await self.harvest(
            client, slc_headers, monkeypatch, [self.entry(1, 10, title="New title")]
        )
        event = await self.get_event(client, slc_headers, "1")
        assert event["Upstream_Changed_At"] is not None

        response = await client.patch(
            f"/api/v1/slc/harvested-events/{event['Id']}",
            headers=slc_headers,
            json={"SLC_Review_Status": "new"},
        )
        assert response.status_code == 200
        assert response.json()["Upstream_Changed_At"] is None

    async def test_acknowledge_unknown_event_returns_404(self, client, slc_headers):
        response = await client.post(
            "/api/v1/slc/harvested-events/does-not-exist/acknowledge-upstream",
            headers=slc_headers,
        )
        assert response.status_code == 404

    async def test_acknowledge_requires_slc_or_staff(self, client, db: AsyncSession):
        event = await seed_harvested_event(db)
        response = await client.post(
            f"/api/v1/slc/harvested-events/{event.Id}/acknowledge-upstream"
        )
        assert response.status_code == 403


class TestPlanHarvest:
    def entry(self, event_id: int, days_ahead: int, **overrides) -> dict:
        start = datetime.combine(
            date.today() + timedelta(days=days_ahead), time(15, 0)
        )
        fields: dict = {
            "eventID": event_id,
            "seriesID": None,
            "startDateTime": start.isoformat(),
            "endDateTime": (start + timedelta(hours=2)).isoformat(),
        }
        fields.update(overrides)
        return make_feed_entry(**fields)

    async def test_plan_reports_changes_without_writing(
        self, db: AsyncSession, monkeypatch
    ):
        patch_feed(
            monkeypatch,
            [self.entry(1, 10), self.entry(2, 15, title="Chamber Music")],
        )
        await harvest_trumba_events(db)
        flagged = (
            await db.execute(
                sa.select(HarvestedEvent).where(HarvestedEvent.Source_Id == "1")
            )
        ).scalar_one()
        await set_review_status(db, flagged.Id, status="flagged")

        patch_feed(
            monkeypatch,
            [
                self.entry(2, 15, title="Chamber Music (moved)"),  # would update
                self.entry(3, 12),  # would create
                # entry 1 is missing while inside coverage: would cancel
            ],
        )
        summary = await plan_trumba_harvest(db)
        assert summary.created == 1
        assert summary.updated == 2  # the edit plus the disappearance
        assert summary.canceled == 1  # the disappearance
        assert summary.unchanged == 0

        # Nothing was written: no cancellation, no badge, no new or edited rows.
        await db.refresh(flagged)
        assert flagged.Is_Canceled is False
        assert flagged.Upstream_Changed_At is None
        titles = set(
            (await db.execute(sa.select(HarvestedEvent.Title))).scalars()
        )
        assert titles == {"Screen on the Green", "Chamber Music"}

    async def test_plan_counts_feed_cancellations(
        self, db: AsyncSession, monkeypatch
    ):
        patch_feed(monkeypatch, [self.entry(1, 10)])
        await harvest_trumba_events(db)

        patch_feed(monkeypatch, [self.entry(1, 10, canceled=True)])
        summary = await plan_trumba_harvest(db)
        assert summary.updated == 1
        assert summary.canceled == 1

        row = (await db.execute(sa.select(HarvestedEvent))).scalar_one()
        assert row.Is_Canceled is False
