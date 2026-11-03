"""apply acronym order of checks

Revision ID: b2d4f6a8c0e3
Revises: c3e5a7b9d1f4
Create Date: 2026-11-03 12:00:00.000000

Apply UCM's Nov. 2026 acronym decision (#381, #399): official names stay as
submitted, the never-spell-out lists stand alone, widely known acronyms follow
AP style, and every other acronym is spelled out with a parenthetical only when
it is used again. Idempotent; touches only the two managed acronym rule keys.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "b2d4f6a8c0e3"
down_revision: str | Sequence[str] | None = "c3e5a7b9d1f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SHARED_ACRONYM_RULE_TEXT = (
    "Apply these acronym checks in order. 1. Inside an official name: an "
    "acronym that is part of an official event, program, product, website "
    "or organization name stays exactly as submitted, with no expansion and"
    " no parenthetical. 2. Never-spell-out list: IMCI, IRIC, COBRE, INBRE, "
    "EPSCoR and ISUB always stand alone, even on first reference, with no "
    "expansion and no parenthetical. 3. Widely known acronyms: following AP"
    " style, use acronyms such as AI, GPS, FBI and NASA without spelling "
    "them out. U of I is also exempt. 4. Everything else: spell out the "
    "full name on first reference in the body. Add the acronym in "
    "parentheses after the full name only when the acronym appears again "
    "later in the body or in the headline, then use only the acronym. If "
    "the acronym is not used again, write the full name alone and leave the"
    " acronym out. No acronym may appear before that definition, except "
    "under checks 1 through 3. An acronym may appear in a headline only "
    "when the body defines it on first reference or it passes check 1, 2 or"
    " 3. When unsure whether an acronym is widely known, spell it out on "
    "first reference."
)

MYUI_ACRONYM_RULE_TEXT = (
    "In My UI, CALS, CAA, ICCU and LHSOM also stand alone, even on first "
    "reference, with no expansion and no parenthetical. Student readers may"
    " not know other university department or program abbreviations, so "
    "spell out every other acronym according to spell_out_acronyms."
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

MANAGED_RULES = (
    ("shared", "spell_out_acronyms", "formatting", SHARED_ACRONYM_RULE_TEXT, "error"),
    ("myui", "flag_unclear_acronyms", "content_filtering", MYUI_ACRONYM_RULE_TEXT, "warning"),
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
    for rule_set, rule_key, category, rule_text, severity in MANAGED_RULES:
        _upsert_rule(
            connection,
            rule_set=rule_set,
            rule_key=rule_key,
            category=category,
            rule_text=rule_text,
            severity=severity,
        )


def downgrade() -> None:
    # Text-only revision of managed rules; the prior wording is not
    # restored on downgrade.
    pass
