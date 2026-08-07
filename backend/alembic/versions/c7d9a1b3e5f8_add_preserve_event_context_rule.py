"""add preserve event context rule

Revision ID: c7d9a1b3e5f8
Revises: b3e5f7a9c1d6
Create Date: 2026-08-07 14:00:00.000000

Add Joy's standing rule that meaningful event context survives
condensing edits: traditions, participant activities, routes and
logistics are preserved; conciseness comes from tightening wording,
not deleting them. Idempotent; touches only the managed
preserve_event_context rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "c7d9a1b3e5f8"
down_revision: str | Sequence[str] | None = "b3e5f7a9c1d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PRESERVE_EVENT_CONTEXT_RULE_TEXT = (
    "When condensing, distinguish unnecessary repetition from meaningful "
    "context. Preserve traditions and ceremonies, participant activities, "
    "routes, locations and event logistics, notable event features, and "
    "details that help readers visualize or understand the event. Achieve "
    "conciseness by tightening wording, not by deleting these details. "
    "Example: 'Sororities will open bids at 11:15 a.m. and run home to "
    "their chapters down Idaho Avenue.' is correct; shortening it to "
    "'Sororities will open bids at 11:15 a.m.' removes a meaningful part "
    "of the event and is not."
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
        rule_key="preserve_event_context",
        category="content_filtering",
        rule_text=PRESERVE_EVENT_CONTEXT_RULE_TEXT,
        severity="warning",
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        style_rules.delete().where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "preserve_event_context",
            style_rules.c.Rule_Text == PRESERVE_EVENT_CONTEXT_RULE_TEXT,
        )
    )
