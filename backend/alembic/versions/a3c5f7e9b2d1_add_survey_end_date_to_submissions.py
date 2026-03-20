"""add Survey_End_Date to submissions if missing

Revision ID: a3c5f7e9b2d1
Revises: 6f4e8a2c1b7d
Create Date: 2026-03-20 11:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3c5f7e9b2d1"
down_revision: Union[str, Sequence[str], None] = "6f4e8a2c1b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "submissions"


def _existing_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def upgrade() -> None:
    """Upgrade schema."""
    existing_columns = _existing_columns()
    if "Survey_End_Date" in existing_columns:
        return

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.add_column(sa.Column("Survey_End_Date", sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    existing_columns = _existing_columns()
    if "Survey_End_Date" not in existing_columns:
        return

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.drop_column("Survey_End_Date")
