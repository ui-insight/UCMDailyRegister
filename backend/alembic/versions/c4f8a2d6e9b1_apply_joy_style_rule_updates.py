"""apply Joy style rule updates

Revision ID: c4f8a2d6e9b1
Revises: b8d4e6f1a2c3
Create Date: 2026-07-18 09:00:00.000000

Apply only the style-rule changes requested in feedback issue #194. This data
migration intentionally avoids ``SEED_OVERWRITE=1``, which would reset every
staff-managed style rule, allowed value and schedule configuration.

It also removes the obsolete My UI ``title_case`` row left behind when that
seed key was renamed to ``sentence_case``. Insert-only seeding correctly
preserves staff changes, but it cannot remove a stale row that conflicts with
the current sentence-case instruction.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4f8a2d6e9b1"
down_revision: str | Sequence[str] | None = "b8d4e6f1a2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STYLE_RULE_UPDATES = [
    {
        "rule_set": "shared",
        "category": "formatting",
        "rule_key": "ap_style_times",
        "rule_text": (
            "Use AP style for times: lowercase a.m. and p.m. with periods. Use noon "
            "and midnight instead of 12 p.m. and 12 a.m. Use figures: 1 p.m., 3:30 "
            "p.m. Use a hyphen for same-period time ranges: '3-4 p.m.' Use 'from' "
            "with 'to' only when spanning a.m. to p.m.: 'from 9 a.m. to 3 p.m.' "
            "Avoid 'o'clock'. Remove redundant time phrases such as 'this morning' "
            "or 'tonight'."
        ),
        "severity": "warning",
    },
    {
        "rule_set": "shared",
        "category": "formatting",
        "rule_key": "event_detail_ordering",
        "rule_text": (
            "Order event details as: time, day, date, location. Example: '3-4 p.m. "
            "Wednesday, Feb. 12, in the Pitman Center Vandal Ballroom'. Do not "
            "reorder or omit these elements. If the event is more than one month "
            "away, omit the day of the week."
        ),
        "severity": "warning",
    },
    {
        "rule_set": "shared",
        "category": "formatting",
        "rule_key": "spell_out_acronyms",
        "rule_text": (
            "Spell out acronyms on first reference and define key terms. Use the "
            "acronym in parentheses after the first spelled-out reference. Acronyms "
            "are allowed in headlines if the full term is spelled out on first "
            "reference in the body text."
        ),
        "severity": "warning",
    },
    {
        "rule_set": "shared",
        "category": "voice",
        "rule_key": "short_sentences",
        "rule_text": (
            "Write short, clear sentences. Avoid run-on sentences and "
            "compound-complex structures. Break long sentences into two or more "
            "shorter ones for readability. Replace semicolons with periods."
        ),
        "severity": "warning",
    },
    {
        "rule_set": "tdr",
        "category": "headlines",
        "rule_key": "sentence_case",
        "rule_text": (
            "Headlines must be sentence case: capitalize only the first word and "
            "proper nouns. Capitalize proper nouns, including official names of "
            "departments, offices, buildings and programs (e.g., Copy Print Center, "
            "Creative Services, Elizabeth Bradfield). Never leave proper names in "
            "lowercase. Example: 'Attend the research awards ceremony' not 'Attend "
            "the Research Awards Ceremony'."
        ),
        "severity": "error",
    },
    {
        "rule_set": "myui",
        "category": "headlines",
        "rule_key": "sentence_case",
        "rule_text": (
            "Headlines must be sentence case: capitalize only the first word and "
            "proper nouns. Capitalize proper nouns, including official names of "
            "departments, offices, buildings and programs (e.g., Copy Print Center, "
            "Creative Services, Elizabeth Bradfield). Never leave proper names in "
            "lowercase. Example: 'Register for spring break activities' not "
            "'Register for Spring Break Activities'."
        ),
        "severity": "error",
    },
    {
        "rule_set": "shared",
        "category": "formatting",
        "rule_key": "spell_out_state_names",
        "rule_text": (
            "Always spell out the name of a state. Example: 'Moscow, Idaho' not "
            "'Moscow, ID'."
        ),
        "severity": "warning",
    },
    {
        "rule_set": "shared",
        "category": "formatting",
        "rule_key": "ampersand_to_and",
        "rule_text": (
            "Replace '&' with 'and' in plain text. Keep '&' only when it is part of "
            "an official title or event name that uses it."
        ),
        "severity": "warning",
    },
    {
        "rule_set": "shared",
        "category": "formatting",
        "rule_key": "preserve_event_title_case",
        "rule_text": (
            "Do not change event titles. Keep event titles in title case exactly as "
            "submitted, even when the surrounding text uses sentence case."
        ),
        "severity": "error",
    },
    {
        "rule_set": "shared",
        "category": "formatting",
        "rule_key": "mountain_time_not_mdt",
        "rule_text": (
            "If the submission includes 'Mountain time', retain it exactly as "
            "written. If 'MDT' or 'MST' appears, replace it with 'Mountain time'. "
            "Do not omit, rephrase or alter this wording."
        ),
        "severity": "warning",
    },
    {
        "rule_set": "shared",
        "category": "formatting",
        "rule_key": "directional_abbreviation_periods",
        "rule_text": (
            "When an address includes a directional abbreviation (N, S, E or W), "
            "add a period after the letter. Example: '1000 W. Pullman Road'. Do not "
            "leave directional abbreviations without a period."
        ),
        "severity": "warning",
    },
    {
        "rule_set": "shared",
        "category": "voice",
        "rule_key": "cta_structure",
        "rule_text": (
            "Structure announcements around a clear call to action: open with the "
            "action the reader should take, follow with context, dates and "
            "incentives, and close with an explicit final call to action such as "
            "'Learn more and register'. Replace vague instructions with explicit "
            "actions. Do not introduce audience qualifiers that are not in the "
            "original submission. When the submission provides a contact's full "
            "name, use it rather than a bare email address."
        ),
        "severity": "warning",
    },
]


PREVIOUS_RULE_TEXT = {
    ("shared", "ap_style_times"): (
        "Use AP style for times: lowercase a.m. and p.m. with periods. Use noon "
        "and midnight instead of 12 p.m. and 12 a.m. Use figures: 1 p.m., 3:30 "
        "p.m. Use a hyphen for same-period time ranges: '3-4 p.m.' Use 'from' "
        "with 'to' only when spanning a.m. to p.m.: 'from 9 a.m. to 3 p.m.'"
    ),
    ("shared", "event_detail_ordering"): (
        "Order event details as: time, day, date, location. Example: '3-4 p.m. "
        "Wednesday, Feb. 12, in the Pitman Center Vandal Ballroom'."
    ),
    ("shared", "spell_out_acronyms"): (
        "Spell out acronyms on first reference and define key terms. Use the "
        "acronym in parentheses after the first spelled-out reference."
    ),
    ("shared", "short_sentences"): (
        "Write short, clear sentences. Avoid run-on sentences and "
        "compound-complex structures. Break long sentences into two or more "
        "shorter ones for readability."
    ),
    ("tdr", "sentence_case"): (
        "Headlines must be sentence case (capitalize only the first word and "
        "proper nouns). Example: 'Attend the research awards ceremony' not "
        "'Attend the Research Awards Ceremony'."
    ),
    ("myui", "sentence_case"): (
        "Headlines must be sentence case (capitalize only the first word and "
        "proper nouns). Example: 'Register for spring break activities' not "
        "'Register for Spring Break Activities'."
    ),
}


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


def _apply_style_rule_updates(bind: sa.Connection) -> None:
    """Apply the focused rule upserts; exposed separately for regression tests."""
    bind.execute(
        sa.delete(style_rules).where(
            style_rules.c.Rule_Set == "myui",
            style_rules.c.Rule_Key == "title_case",
        )
    )

    for rule in STYLE_RULE_UPDATES:
        values = {
            "Category": rule["category"],
            "Rule_Text": rule["rule_text"],
            "Is_Active": True,
            "Severity": rule["severity"],
        }
        result = bind.execute(
            sa.update(style_rules)
            .where(
                style_rules.c.Rule_Set == rule["rule_set"],
                style_rules.c.Rule_Key == rule["rule_key"],
            )
            .values(**values)
        )
        if result.rowcount == 0:
            bind.execute(
                sa.insert(style_rules).values(
                    Id=str(uuid.uuid4()),
                    Rule_Set=rule["rule_set"],
                    Rule_Key=rule["rule_key"],
                    **values,
                )
            )


def upgrade() -> None:
    _apply_style_rule_updates(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    for rule in STYLE_RULE_UPDATES:
        key = (rule["rule_set"], rule["rule_key"])
        previous_text = PREVIOUS_RULE_TEXT.get(key)
        if previous_text is None:
            bind.execute(
                sa.delete(style_rules).where(
                    style_rules.c.Rule_Set == rule["rule_set"],
                    style_rules.c.Rule_Key == rule["rule_key"],
                )
            )
            continue

        bind.execute(
            sa.update(style_rules)
            .where(
                style_rules.c.Rule_Set == rule["rule_set"],
                style_rules.c.Rule_Key == rule["rule_key"],
            )
            .values(Rule_Text=previous_text)
        )

    # Do not recreate myui/title_case: it was obsolete production drift, not
    # intentional pre-migration state.
