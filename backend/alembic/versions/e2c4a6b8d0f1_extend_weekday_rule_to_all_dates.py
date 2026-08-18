"""extend near-term weekday rule to all dates

Revision ID: e2c4a6b8d0f1
Revises: c5e7a9b1d3f6
Create Date: 2026-08-18 10:30:00.000000

Joy clarified that every date within the next 30 days needs its weekday,
including deadlines and other non-event dates. The focused upsert preserves
unrelated staff-managed rules.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "e2c4a6b8d0f1"
down_revision: str | Sequence[str] | None = "c5e7a9b1d3f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DAY_OF_WEEK_RULE_TEXT = (
    "Pair the correct day of the week with every date that falls within the "
    "next 30 days, based on the applicable calendar year. This applies to "
    "event dates, deadlines, registration deadlines, application deadlines, "
    "enrollment deadlines, submission deadlines, drawing dates, promotional "
    "dates and every other date reference. Scan the entire submission before "
    "finalizing so non-event dates are not overlooked. Dates beyond 30 days "
    "do not need a day of the week."
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


def _upsert_rule(connection: sa.Connection) -> None:
    existing_id = connection.execute(
        sa.select(style_rules.c.Id).where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "day_of_week_with_dates",
        )
    ).scalar_one_or_none()
    values = {
        "Category": "formatting",
        "Rule_Text": DAY_OF_WEEK_RULE_TEXT,
        "Is_Active": True,
        "Severity": "error",
    }
    if existing_id:
        connection.execute(
            style_rules.update().where(style_rules.c.Id == existing_id).values(**values)
        )
    else:
        connection.execute(
            style_rules.insert().values(
                Id=str(uuid.uuid4()),
                Rule_Set="shared",
                Rule_Key="day_of_week_with_dates",
                **values,
            )
        )


def upgrade() -> None:
    _upsert_rule(op.get_bind())


def downgrade() -> None:
    # Text-only revision of a managed rule; prior wording is not restored.
    pass
