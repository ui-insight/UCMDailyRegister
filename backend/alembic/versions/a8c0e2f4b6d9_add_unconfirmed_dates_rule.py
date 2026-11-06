"""add unconfirmed dates rule

Revision ID: a8c0e2f4b6d9
Revises: 77b37be60275
Create Date: 2026-11-06 16:00:00.000000

Joy's decision on dates the AI can't confirm (#410): a date without a year
is kept as written and flagged for the editor when it has already passed or
its year is unclear. The deterministic check that raises these flags reports
under this rule, at warning severity, so the flags never send the model into
a compliance repair and staff can switch the rule off. Idempotent; touches
only the managed unconfirmed_dates rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "a8c0e2f4b6d9"
down_revision: str | Sequence[str] | None = "77b37be60275"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RULE_KEY = "unconfirmed_dates"
CATEGORY = "formatting"
SEVERITY = "warning"
RULE_TEXT = (
    "Keep a date without a year exactly as written; never add a year or move "
    "it to a different date. When a date appears to have already passed by "
    "the submission date, flag it DATE HAS PASSED: CONFIRM DATE. When its "
    "next occurrence is far enough out that the intended year is unclear, "
    "flag it CONFIRM YEAR. Do not add a weekday to either kind of date; if "
    "one is added, flag it DAY OF WEEK NOT VERIFIED. Report these flags in "
    "the flags list for the editor; do not write them into the headline or body."
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


def upgrade() -> None:
    connection = op.get_bind()
    existing_id = connection.execute(
        sa.select(style_rules.c.Id).where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == RULE_KEY,
        )
    ).scalar_one_or_none()
    values = {"Category": CATEGORY, "Rule_Text": RULE_TEXT, "Severity": SEVERITY}
    if existing_id:
        connection.execute(
            style_rules.update().where(style_rules.c.Id == existing_id).values(**values)
        )
    else:
        connection.execute(
            style_rules.insert().values(
                Id=str(uuid.uuid4()),
                Rule_Set="shared",
                Rule_Key=RULE_KEY,
                Is_Active=True,
                **values,
            )
        )


def downgrade() -> None:
    op.get_bind().execute(
        style_rules.delete().where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == RULE_KEY,
        )
    )
