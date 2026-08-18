"""preserve specific audience and action-focused language

Revision ID: a4c6e8f0b2d3
Revises: f3d5b7c9e1a2
Create Date: 2026-08-18 12:15:00.000000

Joy's feedback identified a conflict in the research template and clarified
that promotional leads, precise audience descriptions and direct contact
language take precedence over generic phrasing. The focused upsert preserves
unrelated staff-managed rules.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "a4c6e8f0b2d3"
down_revision: str | Sequence[str] | None = "f3d5b7c9e1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RESEARCH_STUDY_RULE_TEXT = (
    "Research recruitment announcements must begin with the most specific accurate "
    "audience description supplied by the source, followed by the study topic. Never "
    "default to generic words such as 'participants,' 'individuals' or 'people' when "
    "the source identifies breastfeeding or lactating women, donors, volunteers, "
    "faculty members, first-year students, alumni or another precise group. Include "
    "important eligibility qualifiers, such as an age range, in the first sentence "
    "whenever concise. Example: 'Researchers are seeking breastfeeding women ages "
    "18-50 for a study on human milk composition,' not 'Researchers are recruiting "
    "participants for a study.' Follow with compensation and participation details."
)
CTA_STRUCTURE_RULE_TEXT = (
    "Structure announcements around one clear call to action and supporting context. "
    "Replace vague instructions with an explicit action, but do not repeat that action "
    "elsewhere in the item. Use direct information-first contact language such as 'For "
    "more information, contact Betsy Church,' never 'Interested participants should "
    "contact Betsy Church.' Edit user-supplied linked text when needed for clarity, "
    "concision and editorial style; linked text is not immutable. Replace generic "
    "unlinked references such as 'landing page,' 'webpage,' 'here' or 'click here' with "
    "descriptive linked text that names the action or destination. Do not introduce "
    "audience qualifiers that are not in the original submission. When the submission "
    "provides a contact's full name, use it rather than a bare email address. Link the "
    "action verb or object: 'Sign up', 'Register for the workshop', 'Apply for the "
    "scholarship' or 'Review the promotion details'."
)
PROMOTIONAL_LEAD_RULE_TEXT = (
    "Promotional announcements must lead with the action readers should take and the "
    "benefit they can receive. Put important qualifying details early when they define "
    "the offer. Avoid passive, circular or redundant introductions such as 'The last "
    "week to have a permit reimbursed is this week.' Prefer 'This is the final week to "
    "enroll in a qualifying meal plan for a chance to have a commuter parking permit "
    "reimbursed in full.' Remove audience references that do not affect eligibility. "
    "Consolidate repeated actions into one descriptive linked call to action and shorten "
    "supporting wording rather than repeating the offer."
)
PRESERVE_AUDIENCE_RULE_TEXT = (
    "Do not narrow, broaden or genericize the intended audience. Preserve broad audience "
    "meaning such as 'all are welcome,' 'everyone is invited' or 'the public is welcome.' "
    "Also preserve the most specific accurate source description, such as donors, "
    "breastfeeding or lactating women, volunteers, faculty members, first-year students "
    "or alumni, instead of replacing it with 'participants,' 'individuals' or 'people.' "
    "For recruitment announcements, include the specific group in the first sentence "
    "whenever possible and surface important eligibility qualifiers early enough that "
    "the offer is not misleading. For concise event invitations, replace broad wording "
    "with a direct invitation such as 'Attend the workshop,' never with a narrower group "
    "unless the original explicitly limits attendance."
)


RULES = (
    ("formatting", "research_study_format", RESEARCH_STUDY_RULE_TEXT, "error"),
    ("voice", "cta_structure", CTA_STRUCTURE_RULE_TEXT, "error"),
    (
        "voice",
        "promotional_action_benefit_lead",
        PROMOTIONAL_LEAD_RULE_TEXT,
        "error",
    ),
    (
        "content_filtering",
        "preserve_audience_scope",
        PRESERVE_AUDIENCE_RULE_TEXT,
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
