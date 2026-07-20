"""add feedback notification state

Revision ID: e7a1c3f5b9d2
Revises: c4f8a2d6e9b1
Create Date: 2026-07-20 11:00:00.000000

Add operational delivery state for in-app feedback notifications. Existing
feedback predates notification support and is marked disabled rather than
pending so the staff queue does not imply an unfinished delivery attempt.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7a1c3f5b9d2"
down_revision: str | Sequence[str] | None = "c4f8a2d6e9b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_feedback",
        sa.Column(
            "Notification_Status",
            sa.String(length=30),
            nullable=False,
            server_default="disabled",
        ),
    )
    op.add_column(
        "product_feedback",
        sa.Column(
            "Notification_Attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "product_feedback",
        sa.Column("Notification_Sent_At", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "product_feedback",
        sa.Column("Notification_Last_Error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_product_feedback_Notification_Status",
        "product_feedback",
        ["Notification_Status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_feedback_Notification_Status",
        table_name="product_feedback",
    )
    op.drop_column("product_feedback", "Notification_Last_Error")
    op.drop_column("product_feedback", "Notification_Sent_At")
    op.drop_column("product_feedback", "Notification_Attempts")
    op.drop_column("product_feedback", "Notification_Status")
