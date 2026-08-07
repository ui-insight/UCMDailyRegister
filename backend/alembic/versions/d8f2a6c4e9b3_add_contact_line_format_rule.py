"""add contact line format rule

Revision ID: d8f2a6c4e9b3
Revises: b6e8f0a2c4d1
Create Date: 2026-08-07 14:00:00.000000

Add Joy's standing contact-line rule: hyperlink contact names with provided
email addresses, retain phone numbers, and never repeat a contact's name in
place of contact information. The migration is idempotent and narrowly
updates only this managed rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "d8f2a6c4e9b3"
down_revision: str | Sequence[str] | None = "b6e8f0a2c4d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONTACT_LINE_RULE_TEXT = (
    "When the original submission provides an email address for a contact "
    "person or unit, hyperlink the person's or unit's name with that email "
    "address instead of displaying the address as plain text. Keep phone "
    "numbers from the original submission. Never repeat the contact's name "
    "in place of contact information: write 'contact Paul Rowley' (name "
    "linked) or 'contact Paul Rowley at 208-885-1234', never 'contact Paul "
    "Rowley at Paul Rowley' or 'contact Paul Rowley at prowley@uidaho.edu'. "
    "In a contact line, 'at' must be followed by meaningful information such "
    "as a phone number or location. If no email address or phone number is "
    "provided, use the name alone."
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
        rule_key="contact_line_format",
        category="formatting",
        rule_text=CONTACT_LINE_RULE_TEXT,
        severity="error",
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        style_rules.delete().where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "contact_line_format",
            style_rules.c.Rule_Text == CONTACT_LINE_RULE_TEXT,
        )
    )
