"""UCM staff can set a repeating schedule to repeat indefinitely (#538).

Synthetic data only. The flag is a deliberate, stored choice: a legacy row
with no end date and no flag still runs only on its requested date (#477).
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

REPEATING_TYPES = ["weekly", "monthly_date", "monthly_nth_weekday"]


def _request(**fields) -> SimpleNamespace:
    defaults = {
        "Requested_Date": None,
        "Second_Requested_Date": None,
        "Recurrence_Type": "once",
        "Recurrence_Interval": 1,
        "Recurrence_End_Date": None,
        "Repeats_Indefinitely": False,
        "Excluded_Dates": [],
    }
    defaults.update(fields)
    return SimpleNamespace(**defaults)


class TestIndefiniteExpansion:
    def test_indefinite_weekly_reaches_far_future_dates(self):
        request = _request(
            Requested_Date=date(2026, 11, 23),
            Recurrence_Type="weekly",
            Repeats_Indefinitely=True,
        )

        occurrences = recurrence_service.expand_schedule_request(
            request, date(2031, 6, 1), date(2031, 6, 30)
        )

        # Nov. 23, 2026 is a Monday; so is every date below.
        assert occurrences == [
            date(2031, 6, 2),
            date(2031, 6, 9),
            date(2031, 6, 16),
            date(2031, 6, 23),
            date(2031, 6, 30),
        ]

    def test_indefinite_monthly_survives_short_months(self):
        """An indefinite series on the 31st must not stop at the first 30-day month (#488)."""
        request = _request(
            Requested_Date=date(2026, 12, 31),
            Recurrence_Type="monthly_date",
            Repeats_Indefinitely=True,
        )

        occurrences = recurrence_service.expand_schedule_request(
            request, date(2030, 1, 1), date(2030, 12, 31)
        )

        assert occurrences == [
            date(2030, 1, 31),
            date(2030, 3, 31),
            date(2030, 5, 31),
            date(2030, 7, 31),
            date(2030, 8, 31),
            date(2030, 10, 31),
            date(2030, 12, 31),
        ]

    def test_indefinite_fifth_weekday_skips_months_without_one(self):
        # Jan. 29, 2027 is the fifth Friday of January.
        request = _request(
            Requested_Date=date(2027, 1, 29),
            Recurrence_Type="monthly_nth_weekday",
            Repeats_Indefinitely=True,
        )

        occurrences = recurrence_service.expand_schedule_request(
            request, date(2027, 1, 1), date(2027, 12, 31)
        )

        assert occurrences == [
            date(2027, 1, 29),
            date(2027, 4, 30),
            date(2027, 7, 30),
            date(2027, 10, 29),
            date(2027, 12, 31),
        ]

    @pytest.mark.parametrize("recurrence_type", REPEATING_TYPES)
    def test_legacy_open_ended_row_still_runs_once(self, recurrence_type):
        request = _request(Requested_Date=date(2026, 9, 14), Recurrence_Type=recurrence_type)

        occurrences = recurrence_service.expand_schedule_request(
            request, date(2026, 9, 1), date(2030, 12, 31)
        )

        assert occurrences == [date(2026, 9, 14)]

    def test_end_date_still_applies_if_a_row_has_both(self):
        request = _request(
            Requested_Date=date(2026, 11, 23),
            Recurrence_Type="weekly",
            Recurrence_End_Date=date(2026, 12, 7),
            Repeats_Indefinitely=True,
        )

        occurrences = recurrence_service.expand_schedule_request(
            request, date(2026, 11, 1), date(2027, 12, 31)
        )

        assert occurrences == [date(2026, 11, 23), date(2026, 11, 30), date(2026, 12, 7)]


def _indefinite_schedule(**overrides) -> dict:
    schedule = {
        "Requested_Date": "2026-11-23",
        "Recurrence_Type": "weekly",
        "Repeats_Indefinitely": True,
    }
    schedule.update(overrides)
    return schedule


@pytest.mark.asyncio
class TestCreateIndefinite:
    @pytest.mark.parametrize("recurrence_type", REPEATING_TYPES)
    async def test_staff_can_create_an_indefinite_schedule(
        self, client: AsyncClient, staff_headers: dict[str, str], recurrence_type: str
    ):
        response = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Schedule_Requests=[_indefinite_schedule(Recurrence_Type=recurrence_type)]
            ),
            headers=staff_headers,
        )

        assert response.status_code == 201, response.text
        schedule = response.json()["Schedule_Requests"][0]
        assert schedule["Repeats_Indefinitely"] is True
        assert schedule["Recurrence_End_Date"] is None

    async def test_non_staff_cannot_create_an_indefinite_schedule(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(Schedule_Requests=[_indefinite_schedule()]),
        )

        assert response.status_code == 403
        assert "repeat indefinitely" in response.json()["detail"]

    async def test_non_staff_job_cannot_smuggle_an_indefinite_flag(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Category="job_opportunity",
                Schedule_Requests=[
                    _indefinite_schedule(Recurrence_Type="weekly", Requested_Date="2026-11-23")
                ],
            ),
        )

        assert response.status_code == 403

    async def test_end_date_and_indefinite_together_are_rejected(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        response = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Schedule_Requests=[_indefinite_schedule(Recurrence_End_Date="2026-12-31")]
            ),
            headers=staff_headers,
        )

        assert response.status_code == 422
        assert "not both" in response.text

    async def test_indefinite_one_time_schedule_is_rejected(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        response = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Schedule_Requests=[_indefinite_schedule(Recurrence_Type="once")]
            ),
            headers=staff_headers,
        )

        assert response.status_code == 422

    async def test_staff_can_still_choose_an_end_date(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        response = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Schedule_Requests=[
                    {
                        "Requested_Date": "2026-11-23",
                        "Recurrence_Type": "weekly",
                        "Recurrence_End_Date": "2026-12-14",
                    }
                ]
            ),
            headers=staff_headers,
        )

        assert response.status_code == 201
        assert response.json()["Schedule_Requests"][0]["Repeats_Indefinitely"] is False


