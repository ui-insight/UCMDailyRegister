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
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "d8a2f4b6c9e1"
down_revision: str | Sequence[str] | None = "c7e9a1b3d5f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STYLE_RULE_UPDATES = [
    {
        "category": "formatting",
        "rule_key": "event_detail_ordering",
        "rule_text": (
            "Start event-detail constructions with the time, then give the day, "
            "date and location in that order. Example: '3-4 p.m. Wednesday, Feb. "
            "12, in the Pitman Center Vandal Ballroom.' Never place the day or "
            "date before the time. Keep the time, day, date and location in the "
            "same complete sentence as the event name. Never begin a separate "
            "sentence with a time, date, day of the week or location fragment. "
            "Correct: 'Stop by the Asian Studies Library Open House 2-4 p.m. "
            "Thursday, Sept. 3, in Admin 204.' Incorrect: 'Stop by the Asian "
            "Studies Library Open House. 2-4 p.m. Thursday, Sept. 3, in Admin "
            "204.' Do not omit these elements. If the event is more than one "
            "month away, omit the day of the week."
        ),
        "severity": "error",
    },
    {
        "category": "voice",
        "rule_key": "short_sentences",
        "rule_text": (
            "Use short, complete sentences. Each sentence should communicate "
            "one main idea. Do not use semicolons. Replace semicolons with "
            "periods. Split compound or lengthy sentences into separate "
            "sentences. Favor clear, direct wording over complex sentence "
            "structures. Keep sentences concise and easy to read. Never "
            "separate an event from its time, date or location when shortening "
            "or splitting prose; keep those details together in one complete "
            "sentence."
        ),
        "severity": "error",
    },
    {
        "category": "headlines",
        "rule_key": "headline_reader_perspective",
        "rule_text": (
            "Headlines must be written from the reader's perspective using "
            "verbs that accurately reflect the action the original submission "
            "asks readers to take. Preserve the primary action, purpose and "
            "intent; never substitute a different activity or transaction. "
            "When an author reads from a book, invite readers to attend a "
            "reading, not read or purchase the book. Correct headlines include "
            "'Attend Elizabeth Bradfield's reading from SOFAR' and 'Hear "
            "Elizabeth Bradfield read from SOFAR.' Incorrect headlines include "
            "'Read Elizabeth Bradfield's poetry collection SOFAR' and "
            "'Purchase Elizabeth Bradfield's poetry collection.' Likewise, "
            "write 'Participate in VR research study' not 'Recruit research "
            "participants'."
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
