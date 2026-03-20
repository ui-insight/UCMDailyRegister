"""PostgreSQL-backed smoke test for CI deployment confidence.

This script is intentionally separate from the regular pytest suite. The default
tests use in-memory SQLite for speed, while this smoke check validates that:

1. Alembic migrations apply cleanly to PostgreSQL.
2. The FastAPI app can read migrated recurrence fields through real ORM queries.
3. Key API routes respond successfully against the migrated PostgreSQL schema.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta

import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient

from app.db.engine import async_session_factory
from app.main import app as fastapi_app
from app.models.edit_history import EditVersion
from app.models.submission import Submission, SubmissionLink, SubmissionScheduleRequest


async def seed_submission() -> str:
    """Seed one recurring submission directly into PostgreSQL."""
    async with async_session_factory() as session:
        await session.execute(sa.delete(EditVersion))
        await session.execute(sa.delete(SubmissionLink))
        await session.execute(sa.delete(SubmissionScheduleRequest))
        await session.execute(sa.delete(Submission))

        requested_date = date.today() + timedelta(days=7)
        submission = Submission(
            Category="faculty_staff",
            Target_Newsletter="tdr",
            Original_Headline="Postgres smoke submission",
            Original_Body="This submission verifies migrated recurrence fields.",
            Submitter_Name="CI Smoke Test",
            Submitter_Email="ci-smoke@uidaho.edu",
        )
        session.add(submission)
        await session.flush()

        session.add(
            SubmissionLink(
                Submission_Id=submission.Id,
                Url="https://www.uidaho.edu",
                Anchor_Text="Learn more",
                Display_Order=0,
            )
        )
        session.add(
            SubmissionScheduleRequest(
                Submission_Id=submission.Id,
                Requested_Date=requested_date,
                Repeat_Count=1,
                Repeat_Note="Created by CI smoke test",
                Is_Flexible=False,
                Flexible_Deadline=None,
                Recurrence_Type="weekly",
                Recurrence_Interval=2,
                Recurrence_End_Date=requested_date + timedelta(days=28),
                Excluded_Dates=[(requested_date + timedelta(days=14)).isoformat()],
            )
        )
        await session.commit()
        return submission.Id


async def main() -> None:
    """Run a lightweight PostgreSQL-backed API smoke test."""
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("DATABASE_URL must point to PostgreSQL for this smoke test.")

    submission_id = await seed_submission()

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health_response = await client.get("/api/v1/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "ok"}

        settings_response = await client.get("/api/v1/settings/ai")
        assert settings_response.status_code == 200
        assert "active_provider" in settings_response.json()

        submissions_response = await client.get("/api/v1/submissions/", params={"limit": 1})
        assert submissions_response.status_code == 200
        payload = submissions_response.json()
        assert payload["Total"] >= 1
        first_item = payload["Items"][0]
        assert first_item["Id"] == submission_id
        assert first_item["Schedule_Requests"][0]["Recurrence_Type"] == "weekly"
        assert "Occurrence_Dates" in first_item["Schedule_Requests"][0]

        detail_response = await client.get(f"/api/v1/submissions/{submission_id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["Schedule_Requests"][0]["Recurrence_Interval"] == 2
        assert detail_payload["Schedule_Requests"][0]["Excluded_Dates"]


if __name__ == "__main__":
    asyncio.run(main())
