"""ban generic CTA filler words

Revision ID: a6c8e2f4b7d9
Revises: f9a3d5e7c2b4
Create Date: 2026-08-07 14:00:00.000000

Strengthen the cta_structure rule: no call to action may be built on
filler words such as 'here' or 'click here'. Link the action verb or
the object of the action instead. Idempotent; touches only the managed
cta_structure rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "a6c8e2f4b7d9"
down_revision: str | Sequence[str] | None = "f9a3d5e7c2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CTA_RULE_TEXT = (
    "Structure announcements around a clear call to action: open with the "
    "action the reader should take, follow with context, dates and "
    "incentives, and close with an explicit final call to action such as "
    "'Learn more and register'. Replace vague instructions with explicit "
    "actions. Do not introduce audience qualifiers that are not in the "
    "original submission. When the submission provides a contact's full "
    "name, use it rather than a bare email address. Never build a call to "
    "action on filler words: no CTA may contain 'here', 'click here', "
    "'learn more here', 'register here', 'apply here' or 'sign up here'. "
    "Link the action verb or the object of the action instead: 'Sign up', "
    "'Register for the workshop', 'Apply for the scholarship' — never "
    "'Sign up here'."
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
        rule_key="cta_structure",
        category="voice",
        rule_text=CTA_RULE_TEXT,
        severity="warning",
    )


def downgrade() -> None:
    # Text-only revision of managed rules; the prior wording is not
    # restored on downgrade.
    pass
