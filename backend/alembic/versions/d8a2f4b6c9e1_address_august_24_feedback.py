"""address Aug. 24 UCM editor and submission feedback

Revision ID: d8a2f4b6c9e1
Revises: c7e9a1b3d5f2
Create Date: 2026-08-25 11:35:00.000000

Editors reported AI headlines changing the source call to action and event
details being split into standalone fragments. The public submission form also
needs the common Employee (Faculty/Staff) category first. Apply only these
managed reference-data updates so existing databases receive the corrections
without overwriting unrelated staff-maintained rules or allowed values.
"""

from collections.abc import Sequence
import json
from pathlib import Path
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "d8a2f4b6c9e1"
down_revision: str | Sequence[str] | None = "c7e9a1b3d5f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The shared seed file is the single source of truth for managed rule wording;
# this migration only selects which rules to sync into existing databases.
_SHARED_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "style_rules" / "shared_rules.json"
)
MANAGED_RULE_KEYS = (
    "event_detail_ordering",
    "short_sentences",
    "headline_reader_perspective",
)


def _load_style_rule_updates() -> list[dict]:
    seeded = {
        rule["rule_key"]: rule for rule in json.loads(_SHARED_RULES_PATH.read_text())
    }
    return [seeded[rule_key] for rule_key in MANAGED_RULE_KEYS]


STYLE_RULE_UPDATES = _load_style_rule_updates()


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

allowed_values = sa.table(
    "allowed_values",
    sa.column("Value_Group", sa.String(100)),
    sa.column("Code", sa.String(100)),
    sa.column("Label", sa.String(255)),
    sa.column("Display_Order", sa.Integer),
)


def _apply_august_24_feedback_updates(connection: sa.Connection) -> None:
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

    connection.execute(
        allowed_values.update()
        .where(
            allowed_values.c.Value_Group == "Submission_Category",
            allowed_values.c.Code == "employee_announcement",
        )
        .values(Label="Employee (Faculty/Staff)", Display_Order=0)
    )


def upgrade() -> None:
    _apply_august_24_feedback_updates(op.get_bind())


def downgrade() -> None:
    # Preserve any subsequent staff edits to managed wording and category order.
    pass
