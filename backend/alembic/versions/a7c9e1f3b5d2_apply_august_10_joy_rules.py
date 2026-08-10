"""apply Aug. 10 Joy editorial rules

Revision ID: a7c9e1f3b5d2
Revises: f6b8d0e2a4c1
Create Date: 2026-08-10 13:45:00.000000

Strengthen rules that the production editor ignored and add the missing
audience, CTA, title, location and context contracts from feedback issue #300.
The focused upserts preserve unrelated staff-managed rules.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "a7c9e1f3b5d2"
down_revision: str | Sequence[str] | None = "f6b8d0e2a4c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STYLE_RULE_UPDATES = [
    {
        "category": "formatting",
        "rule_key": "ap_style_dates",
        "rule_text": "Use AP style for dates. Abbreviate Jan., Feb., Aug., Sept., Oct., Nov. and Dec. only when used with a specific date. Never abbreviate March, April, May, June or July. When a month appears without a specific date, spell out the full month name. Use numerals for dates (Jan. 5, not January fifth). When a month-and-day date appears mid-sentence, place a comma after the date if the sentence continues: 'The conference runs Monday, Oct. 31, and Tuesday, Nov. 1.' Apply the comma to every date in a range or sequence.",
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "ap_style_times",
        "rule_text": "Use AP style for times: lowercase a.m. and p.m. with periods. Use noon and midnight instead of 12 p.m. and 12 a.m. Use figures: 1 p.m., 3:30 p.m. Use a hyphen for same-period time ranges: '3-4 p.m.' Use 'from' with 'to' only when spanning a.m. to p.m.: 'from 9 a.m. to 3 p.m.' Avoid 'o'clock'. Remove redundant time phrases such as 'this morning' or 'tonight'.",
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "spell_out_acronyms",
        "rule_text": "Define every nonstandard acronym on first reference in the body as Full Name (ACRONYM), then use only the acronym on subsequent references. No acronym may appear before that definition. An acronym may appear in a headline only when the body defines it on first reference. Do not repeatedly use the full name after the acronym is established unless clarity requires it. Widely recognized terms such as U of I are exempt.",
        "severity": "error",
    },
    {
        "category": "content_filtering",
        "rule_key": "no_fabricated_content",
        "rule_text": "NEVER add information, facts, names, URLs, or references that are not present in the original submission, except approved canonical expansions or addresses supplied by an active style rule. Every other detail in the edited version must be traceable to the submitted text. Do not merge or cross-reference content from other submissions.",
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "online_not_platform",
        "rule_text": "Use the word 'online' instead of platform names like 'Zoom', 'Teams', or 'Webex' when describing virtual attendance options, unless the platform name is essential (e.g., a Teams-specific training).",
        "severity": "error",
    },
    {
        "category": "voice",
        "rule_key": "cta_structure",
        "rule_text": "Structure announcements around one clear call to action and supporting context. Replace vague instructions with an explicit action, but do not repeat that action elsewhere in the item. Edit user-supplied linked text when needed for clarity, concision and editorial style; linked text is not immutable. Do not introduce audience qualifiers that are not in the original submission. When the submission provides a contact's full name, use it rather than a bare email address. Never build a call to action on filler words such as 'here' or 'click here'. Link the action verb or object: 'Sign up', 'Register for the workshop' or 'Apply for the scholarship'.",
        "severity": "error",
    },
    {
        "category": "voice",
        "rule_key": "single_cta",
        "rule_text": "Each call to action must appear only once. Do not repeat action verbs or equivalent CTA phrases before or after a link. If one CTA accomplishes the goal, do not add another with the same meaning.",
        "severity": "error",
    },
    {
        "category": "content_filtering",
        "rule_key": "preserve_audience_scope",
        "rule_text": "Do not narrow the intended audience. Preserve broad audience meaning such as 'all are welcome,' 'everyone is invited' or 'the public is welcome.' For concise event invitations, replace that wording with a direct invitation such as 'Attend the workshop,' never with a narrower group such as employees, students, faculty, staff or campus community unless the original explicitly limits attendance.",
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "composition_title_format",
        "rule_text": "Apply AP title capitalization to composition titles. Use single quotation marks in headlines and double quotation marks in body text for books, films, plays, poems, albums, songs, operas, programs, lectures, speeches and works of art. Do not quote holy books, reference works, software, apps, game titles or sculptures. Preserve consistent quotation and capitalization throughout the item.",
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "building_room_order",
        "rule_text": "For on-campus locations, place the building name first, followed by the room or venue with no comma between them. Never format a location as Room, Building. Examples: ISUB Reflections Gallery, Bruce M. Pitman Center International Ballroom and IRIC 352.",
        "severity": "error",
    },
    {
        "category": "formatting",
        "rule_key": "approved_off_campus_addresses",
        "rule_text": "When an approved off-campus venue appears, append its canonical address exactly: Kenworthy Performing Arts Centre, 508 S. Main St.; 1912 Center, 412 E. Third St.; One World Cafe, 840 W. Seventh St.; Hunga Dunga Brewing Co., 333 N. Jackson St.; Moscow Public Library, 110 S. Jefferson St.; Palouse-Clearwater Environmental Institute, 1040 Rodeo Drive; Best Western Plus University Inn, 1516 W. Pullman Road; East City Park, 900 E. Third St. Add addresses only for venues on this list.",
        "severity": "error",
    },
    {
        "category": "content_filtering",
        "rule_key": "preserve_purpose_contact_titles",
        "rule_text": "Preserve the purpose, value and context that explain why an event, service or opportunity is offered. Preserve contact information and official contact titles. Capitalize a title immediately before a person's name; lowercase a title after a name or when it stands alone. Shorten wording, not meaning.",
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
