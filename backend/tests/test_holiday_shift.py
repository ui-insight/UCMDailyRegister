"""Regression tests for holiday-shifted publish dates (#514).

TDR's summer schedule publishes on Mondays with Holiday_Shift_Enabled, so a
blacked-out Monday moves that week's edition to Tuesday. The calendar asks for
a range of dates and was offered the Tuesday, but submit validation, assembly
and recurring messages ask about one day at a time and were told the Tuesday
was not a publish date. These tests check every caller gets the same answer.

All dates and content are synthetic. 2027-06-14 is a summer Monday with a
blackout added by the test.
"""

from datetime import date

import pytest
from freezegun import freeze_time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import seed
from app.models.blackout_date import BlackoutDate
from app.models.section import NewsletterSection
from app.services import schedule_service
from tests.conftest import make_submission_data

BLACKED_OUT_MONDAY = "2027-06-14"
SHIFTED_TUESDAY = "2027-06-15"
ORDINARY_WEDNESDAY = "2027-06-16"


async def _seed_summer_blackout(db: AsyncSession) -> None:
    await seed.seed_schedule_configs(db)
    db.add(
        BlackoutDate(
            Blackout_Date=date.fromisoformat(BLACKED_OUT_MONDAY),
            Newsletter_Type="tdr",
            Description="Synthetic closure",
        )
    )
    await db.commit()


async def _seed_tdr_section(db: AsyncSession) -> None:
    db.add(
        NewsletterSection(
            Id="tdr-employee-news",
            Newsletter_Type="tdr",
            Name="Employee News",
            Slug="employee-news",
            Display_Order=1,
            Is_Active=True,
        )
    )
    await db.commit()


@pytest.mark.asyncio
@freeze_time("2027-06-01 19:00:00")
class TestHolidayShiftedPublishDates:
    async def test_single_day_query_matches_range_query(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await _seed_summer_blackout(db)

        week = await client.get(
            "/api/v1/schedule/valid-dates",
            params={"from": "2027-06-14", "to": "2027-06-20", "newsletter_type": "tdr"},
        )
        single = await client.get(
            "/api/v1/schedule/valid-dates",
            params={"from": SHIFTED_TUESDAY, "to": SHIFTED_TUESDAY, "newsletter_type": "tdr"},
        )
        blacked_out = await client.get(
            "/api/v1/schedule/valid-dates",
            params={
                "from": BLACKED_OUT_MONDAY,
                "to": BLACKED_OUT_MONDAY,
                "newsletter_type": "tdr",
            },
        )

        expected = [{"date": SHIFTED_TUESDAY, "newsletters": ["tdr"]}]
        assert week.json()["dates"] == expected
        assert single.json()["dates"] == expected
        assert blacked_out.json()["dates"] == []

    async def test_range_starting_after_blackout_does_not_leak_earlier_dates(
        self,
        db: AsyncSession,
    ):
        await _seed_summer_blackout(db)

        # The scan looks back a week to find shifts; the Monday before
        # (2027-06-07) is a normal edition and must stay out of this range.
        dates = await schedule_service.get_valid_publication_dates(
            db, date(2027, 6, 15), date(2027, 6, 28), "tdr"
        )

        assert [entry["date"] for entry in dates] == [
            date(2027, 6, 15),
            date(2027, 6, 21),
            date(2027, 6, 28),
        ]

    async def test_submit_accepts_shifted_date_and_rejects_other_weekdays(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await _seed_summer_blackout(db)

        accepted = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Schedule_Requests=[{"Requested_Date": SHIFTED_TUESDAY}],
            ),
        )
        rejected = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Schedule_Requests=[{"Requested_Date": ORDINARY_WEDNESDAY}],
            ),
        )

        assert accepted.status_code == 201, accepted.text
        assert rejected.status_code == 422
        assert rejected.json()["detail"] == "TDR publishes on Mondays only"

    async def test_assembly_places_submission_on_shifted_date(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
    ):
        await _seed_summer_blackout(db)
        await _seed_tdr_section(db)

        create_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Headline="Shifted edition item",
                Schedule_Requests=[{"Requested_Date": SHIFTED_TUESDAY}],
            ),
        )
        assert create_resp.status_code == 201, create_resp.text
        submission_id = create_resp.json()["Id"]
        await client.patch(
            f"/api/v1/submissions/{submission_id}",
            json={"Status": "approved"},
            headers=staff_headers,
        )

        assemble_resp = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": SHIFTED_TUESDAY},
            headers=staff_headers,
        )

        assert assemble_resp.status_code == 200
        items = assemble_resp.json()["Items"]
        assert [item["Submission_Id"] for item in items] == [submission_id]

    async def test_recurring_message_placed_on_shifted_date(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
    ):
        await _seed_summer_blackout(db)
        await _seed_tdr_section(db)

        create_resp = await client.post(
            "/api/v1/recurring-messages",
            json={
                "Newsletter_Type": "tdr",
                "Section_Id": "tdr-employee-news",
                "Headline": "Synthetic campaign week",
                "Body": "This message runs in every edition this week.",
                "Start_Date": BLACKED_OUT_MONDAY,
                "Recurrence_Type": "date_range",
                "Recurrence_Interval": 1,
                "End_Date": "2027-06-18",
            },
            headers=staff_headers,
        )
        assert create_resp.status_code == 201, create_resp.text
        message_id = create_resp.json()["Id"]

        assemble_resp = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": SHIFTED_TUESDAY},
            headers=staff_headers,
        )

        assert assemble_resp.status_code == 200
        external_items = assemble_resp.json()["External_Items"]
        assert [item["Source_Id"] for item in external_items] == [message_id]
