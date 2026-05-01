"""add_editor_instructions_to_edit_versions

Revision ID: 2b6a9d4c1e8f
Revises: c9d8e7f6a5b4
Create Date: 2026-05-01 06:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b6a9d4c1e8f"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("edit_versions", sa.Column("Editor_Instructions", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("edit_versions", "Editor_Instructions")
