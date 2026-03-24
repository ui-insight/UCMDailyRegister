"""Service-level submission tests."""

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
