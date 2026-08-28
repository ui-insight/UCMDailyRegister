"""Service-level submission tests."""

from datetime import date

import pytest

from app.schemas.submission import SubmissionCreate
from app.services import submission_service


@pytest.mark.asyncio
async def test_create_submission_persists_second_requested_date(db):
    submission = await submission_service.create_submission(
        db,
        SubmissionCreate(
            Category="faculty_staff",
            Target_Newsletter="both",
            Original_Headline="Two-newsletter announcement",
            Original_Body="Body text for both newsletters.",
            Submitter_Name="Test User",
            Submitter_Email="test@uidaho.edu",
            Links=[],
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-04-10",
                    "Second_Requested_Date": "2026-04-13",
                    "Repeat_Count": 2,
                }
            ],
        ),
    )

    assert submission is not None
    assert submission.Schedule_Requests[0].Second_Requested_Date.isoformat() == "2026-04-13"


@pytest.mark.asyncio
async def test_both_submission_uses_newsletter_specific_date_fields(db):
    submission = await submission_service.create_submission(
        db,
        SubmissionCreate(
            Category="faculty_staff",
            Target_Newsletter="both",
            Original_Headline="Two-newsletter announcement",
            Original_Body="Body text for both newsletters.",
            Submitter_Name="Test User",
            Submitter_Email="test@uidaho.edu",
            Links=[],
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-04-06",
                    "Second_Requested_Date": "2026-04-13",
                },
                {
                    "Requested_Date": "2026-04-06",
                    "Second_Requested_Date": "2026-04-20",
                },
            ],
        ),
    )

    tdr_dates = await submission_service.get_submission_occurrence_dates(
        db,
        submission,
        date(2026, 4, 1),
        date(2026, 4, 30),
        newsletter_type="tdr",
    )
    student_dates = await submission_service.get_submission_occurrence_dates(
        db,
        submission,
        date(2026, 4, 1),
        date(2026, 4, 30),
        newsletter_type="myui",
    )
    combined_dates = await submission_service.get_submission_occurrence_dates(
        db,
        submission,
        date(2026, 4, 1),
        date(2026, 4, 30),
        newsletter_type="both",
    )

    assert tdr_dates == [date(2026, 4, 6)]
    assert student_dates == [date(2026, 4, 13), date(2026, 4, 20)]
    assert combined_dates == [
        date(2026, 4, 6),
        date(2026, 4, 13),
        date(2026, 4, 20),
    ]


