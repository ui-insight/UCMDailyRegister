"""add Holiday_Shift_Enabled to schedule_configs

Revision ID: d2e3f4a5b6c7
Revises: b8f9c2d4e6a1
Create Date: 2026-03-31 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "b8f9c2d4e6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "schedule_configs",
        sa.Column("Holiday_Shift_Enabled", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("schedule_configs", "Holiday_Shift_Enabled")
