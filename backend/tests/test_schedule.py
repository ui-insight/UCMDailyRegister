"""Regression tests for newsletter-specific publication schedules.

The Daily Register follows university closure blackouts. My UI keeps its
Monday cadence through holidays and uses the same Monday cadence during the
summer, unless an editor explicitly activates a custom schedule override.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import seed
from app.models.schedule_config import ScheduleConfig


async def seed_schedule(db: AsyncSession) -> None:
    """Load the production schedule fixtures into the isolated test database."""
    await seed.seed_schedule_configs(db)
    await seed.seed_blackout_dates(db)


@pytest.mark.asyncio
class TestNewsletterSpecificSchedule:
    async def test_myui_keeps_labor_day_monday(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await seed_schedule(db)

        response = await client.get(
            "/api/v1/schedule/valid-dates",
            params={
                "from": "2026-09-07",
                "to": "2026-09-07",
                "newsletter_type": "myui",
            },
        )

        assert response.status_code == 200
        assert response.json()["dates"] == [
            {"date": "2026-09-07", "newsletters": ["myui"]}
        ]

    async def test_tdr_still_skips_labor_day(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await seed_schedule(db)

        response = await client.get(
            "/api/v1/schedule/valid-dates",
            params={
                "from": "2026-09-07",
                "to": "2026-09-07",
                "newsletter_type": "tdr",
            },
        )

        assert response.status_code == 200
        assert response.json()["dates"] == []

    async def test_myui_keeps_monday_cadence_during_summer(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await seed_schedule(db)

        response = await client.get(
            "/api/v1/schedule/valid-dates",
            params={
                "from": "2026-06-01",
                "to": "2026-06-01",
                "newsletter_type": "myui",
            },
        )

        assert response.status_code == 200
        assert response.json()["dates"] == [
            {"date": "2026-06-01", "newsletters": ["myui"]}
        ]

    async def test_myui_academic_year_deadline_is_noon_wednesday(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await seed_schedule(db)

        response = await client.get(
            "/api/v1/schedule/active",
            params={"newsletter_type": "myui", "for_date": "2026-10-05"},
        )

        assert response.status_code == 200
        config = response.json()["config"]
        assert config["Submission_Deadline_Description"] == (
            "Submissions due by noon Wednesday for Monday's edition"
        )
        assert config["Deadline_Day_Of_Week"] == 2
        assert config["Deadline_Time"] == "12:00:00"
        assert response.json()["submission_deadline"] == "2026-10-07T12:00:00"

        seeded = await db.get(ScheduleConfig, config["Id"])
        assert seeded is not None
        assert seeded.Holiday_Shift_Enabled is False
