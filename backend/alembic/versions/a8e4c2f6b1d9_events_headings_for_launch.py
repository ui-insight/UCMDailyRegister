"""put the launch events headings in place in both newsletters

Revision ID: a8e4c2f6b1d9
Revises: 78a5d8e23c00
Create Date: 2026-11-16 15:00:00.000000

Issue #443, phase 1. Joy approved an events heading for each newsletter on
Nov. 2, 2026: ``Upcoming events`` in The Daily Register, replacing Today's
Events and placed right after Employee News, and ``Events this week`` in
My UI. On Nov. 3 she said launch only needs the headings in place so staff
can add events under them; the calendar-driven section is phase 2.

Both newsletters already have a calendar events section (``todays-events``
and ``weekly-events``), which calendar imports and submitted events route
to. This migration renames those rows in place, keeping their Id and slug,
so items already placed in past editions stay attached and visible.
Deactivating them for new rows would hide past editions' events, because
the Builder and Word export show only active sections.

The Daily Register's events heading moves from fourth to second. Feature
Stories and U of I in the News each move down one slot into the place the
old heading left. No other section moves: the rest of Joy's order is still
open in #443 and #441. Idempotent; touches only these four rows.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a8e4c2f6b1d9"
down_revision: str | Sequence[str] | None = "78a5d8e23c00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


newsletter_sections = sa.table(
    "newsletter_sections",
    sa.column("Newsletter_Type", sa.String(50)),
    sa.column("Slug", sa.String(100)),
    sa.column("Name", sa.String(255)),
    sa.column("Display_Order", sa.Integer),
)

# (newsletter type, slug): (name, display order) after and before this change.
UPGRADE = {
    ("tdr", "todays-events"): ("Upcoming events", 2),
    ("tdr", "feature-stories"): ("Feature Stories", 3),
    ("tdr", "uofi-in-the-news"): ("U of I in the News", 4),
    ("myui", "weekly-events"): ("Events this week", 2),
}
DOWNGRADE = {
    ("tdr", "todays-events"): ("Today's Events", 4),
    ("tdr", "feature-stories"): ("Feature Stories", 2),
    ("tdr", "uofi-in-the-news"): ("U of I in the News", 3),
    ("myui", "weekly-events"): ("Weekly Events", 2),
}


def _apply(values: dict[tuple[str, str], tuple[str, int]]) -> None:
    connection = op.get_bind()
    for (newsletter_type, slug), (name, display_order) in values.items():
        connection.execute(
            newsletter_sections.update()
            .where(
                newsletter_sections.c.Newsletter_Type == newsletter_type,
                newsletter_sections.c.Slug == slug,
            )
            .values(Name=name, Display_Order=display_order)
        )


def upgrade() -> None:
    _apply(UPGRADE)


def downgrade() -> None:
    _apply(DOWNGRADE)
