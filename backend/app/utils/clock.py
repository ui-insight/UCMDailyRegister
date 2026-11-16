"""The current date and time in the newsletter's local time zone (#492).

The containers run in UTC, so ``date.today()`` turns over to tomorrow at
4 p.m. Pacific (5 p.m. during daylight time). Anything that means "today's
calendar date for UCM" (schedule windows, next publish date, recurrence
previews, the reference date for dates without a year) takes it from here
instead, in ``settings.newsletter_timezone``. Stored timestamps such as
``Created_At`` stay in UTC; ``local_date`` converts one to a UCM calendar date.

Every function reads the clock through ``utc_now``, so a test can freeze it
with ``monkeypatch.setattr("app.utils.clock.utc_now", lambda: ...)`` or with
freezegun.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.config import settings


def utc_now() -> datetime:
    """The current instant, timezone-aware, in UTC. Tests patch this."""
    return datetime.now(UTC)


def local_zone() -> ZoneInfo:
    """The newsletter's time zone, from ``NEWSLETTER_TIMEZONE``."""
    return ZoneInfo(settings.newsletter_timezone)


def local_now() -> datetime:
    """The current time in the newsletter's time zone, timezone-aware."""
    return utc_now().astimezone(local_zone())


def local_today() -> date:
    """Today's calendar date in the newsletter's time zone."""
    return local_now().date()


def local_date(moment: datetime) -> date:
    """The newsletter-local calendar date of a stored timestamp.

    Naive timestamps are treated as UTC, which is how the app stores
    ``Created_At`` and similar columns.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(local_zone()).date()
