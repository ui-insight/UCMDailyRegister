"""Tests for recurring message management and issue integration."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.section import NewsletterSection


async def _seed_section(
    db: AsyncSession,
    *,
    newsletter_type: str,
    section_id: str,
    name: str,
    slug: str,
) -> NewsletterSection:
    section = NewsletterSection(
        Id=section_id,
        Newsletter_Type=newsletter_type,
        Name=name,
        Slug=slug,
        Display_Order=1,
        Is_Active=True,
    )
    db.add(section)
    await db.commit()
    return section


@pytest.mark.asyncio
class TestRecurringMessageCRUD:
    async def test_staff_can_create_list_update_and_delete_recurring_message(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await _seed_section(
            db,
            newsletter_type="myui",
            section_id="myui-news",
            name="News and Updates",
            slug="news-and-updates",
        )

        create_resp = await client.post(
            "/api/v1/recurring-messages",
            json={
                "Newsletter_Type": "myui",
                "Section_Id": "myui-news",
                "Headline": "First Monday reminder",
                "Body": "Remember to check the student portal.",
                "Start_Date": "2026-04-06",
                "Recurrence_Type": "monthly_nth_weekday",
                "Recurrence_Interval": 1,
                "End_Date": "2026-07-06",
            },
            headers={"X-User-Role": "staff"},
        )
        assert create_resp.status_code == 201
        message_id = create_resp.json()["Id"]

        list_resp = await client.get(
            "/api/v1/recurring-messages?newsletter_type=myui",
            headers={"X-User-Role": "staff"},
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        update_resp = await client.patch(
            f"/api/v1/recurring-messages/{message_id}",
            json={"Is_Active": False},
            headers={"X-User-Role": "staff"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["Is_Active"] is False

        delete_resp = await client.delete(
            f"/api/v1/recurring-messages/{message_id}",
            headers={"X-User-Role": "staff"},
        )
        assert delete_resp.status_code == 204

    async def test_public_user_cannot_manage_recurring_messages(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await _seed_section(
            db,
            newsletter_type="tdr",
            section_id="tdr-employee-news",
            name="Employee News",
            slug="employee-news",
        )

        resp = await client.post(
            "/api/v1/recurring-messages",
            json={
                "Newsletter_Type": "tdr",
                "Section_Id": "tdr-employee-news",
                "Headline": "Weekly reminder",
                "Body": "Wear silver and gold on Friday.",
                "Start_Date": "2026-04-03",
                "Recurrence_Type": "weekly",
                "Recurrence_Interval": 1,
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestRecurringMessageIssueFlow:
    async def test_assemble_newsletter_auto_adds_matching_recurring_message(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await _seed_section(
            db,
            newsletter_type="tdr",
            section_id="tdr-employee-news",
            name="Employee News",
            slug="employee-news",
        )

        create_resp = await client.post(
            "/api/v1/recurring-messages",
            json={
                "Newsletter_Type": "tdr",
                "Section_Id": "tdr-employee-news",
                "Headline": "Vandal Spirit Friday",
                "Body": "Wear Vandal gear every Friday.",
                "Start_Date": "2026-04-03",
                "Recurrence_Type": "weekly",
                "Recurrence_Interval": 1,
            },
            headers={"X-User-Role": "staff"},
        )
        message_id = create_resp.json()["Id"]

        assemble_resp = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": "2026-04-03"},
        )
        assert assemble_resp.status_code == 200
        external_items = assemble_resp.json()["External_Items"]
        assert len(external_items) == 1
        assert external_items[0]["Source_Type"] == "recurring_message"
        assert external_items[0]["Source_Id"] == message_id

    async def test_skip_prevents_reassembly_and_add_restores_message(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        await _seed_section(
            db,
            newsletter_type="tdr",
            section_id="tdr-employee-news",
            name="Employee News",
            slug="employee-news",
        )

        create_resp = await client.post(
            "/api/v1/recurring-messages",
            json={
                "Newsletter_Type": "tdr",
                "Section_Id": "tdr-employee-news",
                "Headline": "Campaign week",
                "Body": "This message should appear during the campaign window.",
                "Start_Date": "2026-04-01",
                "Recurrence_Type": "date_range",
                "Recurrence_Interval": 1,
                "End_Date": "2026-04-07",
            },
            headers={"X-User-Role": "staff"},
        )
        message_id = create_resp.json()["Id"]

        assemble_resp = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": "2026-04-03"},
        )
        newsletter_id = assemble_resp.json()["Id"]
        assert len(assemble_resp.json()["External_Items"]) == 1

        skip_resp = await client.post(
            f"/api/v1/newsletters/{newsletter_id}/recurring-messages/{message_id}/skip",
            headers={"X-User-Role": "staff"},
        )
        assert skip_resp.status_code == 204

        candidates_after_skip = await client.get(
            f"/api/v1/newsletters/{newsletter_id}/recurring-messages",
            headers={"X-User-Role": "staff"},
        )
        assert candidates_after_skip.status_code == 200
        assert candidates_after_skip.json()[0]["Skipped"] is True
        assert candidates_after_skip.json()[0]["Selected"] is False

        reassemble_resp = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": "2026-04-03"},
        )
        assert reassemble_resp.status_code == 200
        assert reassemble_resp.json()["External_Items"] == []

        add_resp = await client.post(
            f"/api/v1/newsletters/{newsletter_id}/recurring-messages/{message_id}",
            headers={"X-User-Role": "staff"},
        )
        assert add_resp.status_code == 201
        assert add_resp.json()["Source_Type"] == "recurring_message"

        candidates_after_add = await client.get(
            f"/api/v1/newsletters/{newsletter_id}/recurring-messages",
            headers={"X-User-Role": "staff"},
        )
        assert candidates_after_add.status_code == 200
        assert candidates_after_add.json()[0]["Selected"] is True
        assert candidates_after_add.json()[0]["Skipped"] is False
