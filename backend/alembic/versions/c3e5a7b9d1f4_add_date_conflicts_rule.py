"""add date conflicts rule

Revision ID: c3e5a7b9d1f4
Revises: f1b3d5e7a9c2
Create Date: 2026-11-03 15:00:00.000000

Add Joy's Nov. 2026 date policy (#384, #410): keep a conflicting weekday and
date as written and flag the conflict, keep the body date when the headline
disagrees, and resolve dates without a year from the submission date.
Idempotent; touches only the managed date_conflicts rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "c3e5a7b9d1f4"
down_revision: str | Sequence[str] | None = "f1b3d5e7a9c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DATE_CONFLICTS_RULE_TEXT = (
    "Never guess or silently correct a date. When a supplied weekday and "
    "date do not match, keep both exactly as written and add a flag stating"
    " the correct weekday for the date given, for example: DATE CONFLICT: "
    "MARCH 3, 2027, IS A WEDNESDAY, NOT A TUESDAY. When the same event has "
    "different dates in the headline, body, links or notes, keep the body "
    "date and add a flag naming the other date, for example: DATE CONFLICT:"
    " HEADLINE SAYS MARCH 4. When a date has no year, assume the next "
    "upcoming occurrence after the submission date. When adding a missing "
    "weekday, calculate it from the calendar for that resolved year, never "
    "from today's date or the publication date. If the weekday cannot be "
    "verified, add the flag DAY OF WEEK NOT VERIFIED instead of adding a "
    "weekday. Report these conflicts in the flags list for the editor; do "
    "not write them into the headline or body."
)


style_rules = sa.table(
    "style_rules",
    sa.column("Id", sa.String(36)),
    sa.column("Rule_Set", sa.String(50)),
    sa.column("Category", sa.String(100)),
    sa.column("Rule_Key", sa.String(100)),
    sa.column("Rule_Text", sa.Text),
    sa.column("Is_Active", sa.Boolean),
    sa.column("Severity", sa.String(50)),
)


def _upsert_rule(
    connection: sa.Connection,
    *,
    rule_set: str,
    rule_key: str,
    category: str,
    rule_text: str,
    severity: str,
) -> None:
    existing_id = connection.execute(
        sa.select(style_rules.c.Id).where(
            style_rules.c.Rule_Set == rule_set,
            style_rules.c.Rule_Key == rule_key,
        )
    ).scalar_one_or_none()
    values = {
        "Category": category,
        "Rule_Text": rule_text,
        "Is_Active": True,
        "Severity": severity,
    }
    if existing_id:
        connection.execute(
            style_rules.update().where(style_rules.c.Id == existing_id).values(**values)
        )
    else:
        connection.execute(
            style_rules.insert().values(
                Id=str(uuid.uuid4()),
                Rule_Set=rule_set,
                Rule_Key=rule_key,
                **values,
            )
        )


def upgrade() -> None:
    connection = op.get_bind()
    _upsert_rule(
        connection,
        rule_set="shared",
        rule_key="date_conflicts",
        category="formatting",
        rule_text=DATE_CONFLICTS_RULE_TEXT,
        severity="error",
    )


def downgrade() -> None:
    op.get_bind().execute(
        style_rules.delete().where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "date_conflicts",
        )
    )
