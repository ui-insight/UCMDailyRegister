"""resolve editorial rule conflicts and authorize acronym expansions

Revision ID: c5e7a9b1d3f6
Revises: a7c9e1f3b5d2
Create Date: 2026-08-11 09:30:00.000000

The Aug. 10 rule batch left two contradictions the editor cannot resolve on
its own: the no-fabrication rule forbade supplying an acronym's full name even
though the acronym rule demands a first-reference definition, and the
composition-title rule ordered AP title case and quotation marks for works
that the event-title rules ordered preserved verbatim and unquoted. Amend the
four affected shared rules to state the authorization and the precedence
explicitly. The focused upserts preserve unrelated staff-managed rules.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "c5e7a9b1d3f6"
down_revision: str | Sequence[str] | None = "a7c9e1f3b5d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STYLE_RULE_UPDATES = [
    {
        "category": "content_filtering",
        "rule_key": "no_fabricated_content",
        "rule_text": "NEVER add information, facts, names, URLs, or references that are not present in the original submission, except approved canonical expansions or addresses supplied by an active style rule, or the standard full name of an acronym when the acronym rule requires a first-reference definition. When you supply an acronym's full name that is not in the submitted text, add a warning flag naming spell_out_acronyms so an editor can verify the expansion. Every remaining detail in the edited version must be traceable to the submitted text. Do not merge or cross-reference content from other submissions.",
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "composition_title_format",
        "rule_text": "Apply AP title capitalization to composition titles. Use single quotation marks in headlines and double quotation marks in body text for books, films, plays, poems, albums, songs, operas, programs, lectures, speeches and works of art. Do not quote holy books, reference works, software, apps, game titles or sculptures. Preserve consistent quotation and capitalization throughout the item. When an event is named for a composition — a film screening, play, reading, lecture or similar work — this rule governs the title's quotation marks and capitalization and takes precedence over event-title preservation and the ban on quoting event names in headlines.",
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "preserve_event_title_case",
        "rule_text": "Do not change event titles. Keep event titles in title case exactly as submitted, even when the surrounding text uses sentence case. This applies everywhere the name appears, including inside sentence-case headlines: official event, program and organization names are proper nouns, and preserving their official capitalization takes precedence over sentence-casing. Example: 'Fraternity and Sorority Life Bid Day' stays fully capitalized inside an otherwise sentence-case headline, never 'fraternity and sorority Bid Day'. Exception: when an event title is itself a composition title, such as a film, play or lecture title, format it under the composition-title rule instead.",
        "severity": "error",
    },
    {
        "category": "headlines",
        "rule_key": "no_event_name_quotes",
        "rule_text": "Do not put quotation marks around event names in headlines. Exception: when the headline names a composition such as a film, play or book, quote it per the composition-title rule.",
        "severity": "warning",
    },
]


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
    for rule in STYLE_RULE_UPDATES:
        values = {
            "Category": rule["category"],
            "Rule_Text": rule["rule_text"],
            "Is_Active": True,
            "Severity": rule["severity"],
        }
        result = bind.execute(
            style_rules.update()
            .where(
                style_rules.c.Rule_Set == "shared",
                style_rules.c.Rule_Key == rule["rule_key"],
            )
            .values(**values)
        )
        if result.rowcount == 0:
            bind.execute(
                style_rules.insert().values(
                    Id=str(uuid.uuid4()),
                    Rule_Set="shared",
                    Rule_Key=rule["rule_key"],
                    **values,
                )
            )


def upgrade() -> None:
    _apply_style_rule_updates(op.get_bind())


def downgrade() -> None:
    # Text-only updates of managed rules; prior wording is not restored.
    pass
