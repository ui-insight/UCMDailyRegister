"""require date continuation commas

Revision ID: e4b7c9d2a1f8
Revises: d8f2a6c4e9b3
Create Date: 2026-08-07 14:00:00.000000

Extend the AP date style rule with the continuation-comma requirement:
a comma must follow a month-and-day date when the sentence continues,
including within ranges and sequences. Idempotent; touches only the
managed ap_style_dates rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "e4b7c9d2a1f8"
down_revision: str | Sequence[str] | None = "d8f2a6c4e9b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


AP_DATES_RULE_TEXT = (
    "Use AP style for dates: abbreviate months with 6+ letters (Jan., "
    "Feb., Aug., Sept., Oct., Nov., Dec.). Spell out March, April, May, "
    "June, July. Use numerals for dates (Jan. 5, not January fifth). When "
    "a month-and-day date appears mid-sentence, place a comma after the "
    "date if the sentence continues: 'The conference runs Monday, Oct. "
    "31, and Tuesday, Nov. 1.' 'The workshop is Wednesday, Sept. 16, in "
    "the Pitman Center.' Apply the comma to every date in a range or "
    "sequence."
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
        rule_key="ap_style_dates",
        category="formatting",
        rule_text=AP_DATES_RULE_TEXT,
        severity="warning",
    )


def downgrade() -> None:
    # Text-only revision of managed rules; the prior wording is not
    # restored on downgrade.
    pass
