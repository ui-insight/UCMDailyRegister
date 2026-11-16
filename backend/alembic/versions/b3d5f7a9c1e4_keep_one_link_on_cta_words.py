"""keep one link on the call-to-action words

Revision ID: b3d5f7a9c1e4
Revises: a8c0e2f4b6d9
Create Date: 2026-11-16 10:00:00.000000

Joy's link rules (#478): a URL the body repeats from the link field is
removed so the call-to-action words carry the link; a URL is never link
text and is linked once per item; and one URL with one call to action is a
single call to action, even when its words name more than one action, so
the information-options rule no longer asks for it to be split. Idempotent
upserts of the two managed rule keys; staff-added rules are untouched.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "b3d5f7a9c1e4"
down_revision: str | Sequence[str] | None = "a8c0e2f4b6d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (rule_key, category, rule_text, severity)
RULES: list[tuple[str, str, str, str]] = [
    (
        "link_embedding",
        "formatting",
        (
            "Embed hyperlinks in meaningful anchor text rather than displaying raw "
            "URLs. Use descriptive link text like 'Learn more', 'Register', 'Apply "
            "now'. Never use a URL as link text, and link each URL only once in an "
            "item. When the submission gives call-to-action words for a link and "
            "the body also writes out that URL, remove the written-out URL and "
            "rework the sentence so the call-to-action words carry the link."
        ),
        "warning",
    ),
    (
        "preserve_information_options",
        "content_filtering",
        (
            "Preserve every distinct action and information-seeking option offered "
            "by the source. If readers may sign up or learn more through different "
            "paths, such as a registration link and a contact for questions, retain"
            " both options; do not narrow a general invitation to contact or reach "
            "out into registration-only language unless registration is the "
            "source's sole purpose. A request for more information is not a "
            "duplicate call to action and takes precedence over the single-CTA "
            "rule. One URL with one call to action is a single call to action, even"
            " when its words name more than one action, such as 'Learn more and "
            "sign up': keep those words together on the one link and do not split "
            "them or flag them under this rule. Shorten surrounding wording instead"
            " of deleting the information path."
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


def _upsert_rules(connection: sa.Connection) -> None:
    for rule_key, category, rule_text, severity in RULES:
        existing_id = connection.execute(
            sa.select(style_rules.c.Id).where(
                style_rules.c.Rule_Set == "shared",
                style_rules.c.Rule_Key == rule_key,
            )
        ).scalar_one_or_none()
        values = {"Category": category, "Rule_Text": rule_text, "Severity": severity}
        if existing_id:
            # Text-only revision: a rule staff switched off stays off.
            connection.execute(
                style_rules.update().where(style_rules.c.Id == existing_id).values(**values)
            )
        else:
            connection.execute(
                style_rules.insert().values(
                    Id=str(uuid.uuid4()),
                    Rule_Set="shared",
                    Rule_Key=rule_key,
                    Is_Active=True,
                    **values,
                )
            )


def upgrade() -> None:
    _upsert_rules(op.get_bind())


def downgrade() -> None:
    # Text-only revisions of managed rules are not automatically reverted.
    pass
