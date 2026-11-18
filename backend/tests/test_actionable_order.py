"""Default Builder order by earliest actionable date (#388). Synthetic data only."""

from datetime import date, datetime, timedelta

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.section import NewsletterSection
from app.models.submission import Submission
from app.utils.actionable_dates import (
    UNTIMED,
    dates_in_text,
    earliest_actionable_date,
    earliest_actionable_moment,
)
from tests.conftest import make_submission_data

PUBLISH = date(2026, 11, 17)
PUBLISH_ISO = PUBLISH.isoformat()


class TestEarliestActionableDate:
    def test_picks_the_earliest_upcoming_date_in_the_copy(self):
        body = "Register by Nov. 20 for the Dec. 3 workshop."
        assert earliest_actionable_date(["Workshop", body], PUBLISH) == date(2026, 11, 20)

    def test_ignores_dates_that_have_passed(self):
        body = "Since Oct. 1, the office has moved. Visit on December 2, 2026."
        assert earliest_actionable_date([body], PUBLISH) == date(2026, 12, 2)

    def test_the_publish_date_itself_counts(self):
        assert earliest_actionable_date(["Today, Nov. 17, at noon."], PUBLISH) == PUBLISH

    def test_year_rolls_over_for_early_next_year_dates(self):
        assert dates_in_text("Applications close Jan. 9.", PUBLISH) == [date(2027, 1, 9)]

    def test_explicit_past_year_is_ignored(self):
        assert earliest_actionable_date(["Held Nov. 30, 2025."], PUBLISH) is None

    def test_known_deadline_counts(self):
        assert earliest_actionable_date(
            ["Take the survey by Dec. 1."], PUBLISH, known_dates=[date(2026, 11, 24), None]
        ) == date(2026, 11, 24)

    def test_no_date_and_impossible_dates_give_none(self):
        assert earliest_actionable_date(["See <b>Feb. 30</b> notes. No date here."], PUBLISH) is None

    def test_reads_text_not_markup(self):
        body = '<a href="https://example.com/nov-18">Details</a> on Nov. 25.'
        assert earliest_actionable_date([body], PUBLISH) == date(2026, 11, 25)


async def _add_sections(db: AsyncSession) -> None:
    db.add_all([
        NewsletterSection(
            Id="tdr-employee-news",
            Newsletter_Type="tdr",
            Name="Employee News",
            Slug="employee-news",
            Display_Order=1,
            Is_Active=True,
        ),
        NewsletterSection(
            Id="tdr-jobs",
            Newsletter_Type="tdr",
            Name="Job Opportunities",
            Slug="job-opportunities",
            Display_Order=11,
            Is_Active=True,
        ),
    ])
    await db.commit()


async def _approved_submission(
    client: AsyncClient,
    db: AsyncSession,
    staff_headers: dict[str, str],
    *,
    headline: str,
    body: str,
    created_at: datetime,
    category: str = "faculty_staff",
    survey_end_date: date | None = None,
) -> str:
    response = await client.post(
        "/api/v1/submissions/",
        json=make_submission_data(
            Category=category,
            Original_Headline=headline,
            Original_Body=body,
            Schedule_Requests=[{"Requested_Date": PUBLISH_ISO}],
        ),
    )
    assert response.status_code == 201, response.text
    submission_id = response.json()["Id"]
    await client.patch(
        f"/api/v1/submissions/{submission_id}",
        json={"Status": "approved"},
        headers=staff_headers,
    )
    await db.execute(
        sa.update(Submission)
        .where(Submission.Id == submission_id)
        .values(Created_At=created_at, Survey_End_Date=survey_end_date)
    )
    await db.commit()
    return submission_id


