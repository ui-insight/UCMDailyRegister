"""add Bruce M. Pitman Center and well-being rules

Revision ID: d2b4f6a8c0e1
Revises: c3f5a7e9b1d2
Create Date: 2026-11-17 12:00:00.000000

Joy's Nov. 17 feedback (#529): the student union is "Bruce M. Pitman
Center" on first reference, followed by the room, and "Pitman Center" only
after that; "well-being" is always hyphenated. This migration adds both as
error-level shared rules. It also changes the example in
``event_detail_ordering`` from "the Pitman Center Vandal Ballroom" to "the
Bruce M. Pitman Center Vandal Ballroom", because that example taught the
short form on first reference. The example is replaced in place, so other
staff edits to that rule are kept. Idempotent.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "d2b4f6a8c0e1"
down_revision: str | Sequence[str] | None = "c3f5a7e9b1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RULE_SET = "shared"
CATEGORY = "terminology"
SEVERITY = "error"

PITMAN_RULE_KEY = "pitman_center_first_reference"
PITMAN_RULE_TEXT = (
    "Call the student union building 'Bruce M. Pitman Center' on first "
    "reference, followed by the specific room or venue when there is one, for "
    "example 'Bruce M. Pitman Center International Ballroom'. Use 'Pitman "
    "Center' only on second and later references. On first reference, "
    "replace 'Pitman Center', 'Bruce Pitman Center' or 'Bruce M Pitman "
    "Center' with 'Bruce M. Pitman Center', even when the submitter wrote the "
    "short form. Leave web and email addresses unchanged."
)

WELL_BEING_RULE_KEY = "well_being_hyphenated"
WELL_BEING_RULE_TEXT = (
    "Always write 'well-being' with a hyphen. Replace 'well being' and "
    "'wellbeing' with 'well-being', even when the submitter wrote the variant. "
    "Capitalize it as 'Well-being' at the start of a sentence or headline. "
    "Leave web and email addresses unchanged."
)

NEW_RULES = {
    WELL_BEING_RULE_KEY: WELL_BEING_RULE_TEXT,
    PITMAN_RULE_KEY: PITMAN_RULE_TEXT,
}

EVENT_RULE_KEY = "event_detail_ordering"
OLD_EXAMPLE = "in the Pitman Center Vandal Ballroom."
NEW_EXAMPLE = "in the Bruce M. Pitman Center Vandal Ballroom."


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


def _rule(connection: sa.Connection, rule_key: str):
    return connection.execute(
        sa.select(style_rules.c.Id, style_rules.c.Rule_Text).where(
            style_rules.c.Rule_Set == RULE_SET,
            style_rules.c.Rule_Key == rule_key,
        )
    ).first()


def _replace_example(connection: sa.Connection, old: str, new: str) -> None:
    row = _rule(connection, EVENT_RULE_KEY)
    if row is None or old not in row.Rule_Text:
        return
    connection.execute(
        style_rules.update()
        .where(style_rules.c.Id == row.Id)
        .values(Rule_Text=row.Rule_Text.replace(old, new))
    )


def apply_rules(connection: sa.Connection) -> None:
    """Add or refresh the two rules and fix the event-detail example."""
    for rule_key, rule_text in NEW_RULES.items():
        values = {
            "Category": CATEGORY,
            "Rule_Text": rule_text,
            "Is_Active": True,
            "Severity": SEVERITY,
        }
        row = _rule(connection, rule_key)
        if row is None:
            connection.execute(
                style_rules.insert().values(
                    Id=str(uuid.uuid4()), Rule_Set=RULE_SET, Rule_Key=rule_key, **values
                )
            )
        else:
            connection.execute(
                style_rules.update().where(style_rules.c.Id == row.Id).values(**values)
            )
    _replace_example(connection, OLD_EXAMPLE, NEW_EXAMPLE)


def remove_rules(connection: sa.Connection) -> None:
    """Undo ``apply_rules``."""
    connection.execute(
        style_rules.delete().where(
            style_rules.c.Rule_Set == RULE_SET,
            style_rules.c.Rule_Key.in_(list(NEW_RULES)),
        )
    )
    _replace_example(connection, NEW_EXAMPLE, OLD_EXAMPLE)


def upgrade() -> None:
    apply_rules(op.get_bind())


def downgrade() -> None:
    remove_rules(op.get_bind())
