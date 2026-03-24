"""Seed the database with reference data from JSON files.

Seeds AllowedValue controlled vocabulary, newsletter sections, style rules,
and schedule configurations. Idempotent — skips records that already exist
based on unique key combinations.
"""

import asyncio
import json
from datetime import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import async_session_factory, engine
from app.db.base import Base
import app.models  # noqa: F401 — ensure all models registered with Base
from app.models.allowed_value import AllowedValue
from app.models.section import NewsletterSection
from app.models.style_rule import StyleRule
from app.models.blackout_date import BlackoutDate
from app.models.schedule_config import ScheduleConfig

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


async def seed_allowed_values(session: AsyncSession) -> None:
    """Seed the AllowedValue table from allowed_values.json."""
    filepath = DATA_DIR / "allowed_values" / "allowed_values.json"
    values = json.loads(filepath.read_text())
    for v in values:
        existing = await session.execute(
            select(AllowedValue).where(
                AllowedValue.Value_Group == v["Value_Group"],
                AllowedValue.Code == v["Code"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        record = AllowedValue(
            Value_Group=v["Value_Group"],
            Code=v["Code"],
            Label=v["Label"],
            Display_Order=v.get("Display_Order", 0),
            Visibility_Role=v.get("Visibility_Role", "public"),
            Description=v.get("Description"),
        )
        session.add(record)
    await session.commit()


async def seed_sections(session: AsyncSession) -> None:
    """Seed newsletter sections from tdr_sections.json and myui_sections.json."""
    for newsletter_type, filename in [("tdr", "tdr_sections.json"), ("myui", "myui_sections.json")]:
        filepath = DATA_DIR / "sections" / filename
        sections = json.loads(filepath.read_text())
        for s in sections:
            existing = await session.execute(
                select(NewsletterSection).where(
                    NewsletterSection.Newsletter_Type == newsletter_type,
                    NewsletterSection.Slug == s["slug"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            section = NewsletterSection(
                Newsletter_Type=newsletter_type,
                Name=s["name"],
                Slug=s["slug"],
                Display_Order=s["display_order"],
                Description=s.get("description"),
                Requires_Image=s.get("requires_image", False),
                Image_Dimensions=s.get("image_dimensions"),
            )
            session.add(section)
    await session.commit()


async def seed_style_rules(session: AsyncSession) -> None:
    """Seed style rules from shared_rules.json, tdr_rules.json, myui_rules.json."""
    for rule_set, filename in [
        ("shared", "shared_rules.json"),
        ("tdr", "tdr_rules.json"),
        ("myui", "myui_rules.json"),
    ]:
        filepath = DATA_DIR / "style_rules" / filename
        rules = json.loads(filepath.read_text())
        for r in rules:
            result = await session.execute(
                select(StyleRule).where(
                    StyleRule.Rule_Set == rule_set,
                    StyleRule.Rule_Key == r["rule_key"],
                )
            )
            existing_rule = result.scalar_one_or_none()
            if existing_rule:
                # Update rule text and severity if they've changed
                if (
                    existing_rule.Rule_Text != r["rule_text"]
                    or existing_rule.Severity != r.get("severity", "warning")
                    or existing_rule.Category != r["category"]
                ):
                    existing_rule.Rule_Text = r["rule_text"]
                    existing_rule.Severity = r.get("severity", "warning")
                    existing_rule.Category = r["category"]
                continue
            rule = StyleRule(
                Rule_Set=rule_set,
                Category=r["category"],
                Rule_Key=r["rule_key"],
                Rule_Text=r["rule_text"],
                Severity=r.get("severity", "warning"),
            )
            session.add(rule)
    await session.commit()


async def seed_schedule_configs(session: AsyncSession) -> None:
    """Seed schedule configurations from schedule_config.json."""
    filepath = DATA_DIR / "schedule" / "schedule_config.json"
    configs = json.loads(filepath.read_text())
    for c in configs:
        existing = await session.execute(
            select(ScheduleConfig).where(
                ScheduleConfig.Newsletter_Type == c["newsletter_type"],
                ScheduleConfig.Mode == c["mode"],
            )
        )
        if existing.scalar_one_or_none():
            continue

        h, m, s = (int(x) for x in c["deadline_time"].split(":"))
        config = ScheduleConfig(
            Newsletter_Type=c["newsletter_type"],
            Mode=c["mode"],
            Submission_Deadline_Description=c["submission_deadline_description"],
            Deadline_Day_Of_Week=c.get("deadline_day_of_week"),
            Deadline_Time=time(h, m, s),
            Publish_Day_Of_Week=c.get("publish_day_of_week"),
            Is_Daily=c.get("is_daily", False),
            Active_Start_Month=c.get("active_start_month"),
            Active_End_Month=c.get("active_end_month"),
        )
        session.add(config)
    await session.commit()


async def seed_blackout_dates(session: AsyncSession) -> None:
    """Seed blackout dates from blackout_dates.json."""
    filepath = DATA_DIR / "schedule" / "blackout_dates.json"
    dates = json.loads(filepath.read_text())
    for d in dates:
        existing = await session.execute(
            select(BlackoutDate).where(
                BlackoutDate.Blackout_Date == d["date"],
                BlackoutDate.Newsletter_Type == d.get("newsletter_type"),
            )
        )
        if existing.scalar_one_or_none():
            continue
        record = BlackoutDate(
            Blackout_Date=d["date"],
            Newsletter_Type=d.get("newsletter_type"),
            Description=d.get("description"),
        )
        session.add(record)
    await session.commit()


async def seed_all() -> None:
    """Create all tables and seed reference data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await seed_allowed_values(session)
        print("Seeded allowed values.")
        await seed_sections(session)
        print("Seeded newsletter sections.")
        await seed_style_rules(session)
        print("Seeded style rules.")
        await seed_schedule_configs(session)
        print("Seeded schedule configs.")
        await seed_blackout_dates(session)
        print("Seeded blackout dates.")
    print("Database seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_all())
