"""add_recurrence_fields_to_submission_schedule_requests

Revision ID: c7d6f3416b9e
Revises: bf1f70f4c8d9
Create Date: 2026-03-20 09:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d6f3416b9e"
down_revision: Union[str, Sequence[str], None] = "bf1f70f4c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("submission_schedule_requests", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "Is_Flexible",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("Flexible_Deadline", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "Recurrence_Type",
                sa.String(length=50),
                nullable=False,
                server_default="once",
            )
        )
        batch_op.add_column(
            sa.Column(
                "Recurrence_Interval",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column("Recurrence_End_Date", sa.Date(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "Excluded_Dates",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("submission_schedule_requests", schema=None) as batch_op:
        batch_op.drop_column("Excluded_Dates")
        batch_op.drop_column("Recurrence_End_Date")
        batch_op.drop_column("Recurrence_Interval")
        batch_op.drop_column("Recurrence_Type")
        batch_op.drop_column("Flexible_Deadline")
        batch_op.drop_column("Is_Flexible")
