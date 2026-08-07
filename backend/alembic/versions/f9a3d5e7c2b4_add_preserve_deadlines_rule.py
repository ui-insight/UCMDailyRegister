"""add preserve deadlines rule

Revision ID: f9a3d5e7c2b4
Revises: e4b7c9d2a1f8
Create Date: 2026-08-07 14:00:00.000000

Add Joy's standing rule that deadlines and other actionable dates
survive condensing edits. Actionable information outranks conciseness:
shorten surrounding prose instead of deleting deadlines. Idempotent;
touches only the managed preserve_action_deadlines rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "f9a3d5e7c2b4"
down_revision: str | Sequence[str] | None = "e4b7c9d2a1f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PRESERVE_DEADLINES_RULE_TEXT = (
    "Preserve every deadline and actionable date from the original "
    "submission: registration, application, abstract, proposal, "
    "nomination and submission deadlines, event dates and times, "
    "application periods, registration requirements and eligibility "
    "information. Keep multiple deadlines when they serve different "
    "purposes. Never replace a specific deadline with a generic call to "
    "action such as 'Learn more and register'. When editing for "
    "conciseness, shorten the surrounding prose instead of removing "
    "deadlines. Example: 'Registration closes Oct. 23. Abstract "
    "submissions are due Oct. 16. Learn more and register.' is correct; "
    "dropping either date is not."
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
        rule_key="preserve_action_deadlines",
        category="content_filtering",
        rule_text=PRESERVE_DEADLINES_RULE_TEXT,
        severity="error",
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        style_rules.delete().where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "preserve_action_deadlines",
            style_rules.c.Rule_Text == PRESERVE_DEADLINES_RULE_TEXT,
        )
    )
