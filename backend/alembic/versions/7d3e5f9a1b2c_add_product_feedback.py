"""add_product_feedback

Revision ID: 7d3e5f9a1b2c
Revises: 2b6a9d4c1e8f
Create Date: 2026-05-01 11:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7d3e5f9a1b2c"
down_revision: Union[str, Sequence[str], None] = "2b6a9d4c1e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_feedback",
        sa.Column("Id", sa.String(length=36), nullable=False),
        sa.Column("Feedback_Type", sa.String(length=20), nullable=False),
        sa.Column("Summary", sa.String(length=240), nullable=False),
        sa.Column("Details", sa.Text(), nullable=False),
        sa.Column("Contact_Email", sa.String(length=320), nullable=True),
        sa.Column("Submitter_Role", sa.String(length=20), nullable=False),
        sa.Column("Route", sa.String(length=500), nullable=False),
        sa.Column("App_Environment", sa.String(length=100), nullable=False),
        sa.Column("Host", sa.String(length=255), nullable=False),
        sa.Column("Browser", sa.Text(), nullable=False),
        sa.Column("Viewport", sa.String(length=50), nullable=False),
        sa.Column("Status", sa.String(length=30), nullable=False),
        sa.Column("GitHub_URL", sa.String(length=500), nullable=True),
        sa.Column("Created_At", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("Updated_At", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_index("ix_product_feedback_Created_At", "product_feedback", ["Created_At"])
    op.create_index("ix_product_feedback_Feedback_Type", "product_feedback", ["Feedback_Type"])
    op.create_index("ix_product_feedback_Status", "product_feedback", ["Status"])
    op.create_index("ix_product_feedback_Submitter_Role", "product_feedback", ["Submitter_Role"])


def downgrade() -> None:
    op.drop_index("ix_product_feedback_Submitter_Role", table_name="product_feedback")
    op.drop_index("ix_product_feedback_Status", table_name="product_feedback")
    op.drop_index("ix_product_feedback_Feedback_Type", table_name="product_feedback")
    op.drop_index("ix_product_feedback_Created_At", table_name="product_feedback")
    op.drop_table("product_feedback")
