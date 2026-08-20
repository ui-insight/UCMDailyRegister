"""align managed editorial rules with Aug. 20 production feedback

Revision ID: c7e9a1b3d5f2
Revises: b5d7f9a1c3e4
Create Date: 2026-08-20 14:00:00.000000

Joy's production review clarified that newsletter audience metadata must not
enter the copy, ampersands are replaced even in official names, cross-period
time ranges use ``to``, event details begin with the time, and relative dates
must retain their explicit calendar dates. This focused upsert aligns existing
databases with the shared seed while leaving unrelated staff-managed rules
untouched.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "c7e9a1b3d5f2"
down_revision: str | Sequence[str] | None = "b5d7f9a1c3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STYLE_RULE_UPDATES = [
    {
        "category": "formatting",
        "rule_key": "today_tomorrow",
        "rule_text": (
            "When a source pairs a relative date such as 'today' or 'tomorrow' "
            "with a specific calendar date, retain both in the edited copy. "
            "Never replace or remove the calendar date. Write the relative "
            "reference followed by the date, such as 'today, Aug. 24,' so the "
            "item remains accurate after publication."
        ),
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "ap_style_times",
        "rule_text": (
            "Use AP style for times: lowercase a.m. and p.m. with periods. Use "
            "noon and midnight instead of 12 p.m. and 12 a.m. Use figures: 1 "
            "p.m., 3:30 p.m. Use a hyphen for same-period time ranges: '3-4 "
            "p.m.' Use 'to' instead of a hyphen when a range crosses a.m. and "
            "p.m.: '11 a.m. to 2 p.m.' Use 'from' only when the sentence "
            "grammar requires a from/to construction. Avoid 'o'clock'. Remove "
            "redundant time phrases such as 'this morning' or 'tonight'."
        ),
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "event_detail_ordering",
        "rule_text": (
            "Start event-detail constructions with the time, then give the day, "
            "date and location in that order. Example: '3-4 p.m. Wednesday, Feb. "
            "12, in the Pitman Center Vandal Ballroom.' Never place the day or "
            "date before the time. Do not omit these elements. If the event is "
            "more than one month away, omit the day of the week."
        ),
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "ampersand_to_and",
        "rule_text": (
            "Replace '&' with 'and' everywhere in published plain text, including "
            "official names, titles, departments, programs and event names, "
            "except Q&A. HTML entities used by markup are not editorial ampersands."
        ),
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "preserve_event_title_case",
        "rule_text": (
            "Do not change the wording or capitalization of event titles. Keep "
            "event titles in title case exactly as submitted, even when the "
            "surrounding text uses sentence case. This applies everywhere the "
            "name appears, including inside sentence-case headlines: official "
            "event, program and organization names are proper nouns, and "
            "preserving their official capitalization takes precedence over "
            "sentence-casing. Example: 'Fraternity and Sorority Life Bid Day' "
            "stays fully capitalized inside an otherwise sentence-case headline, "
            "never 'fraternity and sorority Bid Day'. The ampersand rule is the "
            "sole wording exception: replace '&' with 'and' while preserving all "
            "other title wording and capitalization. When an event title is "
            "itself a composition title, such as a film, play or lecture title, "
            "format it under the composition-title rule instead."
        ),
        "severity": "error",
    },
    {
        "category": "content_filtering",
        "rule_key": "preserve_audience_scope",
        "rule_text": (
            "Do not narrow, broaden or genericize the intended audience, and "
            "never invent it. "
            "Newsletter channel context such as TDR faculty and staff or My UI "
            "students is distribution metadata, never source content, so do not "
            "add an audience group from the selected newsletter. A submission "
            "sent to both newsletters must remain audience-neutral unless its "
            "source explicitly names a group. Preserve broad audience meaning "
            "such as 'all are welcome,' 'everyone is invited' or 'the public is "
            "welcome.' Also preserve the most specific accurate source "
            "description, such as donors, breastfeeding or lactating women, "
            "volunteers, faculty members, first-year students or alumni, instead "
            "of replacing it with 'participants,' 'individuals' or 'people.' For "
            "recruitment announcements, include the specific group in the first "
            "sentence whenever possible and surface important eligibility "
            "qualifiers early enough that the offer is not misleading. For "
            "concise event invitations, replace broad wording with a direct "
            "invitation such as 'Attend the workshop,' never with a narrower "
            "group unless the original explicitly limits attendance."
        ),
        "severity": "error",
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


def _apply_style_rule_updates(connection: sa.Connection) -> None:
    for rule in STYLE_RULE_UPDATES:
        values = {
            "Category": rule["category"],
            "Rule_Text": rule["rule_text"],
            "Is_Active": True,
            "Severity": rule["severity"],
        }
        result = connection.execute(
            style_rules.update()
            .where(
                style_rules.c.Rule_Set == "shared",
                style_rules.c.Rule_Key == rule["rule_key"],
            )
            .values(**values)
        )
        if result.rowcount == 0:
            connection.execute(
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