@pytest.mark.asyncio
async def test_date_range_listing_caches_publication_dates_per_request(
    db,
    monkeypatch: pytest.MonkeyPatch,
):
    for index in range(3):
        await submission_service.create_submission(
            db,
            SubmissionCreate(
                Category="faculty_staff",
                Target_Newsletter="tdr",
                Original_Headline=f"Recurring announcement {index}",
                Original_Body="Body text.",
                Submitter_Name="Test User",
                Submitter_Email="test@uidaho.edu",
                Links=[],
                Schedule_Requests=[
                    {
                        "Requested_Date": "2026-04-06",
                        "Recurrence_Type": "monthly_nth_weekday",
                        "Recurrence_End_Date": "2026-06-01",
                    }
                ],
            ),
        )

    calls = {"configs": 0, "valid_dates": 0}

    async def fake_list_configs(db, newsletter_type=None):
        calls["configs"] += 1
        return [object()]

    async def fake_valid_dates(db, from_date, to_date, newsletter_type):
        calls["valid_dates"] += 1
        return [{"date": date(2026, 5, 4)}]

    monkeypatch.setattr(
        submission_service.schedule_service,
        "list_configs",
        fake_list_configs,
    )
    monkeypatch.setattr(
        submission_service.schedule_service,
        "get_valid_publication_dates",
        fake_valid_dates,
    )

    items, total = await submission_service.list_submissions(
        db,
        target_newsletter="tdr",
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    assert total == 3
    assert len(items) == 3
    assert calls == {"configs": 1, "valid_dates": 1}


@pytest.mark.asyncio
async def test_date_range_listing_excludes_one_time_submissions_outside_range(db):
    await submission_service.create_submission(
        db,
        SubmissionCreate(
            Category="faculty_staff",
            Target_Newsletter="tdr",
            Original_Headline="Old one-time announcement",
            Original_Body="Body text.",
            Submitter_Name="Test User",
            Submitter_Email="test@uidaho.edu",
            Links=[],
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-04-06",
                    "Recurrence_Type": "once",
                }
            ],
        ),
    )

    items, total = await submission_service.list_submissions(
        db,
        target_newsletter="tdr",
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    assert total == 0
    assert items == []


# --- Weekly SLC digest week-range query (#335) ---


async def _create_slc_event(db, headline: str, schedule: dict) -> None:
    await submission_service.create_submission(
        db,
        SubmissionCreate(
            Category="slc_event",
            Target_Newsletter="none",
            Original_Headline=headline,
            Original_Body="Start time: 7:00 PM\nLocation: Pitman Center",
            Submitter_Name="SLC event triage",
            Submitter_Email="slc-triage@uidaho.edu",
            Show_In_SLC_Calendar=True,
            Links=[],
            Schedule_Requests=[schedule],
        ),
    )


@pytest.mark.asyncio
async def test_slc_week_query_hydrates_multi_day_and_recurring_occurrences(db):
    """The digest week (Mon 2026-09-07 .. Sun 2026-09-13) picks up every
    occurrence inside the window, including weekend days: SLC-only events
    are not clipped to newsletter publication dates."""
    # Spans Sat 9/5 - Wed 9/9; only Mon-Wed fall inside the digest week.
    await _create_slc_event(
        db,
        "Homecoming setup",
        {
            "Requested_Date": "2026-09-05",
            "Recurrence_Type": "date_range",
            "Recurrence_End_Date": "2026-09-09",
        },
    )
    # Weekly on Tuesdays; 9/8 is the only occurrence inside the week.
    await _create_slc_event(
        db,
        "Leadership briefing",
        {
            "Requested_Date": "2026-09-01",
            "Recurrence_Type": "weekly",
            "Recurrence_End_Date": "2026-12-15",
        },
    )
    # Saturday one-time event inside the week.
    await _create_slc_event(
        db,
        "Vandal football home game",
        {"Requested_Date": "2026-09-12", "Recurrence_Type": "once"},
    )

    items, total = await submission_service.list_submissions(
        db,
        slc_calendar_only=True,
        date_from=date(2026, 9, 7),
        date_to=date(2026, 9, 13),
    )

    assert total == 3
    by_headline = {item.Original_Headline: item for item in items}
    assert by_headline["Homecoming setup"].Occurrence_Dates == [
        "2026-09-07",
        "2026-09-08",
        "2026-09-09",
    ]
    assert by_headline["Leadership briefing"].Occurrence_Dates == ["2026-09-08"]
    assert by_headline["Vandal football home game"].Occurrence_Dates == ["2026-09-12"]


@pytest.mark.asyncio
async def test_slc_week_query_excludes_out_of_week_and_non_slc_events(db):
    await _create_slc_event(
        db,
        "Event after the digest week",
        {"Requested_Date": "2026-09-20", "Recurrence_Type": "once"},
    )
    # In-week newsletter submission that is not on the SLC calendar.
    await submission_service.create_submission(
        db,
        SubmissionCreate(
            Category="faculty_staff",
            Target_Newsletter="tdr",
            Original_Headline="Newsletter announcement",
            Original_Body="Body text.",
            Submitter_Name="Test User",
            Submitter_Email="test@uidaho.edu",
            Links=[],
            Schedule_Requests=[
                {"Requested_Date": "2026-09-08", "Recurrence_Type": "once"}
            ],
        ),
    )

    items, total = await submission_service.list_submissions(
        db,
        slc_calendar_only=True,
        date_from=date(2026, 9, 7),
        date_to=date(2026, 9, 13),
    )

    assert total == 0
    assert items == []
