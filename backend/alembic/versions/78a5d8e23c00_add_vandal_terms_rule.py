"""add official Vandal terms rule

Revision ID: 78a5d8e23c00
Revises: b3d5f7a9c1e4
Create Date: 2026-11-16 12:00:00.000000

Joy gave the official forms of nine U of I Vandal terms (#480): Vandal
Alert, VandalCard, VandalCARE, VandalChat, Vandal Connect, Vandal Family,
Vandal Gear, VandalMail and VandalStore. The Aug. 5 rule
``vandal_gear_capitalization`` covered only Vandal Gear, so this migration
renames that row to ``vandal_terms`` (keeping its Id) and gives it the full
list. A deterministic check flags any variant left in the edited copy under
the same rule key. Idempotent; touches only these two managed rule keys.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "78a5d8e23c00"
down_revision: str | Sequence[str] | None = "b3d5f7a9c1e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RULE_SET = "shared"
RULE_KEY = "vandal_terms"
CATEGORY = "terminology"
SEVERITY = "error"
RULE_TEXT = (
    "Write these U of I Vandal terms in their official form: 'Vandal Alert' "
    "(two words, each capitalized); 'VandalCard' (one word, two capitals, no "
    "space); 'VandalCARE' (one word, Vandal capitalized and CARE in all "
    "capitals); 'VandalChat' (one word, two capitals, no space); 'Vandal "
    "Connect' (two words); 'Vandal Family' (two capitalized words); 'Vandal "
    "Gear' (two capitalized words); 'VandalMail' (one word, Vandal and Mail "
    "capitalized, no space); 'VandalStore' (one word, two capitals, no "
    "space). Replace any other spacing, hyphenation or capitalization of these"
    " terms, such as 'Vandal Card', 'Vandalmail', 'VandalAlert', 'Vandal "
    "Care' or 'VandalGear', with the official form, even when the submitter "
    "wrote the variant. This rule takes precedence over keeping product and "
    "program names as submitted. Leave web and email addresses unchanged."
)

SUPERSEDED_RULE_KEY = "vandal_gear_capitalization"
SUPERSEDED_RULE_TEXT = (
    "Always write 'Vandal Gear' as two capitalized words. Replace "
    "'VandalGear', 'Vandal gear' or other variants with 'Vandal Gear'."
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


def _rule_id(connection: sa.Connection, rule_key: str) -> str | None:
    return connection.execute(
        sa.select(style_rules.c.Id).where(
            style_rules.c.Rule_Set == RULE_SET,
            style_rules.c.Rule_Key == rule_key,
        )
    ).scalar_one_or_none()


def apply_vandal_terms_rule(connection: sa.Connection) -> None:
    """Rename the Vandal Gear rule to vandal_terms, or add it; then set its text."""
    values = {
        "Category": CATEGORY,
        "Rule_Text": RULE_TEXT,
        "Is_Active": True,
        "Severity": SEVERITY,
    }
    current_id = _rule_id(connection, RULE_KEY)
    superseded_id = _rule_id(connection, SUPERSEDED_RULE_KEY)
    if current_id is None and superseded_id is not None:
        connection.execute(
            style_rules.update()
            .where(style_rules.c.Id == superseded_id)
            .values(Rule_Key=RULE_KEY, **values)
        )
        return
    if current_id is None:
        connection.execute(
            style_rules.insert().values(
                Id=str(uuid.uuid4()),
                Rule_Set=RULE_SET,
                Rule_Key=RULE_KEY,
                **values,
            )
        )
    else:
        connection.execute(
            style_rules.update().where(style_rules.c.Id == current_id).values(**values)
        )
    if superseded_id is not None:
        # Both rows exist (for example, the seed ran first): the new rule
        # covers Vandal Gear, so the old one would only repeat it.
        connection.execute(
            style_rules.update()
            .where(style_rules.c.Id == superseded_id)
            .values(Is_Active=False)
        )


def restore_vandal_gear_rule(connection: sa.Connection) -> None:
    """Undo ``apply_vandal_terms_rule``: back to the Vandal Gear-only rule."""
    current_id = _rule_id(connection, RULE_KEY)
    superseded_id = _rule_id(connection, SUPERSEDED_RULE_KEY)
    if current_id is None:
        return
    if superseded_id is None:
        connection.execute(
            style_rules.update()
            .where(style_rules.c.Id == current_id)
            .values(
                Rule_Key=SUPERSEDED_RULE_KEY,
                Rule_Text=SUPERSEDED_RULE_TEXT,
                Category=CATEGORY,
                Severity=SEVERITY,
            )
        )
        return
    connection.execute(style_rules.delete().where(style_rules.c.Id == current_id))
    connection.execute(
        style_rules.update()
        .where(style_rules.c.Id == superseded_id)
        .values(Is_Active=True)
    )


def upgrade() -> None:
    apply_vandal_terms_rule(op.get_bind())


def downgrade() -> None:
    restore_vandal_gear_rule(op.get_bind())
