"""Tests for the reference-data seeder.

The seed runs on every container start, so it must be insert-only by default:
staff edits to style rules, allowed values, and schedule configs made through
the app must survive a redeploy. SEED_OVERWRITE=1 deliberately resets those
fields to the JSON seed files.
"""

import pytest
from sqlalchemy import select

from app.db import seed
from app.models.allowed_value import AllowedValue
from app.models.schedule_config import ScheduleConfig
from app.models.style_rule import StyleRule
from tests.conftest import TestSession


async def seed_everything() -> None:
    async with TestSession() as session:
        await seed.seed_allowed_values(session)
        await seed.seed_sections(session)
        await seed.seed_style_rules(session)
        await seed.seed_schedule_configs(session)
        await seed.seed_blackout_dates(session)


async def get_one(model, *conditions):
    async with TestSession() as session:
        result = await session.execute(select(model).where(*conditions))
        return result.scalars().first()


async def count_all(model) -> int:
    async with TestSession() as session:
        result = await session.execute(select(model))
        return len(result.scalars().all())


@pytest.mark.asyncio
class TestSeed:
    async def test_fresh_database_seeds_completely_and_is_idempotent(self):
        await seed_everything()
        first_counts = (
            await count_all(AllowedValue),
            await count_all(StyleRule),
            await count_all(ScheduleConfig),
        )
        assert all(count > 0 for count in first_counts)

        await seed_everything()
        second_counts = (
            await count_all(AllowedValue),
            await count_all(StyleRule),
            await count_all(ScheduleConfig),
        )
        assert second_counts == first_counts

    async def test_reseed_preserves_app_edits(self):
        await seed_everything()

        async with TestSession() as session:
            rule = (await session.execute(select(StyleRule))).scalars().first()
            rule_key = (rule.Rule_Set, rule.Rule_Key)
            rule.Rule_Text = "Edited by staff in the app"
            rule.Severity = "error"

            value = (await session.execute(select(AllowedValue))).scalars().first()
            value_key = (value.Value_Group, value.Code)
            value.Label = "Staff-edited label"

            config = (await session.execute(select(ScheduleConfig))).scalars().first()
            config_key = (config.Newsletter_Type, config.Mode)
            config.Submission_Deadline_Description = "Noon Wednesdays during the academic year"
            await session.commit()

        await seed_everything()

        rule = await get_one(
            StyleRule, StyleRule.Rule_Set == rule_key[0], StyleRule.Rule_Key == rule_key[1]
        )
        assert rule.Rule_Text == "Edited by staff in the app"
        assert rule.Severity == "error"

        value = await get_one(
            AllowedValue,
            AllowedValue.Value_Group == value_key[0],
            AllowedValue.Code == value_key[1],
        )
        assert value.Label == "Staff-edited label"

        config = await get_one(
            ScheduleConfig,
            ScheduleConfig.Newsletter_Type == config_key[0],
            ScheduleConfig.Mode == config_key[1],
        )
        assert config.Submission_Deadline_Description == "Noon Wednesdays during the academic year"

    async def test_seed_overwrite_flag_resets_to_json_values(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        await seed_everything()

        async with TestSession() as session:
            rule = (await session.execute(select(StyleRule))).scalars().first()
            rule_key = (rule.Rule_Set, rule.Rule_Key)
            original_text = rule.Rule_Text
            rule.Rule_Text = "Edited by staff in the app"
            await session.commit()

        monkeypatch.setenv("SEED_OVERWRITE", "1")
        await seed_everything()

        rule = await get_one(
            StyleRule, StyleRule.Rule_Set == rule_key[0], StyleRule.Rule_Key == rule_key[1]
        )
        assert rule.Rule_Text == original_text