async def _create(client: AsyncClient, staff_headers: dict[str, str], schedule: dict) -> dict:
    response = await client.post(
        "/api/v1/submissions/",
        json=make_submission_data(Schedule_Requests=[schedule]),
        headers=staff_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
class TestEditorScheduleEndpoints:
    async def test_staff_add_run_date_can_repeat_indefinitely(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission = await _create(client, staff_headers, {"Requested_Date": "2026-11-23"})

        response = await client.post(
            f"/api/v1/submissions/{submission['Id']}/schedule",
            json=_indefinite_schedule(Requested_Date="2026-11-30"),
            headers=staff_headers,
        )

        assert response.status_code == 201, response.text
        assert response.json()["Repeats_Indefinitely"] is True

    async def test_non_staff_cannot_add_an_indefinite_run_date(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission = await _create(client, staff_headers, {"Requested_Date": "2026-11-23"})

        response = await client.post(
            f"/api/v1/submissions/{submission['Id']}/schedule",
            json=_indefinite_schedule(Requested_Date="2026-11-30"),
        )

        assert response.status_code in (401, 403)

    async def test_non_staff_cannot_change_how_a_schedule_ends(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission = await _create(
            client,
            staff_headers,
            {
                "Requested_Date": "2026-11-23",
                "Recurrence_Type": "weekly",
                "Recurrence_End_Date": "2026-12-14",
            },
        )
        schedule_id = submission["Schedule_Requests"][0]["Id"]

        response = await client.patch(
            f"/api/v1/submissions/{submission['Id']}/schedule/{schedule_id}",
            json={"Repeats_Indefinitely": True},
        )

        assert response.status_code == 403

    async def test_staff_end_an_indefinite_series(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission = await _create(client, staff_headers, _indefinite_schedule())
        schedule_id = submission["Schedule_Requests"][0]["Id"]

        response = await client.patch(
            f"/api/v1/submissions/{submission['Id']}/schedule/{schedule_id}",
            json={"Recurrence_End_Date": "2026-12-07"},
            headers=staff_headers,
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["Repeats_Indefinitely"] is False
        assert body["Recurrence_End_Date"] == "2026-12-07"
        # Start date and cadence are kept, so earlier dates are untouched.
        assert body["Requested_Date"] == "2026-11-23"
        assert body["Recurrence_Type"] == "weekly"

    async def test_staff_opt_a_legacy_row_into_repeating_indefinitely(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
    ):
        submission_id, schedule_id = await _legacy_submission(
            db, target="tdr", category="faculty_staff", requested=date(2026, 9, 14)
        )

        response = await client.patch(
            f"/api/v1/submissions/{submission_id}/schedule/{schedule_id}",
            json={"Repeats_Indefinitely": True},
            headers=staff_headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()["Repeats_Indefinitely"] is True

    async def test_patch_needs_exactly_one_ending(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission = await _create(client, staff_headers, _indefinite_schedule())
        schedule_id = submission["Schedule_Requests"][0]["Id"]
        url = f"/api/v1/submissions/{submission['Id']}/schedule/{schedule_id}"

        neither = await client.patch(url, json={}, headers=staff_headers)
        both = await client.patch(
            url,
            json={"Recurrence_End_Date": "2026-12-07", "Repeats_Indefinitely": True},
            headers=staff_headers,
        )
        too_early = await client.patch(
            url, json={"Recurrence_End_Date": "2026-11-01"}, headers=staff_headers
        )

        assert neither.status_code == 422
        assert both.status_code == 422
        assert too_early.status_code == 422

    async def test_one_time_schedule_cannot_change_its_ending(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        submission = await _create(client, staff_headers, {"Requested_Date": "2026-11-23"})
        schedule_id = submission["Schedule_Requests"][0]["Id"]

        response = await client.patch(
            f"/api/v1/submissions/{submission['Id']}/schedule/{schedule_id}",
            json={"Repeats_Indefinitely": True},
            headers=staff_headers,
        )

        assert response.status_code == 422


async def _legacy_submission(
    db: AsyncSession,
    *,
    target: str,
    category: str,
    requested: date,
    recurrence_type: str = "weekly",
    repeats_indefinitely: bool = False,
    end: date | None = None,
) -> tuple[str, str]:
    submission = Submission(
        Category=category,
        Target_Newsletter=target,
        Original_Headline=f"Synthetic {recurrence_type} item",
        Original_Body="Synthetic body text.",
        Submitter_Name="Test User",
        Submitter_Email="test@uidaho.edu",
        Status="approved",
    )
    db.add(submission)
    await db.flush()
    schedule = SubmissionScheduleRequest(
        Submission_Id=submission.Id,
        Requested_Date=requested,
        Recurrence_Type=recurrence_type,
        Recurrence_Interval=1,
        Recurrence_End_Date=end,
        Repeats_Indefinitely=repeats_indefinitely,
    )
    db.add(schedule)
    await db.commit()
    return submission.Id, schedule.Id


@pytest.mark.asyncio
class TestBuilderIncludesIndefiniteItems:
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
        assert response.status_code == 200, response.text
        return {item["Submission_Id"] for item in response.json()["Items"]}

    @pytest.mark.usefixtures("sections")
    async def test_far_future_editions_include_indefinite_weekly_not_legacy(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
    ):
        indefinite, _ = await _legacy_submission(
            db,
            target="myui",
            category="student",
            requested=date(2026, 9, 14),
            repeats_indefinitely=True,
        )
        legacy, _ = await _legacy_submission(
            db, target="myui", category="student", requested=date(2026, 9, 14)
        )

        assert await self._assemble(client, staff_headers, "myui", "2026-09-14") == {
            indefinite,
            legacy,
        }
        assert await self._assemble(client, staff_headers, "myui", "2029-04-16") == {indefinite}

    @pytest.mark.usefixtures("sections")
    async def test_far_future_editions_include_indefinite_monthly(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
    ):
        # Dec. 1, 2026 is the first Tuesday of December.
        monthly, _ = await _legacy_submission(
            db,
            target="tdr",
            category="faculty_staff",
            requested=date(2026, 12, 1),
            recurrence_type="monthly_nth_weekday",
            repeats_indefinitely=True,
        )

        # June 5, 2029 is the first Tuesday of June; June 12 is not.
        assert await self._assemble(client, staff_headers, "tdr", "2029-06-05") == {monthly}
        assert await self._assemble(client, staff_headers, "tdr", "2029-06-12") == set()

    @pytest.mark.usefixtures("sections")
    async def test_ending_a_series_stops_later_editions_only(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
    ):
        submission_id, schedule_id = await _legacy_submission(
            db,
            target="myui",
            category="student",
            requested=date(2026, 11, 2),
            repeats_indefinitely=True,
        )
        assert await self._assemble(client, staff_headers, "myui", "2026-11-09") == {
            submission_id
        }

        response = await client.patch(
            f"/api/v1/submissions/{submission_id}/schedule/{schedule_id}",
            json={"Recurrence_End_Date": "2026-11-16"},
            headers=staff_headers,
        )
        assert response.status_code == 200, response.text

        # The edition already built keeps the item; dates up to the end still qualify.
        assert await self._assemble(client, staff_headers, "myui", "2026-11-09") == {
            submission_id
        }
        assert await self._assemble(client, staff_headers, "myui", "2026-11-16") == {
            submission_id
        }
        assert await self._assemble(client, staff_headers, "myui", "2026-11-23") == set()
