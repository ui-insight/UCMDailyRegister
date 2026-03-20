"""backfill missing recurrence columns on submission schedule requests

Revision ID: 6f4e8a2c1b7d
Revises: c7d6f3416b9e
Create Date: 2026-03-20 11:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f4e8a2c1b7d"
down_revision: Union[str, Sequence[str], None] = "c7d6f3416b9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "submission_schedule_requests"


def _existing_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def upgrade() -> None:
    """Upgrade schema."""
    existing_columns = _existing_columns()

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        if "Recurrence_Type" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "Recurrence_Type",
                    sa.String(length=50),
                    nullable=False,
                    server_default=sa.text("'once'"),
                )
            )
        if "Recurrence_Interval" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "Recurrence_Interval",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("1"),
                )
            )
        if "Recurrence_End_Date" not in existing_columns:
            batch_op.add_column(
                sa.Column("Recurrence_End_Date", sa.Date(), nullable=True)
            )
        if "Excluded_Dates" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "Excluded_Dates",
                    sa.JSON(),
                    nullable=False,
                    server_default=sa.text("'[]'"),
                )
            )


def downgrade() -> None:
    """Downgrade schema."""
    existing_columns = _existing_columns()

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        if "Excluded_Dates" in existing_columns:
            batch_op.drop_column("Excluded_Dates")
        if "Recurrence_End_Date" in existing_columns:
            batch_op.drop_column("Recurrence_End_Date")
        if "Recurrence_Interval" in existing_columns:
            batch_op.drop_column("Recurrence_Interval")
        if "Recurrence_Type" in existing_columns:
            batch_op.drop_column("Recurrence_Type")
