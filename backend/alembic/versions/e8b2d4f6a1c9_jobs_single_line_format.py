"""format job submissions as single-line listings

Revision ID: e8b2d4f6a1c9
Revises: d1f4b6c8e2a7
Create Date: 2026-08-07 14:00:00.000000

Joy reported Jobs submissions being formatted as news items with a
headline, summary paragraph and apply language. Extend the TDR
job_posting_format rule (keeping its policy content) with the required
output format: one line of job title (sentence case), department or
unit, and location. Raise severity to error since this is a hard
format requirement. Idempotent; touches only the managed rule key.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "e8b2d4f6a1c9"
down_revision: str | Sequence[str] | None = "d1f4b6c8e2a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JOB_POSTING_RULE_TEXT = (
    "Job postings are linked to PeopleAdmin listings. Must be listed with "
    "Human Resources. Posted for two weeks, newest at top. Format every "
    "Jobs-category submission as a single-line listing, not a news item: "
    "job title (sentence case: capitalize only the first word and proper "
    "nouns), department or unit, location — e.g. 'Administrative "
    "specialist III, College of Engineering, Moscow'. Do not write a "
    "headline, a descriptive paragraph, promotional language such as "
    "'apply now', instructions directing readers to apply, or an "
    "application deadline unless one is specifically requested. Keep the "
    "entire entry on one line and preserve the hyperlink to the listing."
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
        rule_set="tdr",
        rule_key="job_posting_format",
        category="formatting",
        rule_text=JOB_POSTING_RULE_TEXT,
        severity="error",
    )


def downgrade() -> None:
    # Text-only revision of managed rules; the prior wording is not
    # restored on downgrade.
    pass
