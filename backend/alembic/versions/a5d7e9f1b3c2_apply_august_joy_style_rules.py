"""apply August Joy style rules

Revision ID: a5d7e9f1b3c2
Revises: f3a6b9c2d5e8
Create Date: 2026-08-05 14:00:00.000000

Promote the repeatedly requested event-detail order to a mandatory rule and
add Joy's standing capitalization rule for "Vandal Gear". The migration is
idempotent and narrowly updates only these two managed rule keys.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "a5d7e9f1b3c2"
down_revision: str | Sequence[str] | None = "f3a6b9c2d5e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EVENT_RULE_TEXT = (
    "Order event details as: time, day, date, location. Example: '3-4 p.m. "
    "Wednesday, Feb. 12, in the Pitman Center Vandal Ballroom'. Do not "
    "reorder or omit these elements. If the event is more than one month "
    "away, omit the day of the week."
)
VANDAL_GEAR_RULE_TEXT = (
    "Always write 'Vandal Gear' as two capitalized words. Replace "
    "'VandalGear', 'Vandal gear' or other variants with 'Vandal Gear'."
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
    rule_key: str,
    category: str,
    rule_text: str,
    severity: str,
) -> None:
    existing_id = connection.execute(
        sa.select(style_rules.c.Id).where(
            style_rules.c.Rule_Set == "shared",
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
                Rule_Set="shared",
                Rule_Key=rule_key,
                **values,
            )
        )


def upgrade() -> None:
    connection = op.get_bind()
    _upsert_rule(
        connection,
        rule_key="event_detail_ordering",
        category="formatting",
        rule_text=EVENT_RULE_TEXT,
        severity="error",
    )
    _upsert_rule(
        connection,
        rule_key="vandal_gear_capitalization",
        category="terminology",
        rule_text=VANDAL_GEAR_RULE_TEXT,
        severity="error",
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        style_rules.delete().where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "vandal_gear_capitalization",
            style_rules.c.Rule_Text == VANDAL_GEAR_RULE_TEXT,
        )
    )
    connection.execute(
        style_rules.update()
        .where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "event_detail_ordering",
            style_rules.c.Rule_Text == EVENT_RULE_TEXT,
        )
        .values(Severity="warning")
    )
