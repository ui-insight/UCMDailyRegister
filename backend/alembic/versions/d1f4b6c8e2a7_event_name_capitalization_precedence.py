"""make official event names survive sentence-case headlines

Revision ID: d1f4b6c8e2a7
Revises: c7d9a1b3e5f8
Create Date: 2026-08-07 14:00:00.000000

Joy reported official event names being lowercased, most visibly in
headlines where the sentence-case rule pushes toward lowercase. State
the precedence explicitly in both directions: official event, program
and organization names are proper nouns that keep their official
capitalization everywhere, including inside sentence-case headlines.
Idempotent; touches only the three managed rule keys.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "d1f4b6c8e2a7"
down_revision: str | Sequence[str] | None = "c7d9a1b3e5f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PRESERVE_EVENT_TITLE_RULE_TEXT = (
    "Do not change event titles. Keep event titles in title case exactly "
    "as submitted, even when the surrounding text uses sentence case. "
    "This applies everywhere the name appears, including inside "
    "sentence-case headlines: official event, program and organization "
    "names are proper nouns, and preserving their official capitalization "
    "takes precedence over sentence-casing. Example: 'Fraternity and "
    "Sorority Life Bid Day' stays fully capitalized inside an otherwise "
    "sentence-case headline, never 'fraternity and sorority Bid Day'."
)

TDR_SENTENCE_CASE_RULE_TEXT = (
    "Headlines must be sentence case: capitalize only the first word and "
    "proper nouns. Capitalize proper nouns, including official names of "
    "departments, offices, buildings and programs (e.g., Copy Print "
    "Center, Creative Services, Elizabeth Bradfield). Official event, "
    "program and organization names also count as proper nouns and keep "
    "their official capitalization inside a sentence-case headline (e.g., "
    "'Celebrate Fraternity and Sorority Life Bid Day on Friday'). Never "
    "leave proper names in lowercase. Example: 'Attend the research "
    "awards ceremony' not 'Attend the Research Awards Ceremony'."
)

MYUI_SENTENCE_CASE_RULE_TEXT = (
    "Headlines must be sentence case: capitalize only the first word and "
    "proper nouns. Capitalize proper nouns, including official names of "
    "departments, offices, buildings and programs (e.g., Copy Print "
    "Center, Creative Services, Elizabeth Bradfield). Official event, "
    "program and organization names also count as proper nouns and keep "
    "their official capitalization inside a sentence-case headline (e.g., "
    "'Celebrate Fraternity and Sorority Life Bid Day on Friday'). Never "
    "leave proper names in lowercase. Example: 'Register for spring break "
    "activities' not 'Register for Spring Break Activities'."
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
        rule_key="preserve_event_title_case",
        category="formatting",
        rule_text=PRESERVE_EVENT_TITLE_RULE_TEXT,
        severity="error",
    )
    _upsert_rule(
        connection,
        rule_set="tdr",
        rule_key="sentence_case",
        category="headlines",
        rule_text=TDR_SENTENCE_CASE_RULE_TEXT,
        severity="error",
    )
    _upsert_rule(
        connection,
        rule_set="myui",
        rule_key="sentence_case",
        category="headlines",
        rule_text=MYUI_SENTENCE_CASE_RULE_TEXT,
        severity="error",
    )


def downgrade() -> None:
    # Text-only revision of managed rules; the prior wording is not
    # restored on downgrade.
    pass
