"""add Repeats_Indefinitely to submission schedule requests

Revision ID: e4a6c8b0d2f5
Revises: d2b4f6a8c0e1
Create Date: 2026-11-19 12:00:00.000000

UCM staff can mark a weekly or monthly schedule as repeating with no end
date (#538). The choice is stored as its own boolean so that it cannot be
confused with the older rows that simply have no end date. Those rows keep
running only on their requested dates (#477): every existing row gets
``False`` and no schedule data is changed.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e4a6c8b0d2f5"
down_revision: str | Sequence[str] | None = "d2b4f6a8c0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE = "submission_schedule_requests"
COLUMN = "Repeats_Indefinitely"


def upgrade() -> None:
    """Add the flag; every existing schedule starts as not indefinite."""
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns(TABLE)}
    if COLUMN in columns:
        return
    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                COLUMN,
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    """Drop the flag. Indefinite schedules fall back to running once."""
    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.drop_column(COLUMN)
