"""Tests for the data-driven newsletter section catalog."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import seed


@pytest.mark.asyncio
async def test_tdr_student_reminders_follow_employee_announcements(
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
    assert [section["Name"] for section in sections[-2:]] == [
        "Employee Announcements",
        "Reminders for your students",
    ]
    assert sections[-1]["Slug"] == "reminders-for-your-students"
    assert sections[-1]["Display_Order"] == 10
