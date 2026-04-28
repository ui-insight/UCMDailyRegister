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