async def _assemble(client: AsyncClient, staff_headers: dict[str, str]) -> dict:
    response = await client.post(
        "/api/v1/newsletters/assemble",
        json={"Newsletter_Type": "tdr", "Publish_Date": PUBLISH_ISO},
        headers=staff_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _order(newsletter: dict, section_id: str) -> list[str]:
    items = [item for item in newsletter["Items"] if item["Section_Id"] == section_id]
    return [item["Submission_Id"] for item in sorted(items, key=lambda item: item["Position"])]


@pytest.mark.asyncio
async def test_assembly_orders_items_by_earliest_actionable_date(
    client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
):
    await _add_sections(db)
    base = datetime(2026, 11, 1, 9, 0)
    late_deadline = await _approved_submission(
        client, db, staff_headers,
        headline="Benefits enrollment closes",
        body="Enroll by Nov. 25 in the synthetic benefits portal.",
        created_at=base,
    )
    undated = await _approved_submission(
        client, db, staff_headers,
        headline="New parking app",
        body="The synthetic parking app is now available.",
        created_at=base + timedelta(hours=1),
    )
    soon_event = await _approved_submission(
        client, db, staff_headers,
        headline="Workshop on Dec. 3",
        body="Register by Nov. 18 for the Dec. 3 synthetic workshop.",
        created_at=base + timedelta(hours=2),
    )
    passed_only = await _approved_submission(
        client, db, staff_headers,
        headline="Office moved",
        body="Since Oct. 1, the synthetic office is in Test Hall.",
        created_at=base + timedelta(hours=3),
    )
    survey = await _approved_submission(
        client, db, staff_headers,
        headline="Take the synthetic survey",
        body="Share your views on campus dining.",
        created_at=base + timedelta(hours=4),
        category="survey",
        survey_end_date=date(2026, 11, 21),
    )

    newsletter = await _assemble(client, staff_headers)

    # Dated items go by their earliest upcoming date; undated items always
    # go last, in submission order.
    assert _order(newsletter, "tdr-employee-news") == [
        soon_event,
        survey,
        late_deadline,
        undated,
        passed_only,
    ]


@pytest.mark.asyncio
async def test_reassembly_keeps_staff_order_and_appends_new_items(
    client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
):
    await _add_sections(db)
    base = datetime(2026, 11, 1, 9, 0)
    first = await _approved_submission(
        client, db, staff_headers,
        headline="Event Nov. 19", body="Synthetic event on Nov. 19.", created_at=base,
    )
    second = await _approved_submission(
        client, db, staff_headers,
        headline="Event Nov. 26", body="Synthetic event on Nov. 26.",
        created_at=base + timedelta(hours=1),
    )
    newsletter = await _assemble(client, staff_headers)
    assert _order(newsletter, "tdr-employee-news") == [first, second]

    # Staff put the Nov. 26 item first.
    items = {item["Submission_Id"]: item["Id"] for item in newsletter["Items"]}
    response = await client.put(
        f"/api/v1/newsletters/{newsletter['Id']}/reorder",
        json=[
            {"Id": items[second], "Position": 0, "Section_Id": "tdr-employee-news"},
            {"Id": items[first], "Position": 1, "Section_Id": "tdr-employee-news"},
        ],
        headers=staff_headers,
    )
    assert response.status_code == 200

    # A newer item with an earlier date arrives; reassembly doesn't undo staff order.
    newcomer = await _approved_submission(
        client, db, staff_headers,
        headline="Event today", body="Synthetic event on Nov. 17.",
        created_at=base + timedelta(hours=2),
    )
    newsletter = await _assemble(client, staff_headers)

    assert _order(newsletter, "tdr-employee-news") == [second, first, newcomer]


@pytest.mark.asyncio
async def test_jobs_stay_newest_first_whatever_dates_they_name(
    client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
):
    await _add_sections(db)
    base = datetime(2026, 11, 1, 9, 0)
    older = await _approved_submission(
        client, db, staff_headers,
        headline="Synthetic analyst", body="Closes Nov. 18.",
        created_at=base, category="job_opportunity",
    )
    newer = await _approved_submission(
        client, db, staff_headers,
        headline="Synthetic technician", body="Closes Dec. 15.",
        created_at=base + timedelta(hours=1), category="job_opportunity",
    )

    newsletter = await _assemble(client, staff_headers)

    assert _order(newsletter, "tdr-jobs") == [newer, older]


@pytest.mark.parametrize(
    ("text", "publish", "expected"),
    [
        # PR #507 review: a trailing year applies to both ends of a range.
        ("Workshop Nov. 18-20, 2027", date(2026, 11, 16), date(2027, 11, 18)),
        ("Workshop Nov. 18–20, 2027", date(2026, 11, 16), date(2027, 11, 18)),
        # A range under way on the publish date is actionable now.
        ("Workshop Nov. 16-20", date(2026, 11, 18), date(2026, 11, 18)),
        ("Book drive Nov. 30–Dec. 2", date(2026, 11, 16), date(2026, 11, 30)),
        ("Closure Dec. 30 - Jan. 2, 2027", date(2026, 11, 16), date(2026, 12, 30)),
        ("Closure Dec. 30 to Jan. 2", date(2027, 1, 1), date(2027, 1, 1)),
        # A finished range is not actionable.
        ("Workshop Nov. 2-4", date(2026, 11, 16), None),
        # A time range after a date isn't a date range.
        ("Talk Nov. 20, 3-5 p.m.", date(2026, 11, 16), date(2026, 11, 20)),
    ],
)
def test_date_ranges_are_read_as_a_unit(text, publish, expected):
    assert earliest_actionable_date([text], publish) == expected


@pytest.mark.parametrize(
    ("text", "expected_minutes"),
    [
        # Times before the date, TDR style, and after it.
        ("3-4 p.m. Wednesday, Nov. 18, in Test Hall.", 15 * 60),
        ("Join us Nov. 18 at 10:30 a.m.", 10 * 60 + 30),
        ("Talk Nov. 18, 3-5 p.m.", 15 * 60),
        # A range's start takes the end's period unless it would follow the end.
        ("11-1 p.m. Wednesday, Nov. 18.", 11 * 60),
        ("12-1 p.m. Nov. 18", 12 * 60),
        # Noon is 12 p.m.; midnight is the end of the day.
        ("Noon-1 p.m. Nov. 18", 12 * 60),
        ("9 a.m.-noon Nov. 18", 9 * 60),
        ("Movie night until midnight Nov. 18", 24 * 60),
        ("Party at 12 a.m. Nov. 18", 24 * 60),
        ("Starts 3 PM Nov 18", 15 * 60),
        # A time in another sentence doesn't belong to the date.
        ("Register by Nov. 18. Doors open 9 a.m.", UNTIMED),
        # Bare numbers aren't times.
        ("Room 204, Nov. 18", UNTIMED),
    ],
)
def test_reads_the_start_time_written_with_a_date(text, expected_minutes):
    assert earliest_actionable_moment([text], PUBLISH) == (date(2026, 11, 18), expected_minutes)


def test_soonest_date_and_time_wins():
    body = "3 p.m. Nov. 19 and 9 a.m. Nov. 18; also 8 a.m. Nov. 18."
    assert earliest_actionable_moment([body], PUBLISH) == (date(2026, 11, 18), 8 * 60)


def test_untimed_mention_of_a_day_sorts_before_its_times():
    body = "Register by Nov. 18 for the 2 p.m. Nov. 18 session."
    assert earliest_actionable_moment([body], PUBLISH) == (date(2026, 11, 18), UNTIMED)


def test_multi_day_range_uses_its_start_date_and_time():
    assert earliest_actionable_moment(["Nov. 19-21, 8 a.m.-5 p.m."], PUBLISH) == (
        date(2026, 11, 19),
        8 * 60,
    )


@pytest.mark.asyncio
async def test_assembly_orders_same_day_items_by_start_time(
    client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
):
    """#531: date, then time; untimed first in the day; undated last; ties by submission."""
    await _add_sections(db)
    base = datetime(2026, 11, 1, 9, 0)

    async def add(headline: str, body: str, hours: int) -> str:
        return await _approved_submission(
            client, db, staff_headers,
            headline=headline, body=body, created_at=base + timedelta(hours=hours),
        )

    evening = await add("Synthetic concert", "7 p.m. Thursday, Nov. 19, in Test Hall.", 0)
    undated_first = await add("Synthetic app", "The synthetic app is available.", 1)
    midnight = await add("Synthetic vigil", "Midnight Thursday, Nov. 19, on the Test Lawn.", 2)
    morning = await add("Synthetic breakfast", "8-9:30 a.m. Thursday, Nov. 19, in Test Hall.", 3)
    deadline = await add("Synthetic deadline", "Apply by Nov. 19 in the synthetic portal.", 4)
    lunch_tie_a = await add("Synthetic talk A", "Noon-1 p.m. Thursday, Nov. 19, in Test Hall.", 5)
    next_day = await add("Synthetic workshop", "9 a.m. Friday, Nov. 20, in Test Hall.", 6)
    lunch_tie_b = await add("Synthetic talk B", "12-1 p.m. Thursday, Nov. 19, in Test Hall.", 7)
    undated_second = await add("Synthetic reminder", "Update your synthetic profile.", 8)

    newsletter = await _assemble(client, staff_headers)

    assert _order(newsletter, "tdr-employee-news") == [
        deadline,
        morning,
        lunch_tie_a,
        lunch_tie_b,
        evening,
        midnight,
        next_day,
        undated_first,
        undated_second,
    ]
