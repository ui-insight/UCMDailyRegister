"""add editorial fields to submissions

Revision ID: f1b2c3d4e5f6
Revises: a3c5f7e9b2d1
Create Date: 2026-03-20 12:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "a3c5f7e9b2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "submissions"


def _existing_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def upgrade() -> None:
    """Upgrade schema."""
    existing_columns = _existing_columns()

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        if "Assigned_Editor" not in existing_columns:
            batch_op.add_column(sa.Column("Assigned_Editor", sa.String(length=255), nullable=True))
        if "Editorial_Notes" not in existing_columns:
            batch_op.add_column(sa.Column("Editorial_Notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    existing_columns = _existing_columns()

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        if "Editorial_Notes" in existing_columns:
            batch_op.drop_column("Editorial_Notes")
        if "Assigned_Editor" in existing_columns:
            batch_op.drop_column("Assigned_Editor")
