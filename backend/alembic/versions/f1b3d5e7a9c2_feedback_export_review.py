"""Record reviewed feedback exports without retaining another report copy.

Revision ID: f1b3d5e7a9c2
Revises: e9a1b3c5d7f2
"""

from alembic import op
import sqlalchemy as sa

revision = "f1b3d5e7a9c2"
down_revision = "e9a1b3c5d7f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_feedback", sa.Column("GitHub_Export_Reviewed_At", sa.DateTime(), nullable=True))
    op.add_column("product_feedback", sa.Column("GitHub_Export_SHA256", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("product_feedback", "GitHub_Export_SHA256")
    op.drop_column("product_feedback", "GitHub_Export_Reviewed_At")
