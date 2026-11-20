"""fictional example in the contact line rule

Revision ID: 512cdfd1ec2e
Revises: f8b2d4a6c1e3
Create Date: 2026-11-20 16:00:00.000000

The shared `contact_line_format` style rule illustrated itself with a
real-looking name, University email address and phone number. The rule text is
sent in the system prompt of every AI edit, and project rules require
synthetic examples. Swap in an obviously fictional contact (a 555 number and
an example.edu address). Only those example substrings are replaced, so any
other staff edits to the rule survive.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "512cdfd1ec2e"
down_revision: str | Sequence[str] | None = "f8b2d4a6c1e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Old example -> fictional replacement. The email goes before the name so the
# name swap cannot break it.
_SWAPS = (
    ("prowley@uidaho.edu", "jsample@example.edu"),
    ("208-885-1234", "208-555-0100"),
    ("Paul Rowley", "Jordan Sample"),
)


def _swap(pairs: Sequence[tuple[str, str]]) -> None:
    rule_text = sa.column("Rule_Text", sa.Text)
    style_rules = sa.table("style_rules", sa.column("Rule_Key"), sa.column("Rule_Set"), rule_text)
    connection = op.get_bind()
    for old, new in pairs:
        connection.execute(
            style_rules.update()
            .where(
                style_rules.c.Rule_Set == "shared",
                style_rules.c.Rule_Key == "contact_line_format",
            )
            .values(Rule_Text=sa.func.replace(rule_text, old, new))
        )


def upgrade() -> None:
    _swap(_SWAPS)


def downgrade() -> None:
    # The real-looking example is not restored: it should not come back.
    pass
