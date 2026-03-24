"""add Second_Requested_Date to submission_schedule_requests if missing

Revision ID: b8f9c2d4e6a1
Revises: e1f3a9b7c4d2
Create Date: 2026-03-24 11:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8f9c2d4e6a1"
down_revision: Union[str, Sequence[str], None] = "e1f3a9b7c4d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "submission_schedule_requests"
COLUMN_NAME = "Second_Requested_Date"


def _existing_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def upgrade() -> None:
    """Upgrade schema."""
    if COLUMN_NAME in _existing_columns():
        return

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.add_column(sa.Column(COLUMN_NAME, sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    if COLUMN_NAME not in _existing_columns():
        return

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.drop_column(COLUMN_NAME)
