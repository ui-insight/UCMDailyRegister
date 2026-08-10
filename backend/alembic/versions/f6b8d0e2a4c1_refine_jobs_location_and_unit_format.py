"""refine Jobs location and official-unit formatting

Revision ID: f6b8d0e2a4c1
Revises: f2c6a8b4d1e3
Create Date: 2026-08-10 13:30:00.000000

Joy confirmed that the single-line Jobs rule still included Moscow, retained
the IMCI acronym and lowercased an official unit name. Update the managed TDR
rule while preserving the rest of the one-line/no-news-item contract.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "f6b8d0e2a4c1"
down_revision: str | Sequence[str] | None = "f2c6a8b4d1e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JOB_POSTING_RULE_TEXT = (
    "Job postings are linked to PeopleAdmin listings. Must be listed with "
    "Human Resources. Posted for two weeks, newest at top. Format every "
    "Jobs-category submission as a single-line listing, not a news item: "
    "job title, department or unit, location only when outside Moscow. Use "
    "sentence case for the job title: capitalize only the first word, "
    "required classifications or levels (such as III or IV), acronyms and "
    "proper nouns. Preserve the official capitalization of units, "
    "departments, programs, colleges, centers and institutes. Replace IMCI "
    "with Institute for Modeling Collaboration and Innovation. Omit Moscow "
    "when it is supplied as the location; if no location is supplied, assume "
    "Moscow and omit the location. Include a location only when it is outside "
    "Moscow. Example: 'Laboratory manager, Image and Data Acquisition Core, "
    "Institute for Modeling Collaboration and Innovation'. Do not write a "
    "headline, a descriptive paragraph, promotional language such as 'apply "
    "now', instructions directing readers to apply, or an application "
    "deadline unless one is specifically requested. Keep the entire entry on "
    "one line and preserve the hyperlink to the listing."
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
    _upsert_rule(
        op.get_bind(),
        rule_set="tdr",
        rule_key="job_posting_format",
        category="formatting",
        rule_text=JOB_POSTING_RULE_TEXT,
        severity="error",
    )


def downgrade() -> None:
    # Text-only revision of a managed rule; prior wording is not restored.
    pass
