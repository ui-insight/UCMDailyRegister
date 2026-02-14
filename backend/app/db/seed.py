"""Seed the database with style rules, sections, and schedule configs from JSON files."""

import asyncio
import json
from datetime import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import async_session_factory, engine
from app.db.base import Base
import app.models  # noqa: F401
from app.models.section import NewsletterSection
from app.models.style_rule import StyleRule
from app.models.schedule_config import ScheduleConfig

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


async def seed_sections(session: AsyncSession) -> None:
    for newsletter_type, filename in [("tdr", "tdr_sections.json"), ("myui", "myui_sections.json")]:
        filepath = DATA_DIR / "sections" / filename
        sections = json.loads(filepath.read_text())
        for s in sections:
            existing = await session.execute(
                select(NewsletterSection).where(
                    NewsletterSection.newsletter_type == newsletter_type,
                    NewsletterSection.slug == s["slug"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            section = NewsletterSection(
                newsletter_type=newsletter_type,
                name=s["name"],
                slug=s["slug"],
                display_order=s["display_order"],
                description=s.get("description"),
                requires_image=s.get("requires_image", False),
                image_dimensions=s.get("image_dimensions"),
            )
            session.add(section)
    await session.commit()


async def seed_style_rules(session: AsyncSession) -> None:
    for rule_set, filename in [
        ("shared", "shared_rules.json"),
        ("tdr", "tdr_rules.json"),
        ("myui", "myui_rules.json"),
    ]:
        filepath = DATA_DIR / "style_rules" / filename
        rules = json.loads(filepath.read_text())
        for r in rules:
            existing = await session.execute(
                select(StyleRule).where(
                    StyleRule.rule_set == rule_set,
                    StyleRule.rule_key == r["rule_key"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            rule = StyleRule(
                rule_set=rule_set,
                category=r["category"],
                rule_key=r["rule_key"],
                rule_text=r["rule_text"],
                severity=r.get("severity", "warning"),
            )
            session.add(rule)
    await session.commit()


async def seed_schedule_configs(session: AsyncSession) -> None:
    filepath = DATA_DIR / "schedule" / "schedule_config.json"
    configs = json.loads(filepath.read_text())
    for c in configs:
        existing = await session.execute(
            select(ScheduleConfig).where(
                ScheduleConfig.newsletter_type == c["newsletter_type"],
                ScheduleConfig.mode == c["mode"],
            )
        )
        if existing.scalar_one_or_none():
            continue

        h, m, s = (int(x) for x in c["deadline_time"].split(":"))
        config = ScheduleConfig(
            newsletter_type=c["newsletter_type"],
            mode=c["mode"],
            submission_deadline_description=c["submission_deadline_description"],
            deadline_day_of_week=c.get("deadline_day_of_week"),
            deadline_time=time(h, m, s),
            publish_day_of_week=c.get("publish_day_of_week"),
            is_daily=c.get("is_daily", False),
            active_start_month=c.get("active_start_month"),
            active_end_month=c.get("active_end_month"),
        )
        session.add(config)
    await session.commit()


async def seed_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await seed_sections(session)
        print("Seeded newsletter sections.")
        await seed_style_rules(session)
        print("Seeded style rules.")
        await seed_schedule_configs(session)
        print("Seeded schedule configs.")
    print("Database seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_all())
