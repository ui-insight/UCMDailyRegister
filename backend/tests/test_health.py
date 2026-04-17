"""Tests for the health and readiness endpoints."""

from datetime import time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule_config import ScheduleConfig
from app.models.section import NewsletterSection
from app.models.style_rule import StyleRule


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readyz_reports_empty_tables(client: AsyncClient):
    """Baseline fixture seeds only AllowedValue — other vocabularies are empty."""
    resp = await client.get("/api/v1/readyz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert set(body["empty_tables"]) == {
        "newsletter_sections",
        "schedule_configs",
        "style_rules",
    }
    assert body["counts"]["allowed_values"] > 0


@pytest.mark.asyncio
async def test_readyz_passes_when_all_vocabularies_populated(
    client: AsyncClient, db: AsyncSession
):
    db.add_all(
        [
            NewsletterSection(
                Newsletter_Type="tdr",
                Name="Test Section",
                Slug="test-section",
                Display_Order=1,
            ),
            StyleRule(
                Rule_Set="shared",
                Category="grammar",
                Rule_Key="readyz_test",
                Rule_Text="Test rule.",
                Severity="warning",
            ),
            ScheduleConfig(
                Newsletter_Type="tdr",
                Mode="academic_year",
                Submission_Deadline_Description="noon",
                Deadline_Time=time(12, 0, 0),
                Is_Daily=True,
            ),
        ]
    )
    await db.commit()

    resp = await client.get("/api/v1/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert all(count > 0 for count in body["counts"].values())
