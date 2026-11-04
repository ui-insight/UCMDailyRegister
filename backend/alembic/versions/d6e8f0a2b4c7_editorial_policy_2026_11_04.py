"""apply UCM editorial policy version 2026-11-04

Revision ID: d6e8f0a2b4c7
Revises: a1c3e5b7d9f2
Create Date: 2026-11-04 15:00:00.000000

Apply the editorial decisions Joy recorded on Nov. 1, 2026 (#409): when the
AI may reword (#396), protected names (#396), item sentence order and long
outside quotes (#373), the five headline rules (#376), curly quotes, direct
action wording, adverb placement, nearby repetition, and one flag format.
Idempotent upserts by rule key; staff-added rules are untouched.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "d6e8f0a2b4c7"
down_revision: str | Sequence[str] | None = "a1c3e5b7d9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (rule_set, rule_key, category, rule_text, severity)
MANAGED_RULES: list[tuple[str, str, str, str, str]] = [
    (
        "shared",
        "composition_title_format",
        "formatting",
        (
            "Apply AP title capitalization to composition titles. Use single "
            "quotation marks in headlines and double quotation marks in body "
            "text for books, films, plays, poems, albums, songs, operas, "
            "programs, lectures, speeches and works of art. Do not quote holy "
            "books, reference works, software, apps, game titles or sculptures."
            " Preserve consistent quotation and capitalization throughout the "
            "item. When an event is named for a composition — a film screening,"
            " play, reading, lecture or similar work — this rule governs the "
            "title's quotation marks and capitalization and takes precedence "
            "over event-title preservation and the ban on quoting event names "
            "in headlines. Titles of classes, guides, articles and podcasts are"
            " the exception: add the quotation marks but keep the submitted "
            "words and capitalization."
        ),
        "error",
    ),
    (
        "shared",
        "conservative_rewording",
        "voice",
        (
            "Tighten wording only when it makes the item clearer and the "
            "meaning stays exactly the same. Do not rewrite a sentence that is "
            "already clear and concise just because another phrasing is "
            "possible; leave it as submitted apart from changes another active "
            "rule requires. Correct obvious spelling, capitalization and "
            "typographical errors, except inside protected names. Concise "
            "possessives and similar tightening fall under this rule, not "
            "separate requirements."
        ),
        "error",
    ),
    (
        "shared",
        "protected_names",
        "terminology",
        (
            "Keep these exactly as submitted, with no expanding, shortening, "
            "recapitalizing or correcting: website, platform and product names;"
            " event names, including any acronyms inside them; names of people,"
            " including spelling and middle initials; and titles of classes, "
            "guides, articles and podcasts. Titles of classes, guides, articles"
            " and podcasts still take the quotation marks the composition-title"
            " rule requires, but their words and capitalization stay as "
            "submitted. Replacing '&' with 'and' under the ampersand rule is "
            "the only wording exception. When a platform name only says how to "
            "attend, such as 'on Zoom', follow the online rule; a platform that"
            " is the subject, such as a Teams training, stays as submitted. If "
            "a protected name looks misspelled or appears in more than one "
            "form, use the most complete submitted form and add a warning flag "
            "whose message is '[NAME VARIES IN SUBMISSION: CONFIRM OFFICIAL "
            "NAME]'. Venues, buildings and organizations: when a submitted name"
            " matches a canonical form supplied by an active rule, use that "
            "form; otherwise keep the submitted name. Never create a new "
            "capitalized venue name, and never add words such as 'Office', "
            "'Department' or 'Center' to an organization's name. If a venue is "
            "unclear, keep it as submitted and add a warning flag whose message"
            " is '[CONFIRM VENUE NAME]'."
        ),
        "error",
    ),
    (
        "shared",
        "item_sentence_order",
        "formatting",
        (
            "Default sentence order for event items: 1. who, what, time, day, "
            "date and place; 2. brief background with one credential; 3. the "
            "main call to action; 4. secondary events. When that order makes a "
            "sentence awkward, a natural sentence wins within these limits: "
            "event details stay in the first or second sentence; an overloaded "
            "opening splits into two complete sentences; background may move "
            "later or be cut but never comes before the event details; the call"
            " to action may move up, for example when the item is mainly about "
            "registering, as long as the event details stay near the top. For "
            "notices that are not events, such as closures, deadline changes "
            "and other updates, lead with the current facts, then mention the "
            "earlier plan only if needed, then the call to action. The time, "
            "day, date and place order inside the event details never changes."
        ),
        "error",
    ),
    (
        "shared",
        "trim_outside_quotes",
        "content_filtering",
        (
            "Trim a long quotation from an outside source to the part that "
            "supports the item, unless the submitter notes ask to keep it. "
            "Trimming must not remove facts, deadlines, requirements or the "
            "action readers should take. Do not flag a quotation you trimmed."
        ),
        "warning",
    ),
    (
        "shared",
        "headline_rules",
        "headlines",
        (
            "Every headline follows these rules. 1. Ask readers to act: start "
            "with a verb naming the specific action tied to the main call to "
            "action. 'Buy tickets', 'Register' and 'Submit' beat vague verbs "
            "such as 'Attend' when a more specific action applies. 2. Write a "
            "complete phrase, with articles and connecting words: 'Get tickets "
            "to see the Example Quartet in concert', not 'Attend Example "
            "Quartet performance'. 3. Do not begin the headline with the same "
            "wording as the first sentence of the body; it may mention the same"
            " event, name or date. 4. Use sentence case. 5. Never use "
            "exclamation marks."
        ),
        "error",
    ),
    (
        "shared",
        "curly_quotes",
        "formatting",
        (
            "Use curly quotation marks and apostrophes (‘ ’ “ ”) in headlines "
            "and body text. Never convert curly marks to straight ones, and "
            "convert straight marks from the submission to curly ones. Leave "
            "URLs and HTML attributes unchanged."
        ),
        "error",
    ),
    (
        "shared",
        "direct_action_wording",
        "voice",
        (
            "Write calls to action in the active voice, addressed to the "
            "reader: 'Register by Friday', not 'Registration should be "
            "completed by Friday'. Use 'can', not 'may', for what readers are "
            "able to do: 'Employees can enroll online', not 'Employees may "
            "enroll online'. Keep 'may' only where it means permission or "
            "possibility."
        ),
        "error",
    ),
    (
        "shared",
        "adverb_placement",
        "voice",
        (
            "With a compound verb, place the adverb before the helping verb, "
            "following AP style ('also will give', not 'will also give'), "
            "unless that changes the meaning or reads awkwardly."
        ),
        "warning",
    ),
    (
        "shared",
        "avoid_nearby_repetition",
        "voice",
        (
            "Do not repeat a distinctive word or phrase in nearby sentences. "
            "Repeating names, places and basic terms is fine when clarity "
            "requires it."
        ),
        "warning",
    ),
    (
        "shared",
        "review_flags",
        "content_filtering",
        (
            "Never put review notes, bracketed flags or questions for staff in "
            "the headline or body. Report each one in the flags list instead, "
            "with the bracketed note as the flag message, for example '[CONFIRM"
            " VENUE NAME]' or '[DATE CONFLICT: MARCH 3, 2027, IS A WEDNESDAY, "
            "NOT A TUESDAY]'. Keep the source wording in the copy where the "
            "note applies."
        ),
        "error",
    ),
    (
        "shared",
        "headline_distinct_from_lead",
        "headlines",
        (
            "The headline must not begin with the same wording as the first "
            "sentence of the body. It may mention the same event, name or date,"
            " and it may describe the same action in other words. Example: for "
            "a body opening 'The Example Center will hold its pottery sale 10 "
            "a.m. to 4 p.m. Saturday, Dec. 5, in the Example Hall.', write 'Buy"
            " handmade pottery at the Example Center sale', not 'The Example "
            "Center will hold its pottery sale'."
        ),
        "warning",
    ),
    (
        "shared",
        "no_exclamation_marks",
        "voice",
        (
            "Never use exclamation marks in headlines. Avoid them in body text."
            " Use a professional, neutral tone."
        ),
        "error",
    ),
    (
        "shared",
        "headline_reader_perspective",
        "headlines",
        (
            "Headlines must be written from the reader's perspective using "
            "verbs that accurately reflect the action the original submission "
            "asks readers to take. Preserve the primary action, purpose and "
            "intent; never substitute a different activity or transaction. When"
            " an author reads from a book, invite readers to hear the reading, "
            "not read or purchase the book. Correct: 'Hear Elizabeth Bradfield "
            "read from SOFAR'. Incorrect: 'Read Elizabeth Bradfield's poetry "
            "collection SOFAR' and 'Purchase Elizabeth Bradfield's poetry "
            "collection'. Likewise, write 'Participate in a VR research study',"
            " not 'Recruit research participants'."
        ),
        "error",
    ),
    (
        "shared",
        "promotional_action_benefit_lead",
        "voice",
        (
            "Promotional announcements must lead with the action readers should"
            " take and the benefit they can receive. Put important qualifying "
            "details early when they define the offer. Avoid passive, circular "
            "or redundant introductions such as 'The last week to have a permit"
            " reimbursed is this week.' Prefer 'This is the final week to "
            "enroll in a qualifying meal plan for a chance to have a commuter "
            "parking permit reimbursed in full.' Remove audience references "
            "that do not affect eligibility. Consolidate repeated actions into "
            "one descriptive linked call to action and shorten supporting "
            "wording rather than repeating the offer. For event items, the item"
            " sentence order rule decides where the call to action goes, and "
            "headlines follow the headline rules."
        ),
        "error",
    ),
    (
        "tdr",
        "sentence_case",
        "headlines",
        (
            "Headlines must be sentence case: capitalize only the first word "
            "and proper nouns. Capitalize proper nouns, including official "
            "names of departments, offices, buildings and programs (e.g., Copy "
            "Print Center, Creative Services, Elizabeth Bradfield). Official "
            "event, program and organization names also count as proper nouns "
            "and keep their official capitalization inside a sentence-case "
            "headline (e.g., 'Celebrate Fraternity and Sorority Life Bid Day on"
            " Friday'). Never leave proper names in lowercase. Example: "
            "'Register for the research awards luncheon' not 'Register for the "
            "Research Awards Luncheon'."
        ),
        "error",
    ),
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
