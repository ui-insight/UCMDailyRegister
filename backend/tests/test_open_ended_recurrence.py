"""Repeating schedules with no end date must not run forever (#477).

Synthetic data only. The legacy rows are inserted straight into the database
because the API now refuses a repeating schedule without an end date.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.section import NewsletterSection
from app.models.submission import Submission, SubmissionScheduleRequest
from app.services import recurrence_service
from tests.conftest import make_submission_data


def _request(**fields) -> SimpleNamespace:
    defaults = {
        "Requested_Date": None,
        "Second_Requested_Date": None,
        "Recurrence_Type": "once",
        "Recurrence_Interval": 1,
        "Recurrence_End_Date": None,
        "Excluded_Dates": [],
    }
    defaults.update(fields)
    return SimpleNamespace(**defaults)


class TestEffectiveRecurrence:
    @pytest.mark.parametrize("recurrence_type", ["weekly", "monthly_date", "monthly_nth_weekday"])
    def test_open_ended_repeat_runs_only_on_its_requested_date(self, recurrence_type):
        request = _request(Requested_Date=date(2026, 9, 14), Recurrence_Type=recurrence_type)

        occurrences = recurrence_service.expand_schedule_request(
            request, date(2026, 9, 1), date(2026, 12, 31)
        )

        assert occurrences == [date(2026, 9, 14)]

    def test_open_ended_repeat_keeps_its_second_date(self):
        request = _request(
            Requested_Date=date(2026, 9, 8),
            Second_Requested_Date=date(2026, 9, 15),
            Recurrence_Type="weekly",
        )

        occurrences = recurrence_service.expand_schedule_request(
            request, date(2026, 9, 1), date(2026, 12, 31)
        )

        assert occurrences == [date(2026, 9, 8), date(2026, 9, 15)]

    def test_weekly_with_end_date_still_repeats_until_it_ends(self):
        request = _request(
            Requested_Date=date(2026, 9, 14),
            Recurrence_Type="weekly",
            Recurrence_End_Date=date(2026, 10, 5),
        )

        occurrences = recurrence_service.expand_schedule_request(
            request, date(2026, 9, 1), date(2026, 12, 31)
        )

        assert occurrences == [
            date(2026, 9, 14),
            date(2026, 9, 21),
            date(2026, 9, 28),
            date(2026, 10, 5),
        ]


@pytest.mark.asyncio
class TestRepeatingScheduleNeedsEndDate:
    @pytest.mark.parametrize("recurrence_type", ["weekly", "monthly_date", "monthly_nth_weekday"])
    async def test_api_rejects_repeat_without_end_date(
        self, client: AsyncClient, staff_headers: dict[str, str], recurrence_type: str
    ):
        response = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Schedule_Requests=[
                    {"Requested_Date": "2026-09-14", "Recurrence_Type": recurrence_type}
                ]
            ),
            headers=staff_headers,
        )

        assert response.status_code == 422
        assert "Recurrence_End_Date is required" in response.text


async def _legacy_submission(
    db: AsyncSession,
    *,
    headline: str,
    target: str,
    category: str,
    requested: date,
    second: date | None = None,
    recurrence_type: str = "weekly",
    end: date | None = None,
    repeat_count: int = 1,
) -> str:
    submission = Submission(
        Category=category,
        Target_Newsletter=target,
        Original_Headline=headline,
        Original_Body="Synthetic body text.",
        Submitter_Name="Test User",
        Submitter_Email="test@uidaho.edu",
        Status="approved",
    )
    db.add(submission)
    await db.flush()
    db.add(
        SubmissionScheduleRequest(
            Submission_Id=submission.Id,
            Requested_Date=requested,
            Second_Requested_Date=second,
            Repeat_Count=repeat_count,
            Recurrence_Type=recurrence_type,
            Recurrence_Interval=1,
            Recurrence_End_Date=end,
        )
    )
    await db.commit()
    return submission.Id


@pytest.mark.asyncio
class TestAssemblyIgnoresOpenEndedRepeats:
    @pytest.fixture
    async def sections(self, db: AsyncSession):
        db.add_all(
            [
                NewsletterSection(
                    Newsletter_Type="myui",
                    Name="News and Updates",
                    Slug="news-and-updates",
                    Display_Order=1,
                    Is_Active=True,
                ),
                NewsletterSection(
                    Newsletter_Type="tdr",
                    Name="Employee News",
                    Slug="employee-news",
                    Display_Order=1,
                    Is_Active=True,
                ),
            ]
        )
        await db.commit()

    async def _assemble(self, client, staff_headers, newsletter_type, publish_date):
        response = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": newsletter_type, "Publish_Date": publish_date},
            headers=staff_headers,
        )
        assert response.status_code == 200
        return [item["Submission_Id"] for item in response.json()["Items"]]

    @pytest.mark.usefixtures("sections")
    async def test_my_ui_edition_gets_only_items_scheduled_for_it(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
    ):
        old_student = await _legacy_submission(
            db,
            headline="September student item",
            target="myui",
            category="student",
            requested=date(2026, 9, 14),
        )
        old_both = await _legacy_submission(
            db,
            headline="September item for both newsletters",
            target="both",
            category="faculty_staff",
            requested=date(2026, 9, 8),
            second=date(2026, 9, 14),
            repeat_count=2,
        )
        bounded = await _legacy_submission(
            db,
            headline="Weekly item that ends in December",
            target="myui",
            category="student",
            requested=date(2026, 11, 2),
            end=date(2026, 12, 7),
        )
        scheduled = await _legacy_submission(
            db,
            headline="Item scheduled for Nov. 16",
            target="myui",
            category="student",
            requested=date(2026, 11, 16),
            recurrence_type="once",
        )

        assert set(await self._assemble(client, staff_headers, "myui", "2026-11-16")) == {
            bounded,
            scheduled,
        }
        assert set(await self._assemble(client, staff_headers, "myui", "2026-09-14")) == {
            old_student,
            old_both,
        }

    @pytest.mark.usefixtures("sections")
    async def test_both_item_stops_repeating_in_the_daily_register(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
    ):
        old_both = await _legacy_submission(
            db,
            headline="September item for both newsletters",
            target="both",
            category="faculty_staff",
            requested=date(2026, 9, 8),
            second=date(2026, 9, 14),
            repeat_count=2,
        )

        assert await self._assemble(client, staff_headers, "tdr", "2026-11-17") == []
        assert await self._assemble(client, staff_headers, "tdr", "2026-09-08") == [old_both]
