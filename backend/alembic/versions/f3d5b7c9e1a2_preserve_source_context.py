"""preserve organizational and participant source context

Revision ID: f3d5b7c9e1a2
Revises: e2c4a6b8d0f1
Create Date: 2026-08-18 11:30:00.000000

Joy's source-fidelity feedback clarified six forms of meaning that must take
precedence over concision. This focused upsert adds organizational and
information-option rules and strengthens the existing requirement, participant
context and contact-title rules without replacing unrelated staff-managed data.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "f3d5b7c9e1a2"
down_revision: str | Sequence[str] | None = "e2c4a6b8d0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PRESERVE_REQUIREMENTS_RULE_TEXT = (
    "Preserve every deadline, actionable date and mandatory requirement from the "
    "original submission: registration, application, abstract, proposal, nomination "
    "and submission deadlines; event dates and times; application periods; eligibility, "
    "age and enrollment conditions; regulatory requirements; and required licenses or "
    "certifications. Keep mandatory language mandatory and never shorten a requirement "
    "until it appears optional or less important. Keep multiple deadlines when they "
    "serve different purposes. Never replace a specific deadline with a generic call to "
    "action such as 'Learn more and register'. When editing for conciseness, shorten the "
    "surrounding prose instead of removing deadlines or requirements. Example: "
    "'Registration closes Oct. 23. Abstract submissions are due Oct. 16. Applicants "
    "must be TIPS certified. Learn more and register.' is correct; dropping any deadline "
    "or requirement is not."
)
PRESERVE_ORGANIZATIONAL_CONTEXT_RULE_TEXT = (
    "Preserve the specific organization that grants, administers or oversees an award, "
    "ranking, rating, certification, accreditation, recognition or designation. Also "
    "preserve the university program, office, department or initiative that offers, "
    "sponsors or administers an opportunity, service, event, grant, program or activity. "
    "When that entity is central to understanding the opportunity, name it early in the "
    "body; retaining it only in the headline is not sufficient. Shorten surrounding "
    "wording, not the identity or role of the awarding or sponsoring entity. Example: "
    "keep 'Association for Advancement in Sustainability in Higher Education STARS "
    "Gold-rated university,' not only 'STARS Gold-rated university,' and keep 'raise "
    "funds through Idaho Eats,' not only 'raise funds.'"
)
PRESERVE_INFORMATION_OPTIONS_RULE_TEXT = (
    "Preserve every distinct action and information-seeking option offered by the source. "
    "If readers may sign up or learn more, retain both options; do not narrow a general "
    "invitation to contact or reach out into registration-only language unless "
    "registration is the source's sole purpose. A request for more information is not a "
    "duplicate call to action and takes precedence over the single-CTA rule. Shorten "
    "surrounding wording instead of deleting the information path."
)
PRESERVE_PARTICIPANT_CONTEXT_RULE_TEXT = (
    "When condensing, distinguish unnecessary repetition from meaningful context. "
    "Preserve participant responsibilities and operational details explaining what "
    "volunteers, attendees or other participants will actually do. Also preserve "
    "traditions and ceremonies, participant activities, routes, locations and event "
    "logistics, notable event features, and details that help readers visualize or "
    "understand the event or opportunity. Achieve conciseness by tightening wording, not "
    "by deleting these details. Example: 'Sororities will open bids at 11:15 a.m. and "
    "run home to their chapters down Idaho Avenue.' is correct; shortening it to "
    "'Sororities will open bids at 11:15 a.m.' removes meaningful participant activity "
    "and is not."
)
PRESERVE_CONTACT_TITLES_RULE_TEXT = (
    "Preserve the purpose, value and context that explain why an event, service or "
    "opportunity is offered. Preserve contact information and every official contact "
    "title supplied by the source; never remove a title solely for brevity. Capitalize a "
    "title immediately before a person's name. Prefer placing it after the name in "
    "AP-style lowercase, such as 'Danny Conklin, concessions manager,' and keep each "
    "title associated with the correct person. Shorten wording, not meaning or "
    "credentials."
)


RULES = (
    (
        "content_filtering",
        "preserve_action_deadlines",
        PRESERVE_REQUIREMENTS_RULE_TEXT,
        "error",
    ),
    (
        "content_filtering",
        "preserve_organizational_context",
        PRESERVE_ORGANIZATIONAL_CONTEXT_RULE_TEXT,
        "error",
    ),
    (
        "content_filtering",
        "preserve_information_options",
        PRESERVE_INFORMATION_OPTIONS_RULE_TEXT,
        "error",
    ),
    (
        "content_filtering",
        "preserve_event_context",
        PRESERVE_PARTICIPANT_CONTEXT_RULE_TEXT,
        "error",
    ),
    (
        "content_filtering",
        "preserve_purpose_contact_titles",
        PRESERVE_CONTACT_TITLES_RULE_TEXT,
        "error",
    ),
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


def _upsert_rules(connection: sa.Connection) -> None:
    for category, rule_key, rule_text, severity in RULES:
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
                style_rules.update()
                .where(style_rules.c.Id == existing_id)
                .values(**values)
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
    _upsert_rules(op.get_bind())


def downgrade() -> None:
    # Text-only revisions of managed rules are not automatically reverted.
    pass
