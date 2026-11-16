"""Tests for the data-driven newsletter section catalog."""

import io

import pytest
import sqlalchemy as sa
from docx import Document
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import seed
from app.models.section import NewsletterSection


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


@pytest.mark.asyncio
async def test_tdr_upcoming_events_heading_follows_employee_news(
    client: AsyncClient,
    db: AsyncSession,
):
    """#443 phase 1: Upcoming events replaces Today's Events, right after Employee News."""
    await seed.seed_sections(db)

    response = await client.get("/api/v1/sections", params={"newsletter_type": "tdr"})

    sections = response.json()
    assert [section["Name"] for section in sections[:4]] == [
        "Employee News",
        "Upcoming events",
        "Feature Stories",
        "U of I in the News",
    ]
    assert "Today's Events" not in [section["Name"] for section in sections]
    # The calendar section keeps its slug, so imports and past editions stay attached.
    assert sections[1]["Slug"] == "todays-events"
    # Employee Announcements stays in the order (#441).
    assert "employee-announcements" in [section["Slug"] for section in sections]


@pytest.mark.asyncio
async def test_myui_events_this_week_heading(
    client: AsyncClient,
    db: AsyncSession,
):
    await seed.seed_sections(db)

    response = await client.get("/api/v1/sections", params={"newsletter_type": "myui"})

    sections = response.json()
    assert [section["Name"] for section in sections[:3]] == [
        "Highlighted Events",
        "Events this week",
        "News and Updates",
    ]
    assert sections[1]["Slug"] == "weekly-events"


@pytest.mark.asyncio
async def test_reseeding_does_not_duplicate_events_sections(db: AsyncSession):
    await seed.seed_sections(db)
    await seed.seed_sections(db)

    result = await db.execute(
        sa.select(sa.func.count())
        .select_from(NewsletterSection)
        .where(NewsletterSection.Slug.in_(["todays-events", "weekly-events"]))
    )
    assert result.scalar_one() == 2


async def _create_newsletter(
    client: AsyncClient, staff_headers: dict[str, str], newsletter_type: str
) -> str:
    resp = await client.post(
        "/api/v1/newsletters",
        json={"Newsletter_Type": newsletter_type, "Publish_Date": "2026-11-17"},
        headers=staff_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["Id"]


async def _export_paragraphs(
    client: AsyncClient, staff_headers: dict[str, str], newsletter_id: str
) -> list[str]:
    resp = await client.get(f"/api/v1/newsletters/{newsletter_id}/export", headers=staff_headers)
    assert resp.status_code == 200
    return [p.text for p in Document(io.BytesIO(resp.content)).paragraphs]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("newsletter_type", "heading"),
    [("tdr", "Upcoming events"), ("myui", "Events this week")],
)
async def test_export_keeps_empty_events_heading_with_no_events(
    client: AsyncClient,
    db: AsyncSession,
    staff_headers: dict[str, str],
    newsletter_type: str,
    heading: str,
):
    await seed.seed_sections(db)
    newsletter_id = await _create_newsletter(client, staff_headers, newsletter_type)

    paragraphs = await _export_paragraphs(client, staff_headers, newsletter_id)

    assert heading in paragraphs
    assert paragraphs[paragraphs.index(heading) + 1] == "No events."
    # Other empty sections are still left out of the export.
    assert "Kudos" not in paragraphs
    assert "News and Updates" not in paragraphs


@pytest.mark.asyncio
async def test_export_lists_events_under_the_heading_without_placeholder(
    client: AsyncClient,
    db: AsyncSession,
    staff_headers: dict[str, str],
):
    await seed.seed_sections(db)
    newsletter_id = await _create_newsletter(client, staff_headers, "tdr")
    resp = await client.post(
        f"/api/v1/newsletters/{newsletter_id}/calendar-events",
        json={
            "Source_Id": "synthetic-event-1",
            "Url": "https://example.com/synthetic-event-1",
            "Title": "Synthetic campus lecture",
            "Description": "A made-up talk for tests.",
            "Location": "Test Hall 101",
            "Event_Start": "2026-11-17T12:00:00",
            "Event_End": "2026-11-17T13:00:00",
        },
        headers=staff_headers,
    )
    assert resp.status_code == 201, resp.text

    paragraphs = await _export_paragraphs(client, staff_headers, newsletter_id)

    heading_index = paragraphs.index("Upcoming events")
    assert "No events." not in paragraphs
    assert any("Synthetic campus lecture" in p for p in paragraphs[heading_index + 1 :])
