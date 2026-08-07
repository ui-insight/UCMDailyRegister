"""add Manually_Placed to newsletter items

Revision ID: f2c6a8b4d1e3
Revises: e8b2d4f6a1c9
Create Date: 2026-08-07 15:00:00.000000

Track whether staff moved a newsletter item to a different section so
newsletter re-assembly can re-sync auto-placed items to the current
category-to-section mapping without clobbering manual curation.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f2c6a8b4d1e3"
down_revision: str | Sequence[str] | None = "e8b2d4f6a1c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("newsletter_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "Manually_Placed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("newsletter_items", schema=None) as batch_op:
        batch_op.drop_column("Manually_Placed")
