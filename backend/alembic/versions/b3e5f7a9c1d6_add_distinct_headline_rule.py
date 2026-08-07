"""add distinct headline rule

Revision ID: b3e5f7a9c1d6
Revises: a6c8e2f4b7d9
Create Date: 2026-08-07 14:00:00.000000

Add Joy's standing headline rule: the headline must not duplicate or
lightly reword the body's first sentence. It should summarize the
purpose, opportunity or benefit so headline and body each contribute
unique information. Idempotent; touches only the managed
headline_distinct_from_lead rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "b3e5f7a9c1d6"
down_revision: str | Sequence[str] | None = "a6c8e2f4b7d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DISTINCT_HEADLINE_RULE_TEXT = (
    "The headline must not be the first sentence of the body or a minor "
    "rewording of it. Write a headline that summarizes the purpose, "
    "opportunity or benefit of the announcement so the headline and body "
    "each contribute unique information. Example: for a body opening "
    "'Sign up for the sustainability newsletter.', write the headline "
    "'Receive monthly sustainability updates', not 'Sign up for "
    "sustainability newsletter'."
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
        rule_key="headline_distinct_from_lead",
        category="headlines",
        rule_text=DISTINCT_HEADLINE_RULE_TEXT,
        severity="warning",
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        style_rules.delete().where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "headline_distinct_from_lead",
            style_rules.c.Rule_Text == DISTINCT_HEADLINE_RULE_TEXT,
        )
    )
