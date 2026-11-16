"""Newsletter-local "today" (#492).

The containers run in UTC. At 01:30 UTC on Nov. 17 it is still 5:30 p.m. on
Monday, Nov. 16 in Moscow, Idaho, so schedule and date logic must see Nov. 16.
"""

from datetime import UTC, date, datetime, timezone

import pytest
from freezegun import freeze_time
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, settings
from app.db import seed
from app.models.schedule_config import ScheduleConfig
from app.models.submission import Submission
from app.services import schedule_service
from app.services.ai.editor import AIEditor
from app.utils import clock
from app.utils.style_checks import detect_weekday_date_mismatches
from tests.test_date_conflict_flags import DATE_RULES, RecordingProvider

# 5:30 p.m. PST on Monday, Nov. 16, 2026.
EVENING_PACIFIC = datetime(2026, 11, 17, 1, 30, tzinfo=UTC)


def test_default_zone_is_pacific():
    assert Settings.model_fields["newsletter_timezone"].default == "America/Los_Angeles"


def test_local_today_in_the_evening_is_still_the_pacific_date(freeze_clock):
    freeze_clock(EVENING_PACIFIC)

    assert clock.local_today() == date(2026, 11, 16)
    now = clock.local_now()
    assert (now.hour, now.minute) == (17, 30)
    assert now.utcoffset().total_seconds() == -8 * 3600


def test_local_today_during_daylight_time(freeze_clock):
    # 5:30 p.m. PDT on July 1.
    freeze_clock(datetime(2026, 7, 2, 0, 30, tzinfo=UTC))

    assert clock.local_today() == date(2026, 7, 1)


def test_local_today_rolls_over_at_local_midnight(freeze_clock):
    freeze_clock(datetime(2026, 11, 17, 8, 0, tzinfo=UTC))  # midnight PST

    assert clock.local_today() == date(2026, 11, 17)


def test_freezegun_also_freezes_the_clock():
    with freeze_time("2026-11-17 01:30:00"):
        assert clock.local_today() == date(2026, 11, 16)


def test_zone_is_configurable(freeze_clock, monkeypatch):
    freeze_clock(EVENING_PACIFIC)
    monkeypatch.setattr(settings, "newsletter_timezone", "UTC")

    assert clock.local_today() == date(2026, 11, 17)


def test_invalid_zone_is_rejected():
    with pytest.raises(ValidationError, match="NEWSLETTER_TIMEZONE"):
        Settings(newsletter_timezone="Mars/Olympus_Mons")


@pytest.mark.parametrize(
    "stored",
    [
        datetime(2026, 11, 17, 1, 30),  # naive, stored as UTC
        datetime(2026, 11, 17, 1, 30, tzinfo=timezone.utc),
    ],
)
def test_local_date_converts_stored_utc_timestamps(stored):
    assert clock.local_date(stored) == date(2026, 11, 16)


def test_next_publish_date_defaults_to_local_today(freeze_clock):
    freeze_clock(EVENING_PACIFIC)
    daily = ScheduleConfig(Newsletter_Type="tdr", Mode="academic_year", Is_Daily=True)

    # Monday evening: the next daily issue is Tuesday, not Wednesday.
    assert schedule_service.get_next_publish_date(daily) == date(2026, 11, 17)


@pytest.mark.asyncio
async def test_active_schedule_endpoint_uses_local_today(
    client: AsyncClient,
    db: AsyncSession,
    freeze_clock,
):
    await seed.seed_schedule_configs(db)
    await seed.seed_blackout_dates(db)
    freeze_clock(EVENING_PACIFIC)

    evening = await client.get("/api/v1/schedule/active", params={"newsletter_type": "tdr"})
    explicit = await client.get(
        "/api/v1/schedule/active",
        params={"newsletter_type": "tdr", "for_date": "2026-11-16"},
    )

    assert evening.status_code == 200
    assert evening.json()["next_publish_date"] == explicit.json()["next_publish_date"]


def test_style_checks_default_to_local_today(freeze_clock):
    # A yearless date more than 60 days before the reference rolls to next
    # year. Sept. 17 is 60 days before Nov. 16 (stays 2026, a Thursday) but
    # 61 days before Nov. 17 (would become 2027, a Friday).
    freeze_clock(EVENING_PACIFIC)

    assert detect_weekday_date_mismatches("Thursday, Sept. 17") == []
    assert detect_weekday_date_mismatches("Friday, Sept. 17") == ["Friday, Sept. 17"]


@pytest.mark.asyncio
async def test_submission_date_for_ai_edit_is_the_local_date():
    """An item submitted at 5:30 p.m. Pacific on Nov. 16 is a Nov. 16 submission (#410)."""
    body = "The talk is 2 p.m. Wednesday, Dec. 2, in Example Hall."
    provider = RecordingProvider(body)
    editor = AIEditor(provider)

    async def no_rules(*_args, **_kwargs):
        return DATE_RULES

    editor.load_style_rules = no_rules
    submission = Submission(
        Id="synthetic-evening",
        Category="faculty_staff",
        Target_Newsletter="tdr",
        Original_Headline="Guest talk",
        Original_Body=body,
        Submitter_Name="Synthetic submitter",
        Submitter_Email="synthetic@example.edu",
        Links=[],
        # Created_At is stored as naive UTC.
        Created_At=datetime(2026, 11, 17, 1, 30),
    )

    await editor.edit_submission(None, submission, "tdr")

    assert "**Submission Date:** Monday, November 16, 2026" in provider.user_prompts[0]
