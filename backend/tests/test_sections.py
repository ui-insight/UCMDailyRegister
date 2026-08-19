"""Tests for the data-driven newsletter section catalog."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import seed


@pytest.mark.asyncio
async def test_tdr_jobs_follow_student_reminders_at_bottom(
    client: AsyncClient,
    db: AsyncSession,
):
    await seed.seed_sections(db)

    response = await client.get(
        "/api/v1/sections",
        params={"newsletter_type": "tdr"},
    )

    assert response.status_code == 200
    sections = response.json()
    assert [section["Name"] for section in sections[-3:]] == [
        "Employee Announcements",
        "Reminders for your students",
        "Job Opportunities",
    ]
    assert sections[-2]["Slug"] == "reminders-for-your-students"
    assert sections[-2]["Display_Order"] == 10
    assert sections[-1]["Slug"] == "job-opportunities"
    assert sections[-1]["Display_Order"] == 11
