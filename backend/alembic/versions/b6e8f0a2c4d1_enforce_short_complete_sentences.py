"""enforce short complete sentences

Revision ID: b6e8f0a2c4d1
Revises: a5d7e9f1b3c2
Create Date: 2026-08-05 14:45:00.000000

Promote Joy's recurring short-sentence requirement to a mandatory rule. The
migration updates only the managed shared rule and preserves unrelated staff
configuration.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "b6e8f0a2c4d1"
down_revision: str | Sequence[str] | None = "a5d7e9f1b3c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SHORT_SENTENCE_RULE_TEXT = (
    "Use short, complete sentences. Each sentence should communicate one main idea. "
    "Do not use semicolons. Replace semicolons with periods. Split compound or "
    "lengthy sentences into separate sentences. Favor clear, direct wording over "
    "complex sentence structures. Keep sentences concise and easy to read."
)
PREVIOUS_RULE_TEXT = (
    "Write short, clear sentences. Avoid run-on sentences and compound-complex "
    "structures. Break long sentences into two or more shorter ones for readability. "
    "Replace semicolons with periods."
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


def _upsert_short_sentence_rule(connection: sa.Connection) -> None:
    values = {
        "Category": "voice",
        "Rule_Text": SHORT_SENTENCE_RULE_TEXT,
        "Is_Active": True,
        "Severity": "error",
    }
    result = connection.execute(
        style_rules.update()
        .where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "short_sentences",
        )
        .values(**values)
    )
    if result.rowcount == 0:
        connection.execute(
            style_rules.insert().values(
                Id=str(uuid.uuid4()),
                Rule_Set="shared",
                Rule_Key="short_sentences",
                **values,
            )
        )


def upgrade() -> None:
    _upsert_short_sentence_rule(op.get_bind())


def downgrade() -> None:
    op.get_bind().execute(
        style_rules.update()
        .where(
            style_rules.c.Rule_Set == "shared",
            style_rules.c.Rule_Key == "short_sentences",
            style_rules.c.Rule_Text == SHORT_SENTENCE_RULE_TEXT,
        )
        .values(
            Rule_Text=PREVIOUS_RULE_TEXT,
            Is_Active=True,
            Severity="warning",
        )
    )
