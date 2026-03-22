"""add recurring message library

Revision ID: e1f3a9b7c4d2
Revises: f1b2c3d4e5f6
Create Date: 2026-03-22 11:40:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f3a9b7c4d2"
down_revision: str | Sequence[str] | None = "f1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recurring_messages",
        sa.Column("Id", sa.String(length=36), nullable=False),
        sa.Column("Newsletter_Type", sa.String(length=50), nullable=False),
        sa.Column("Section_Id", sa.String(length=36), nullable=False),
        sa.Column("Headline", sa.Text(), nullable=False),
        sa.Column("Body", sa.Text(), nullable=False),
        sa.Column("Start_Date", sa.Date(), nullable=False),
        sa.Column("Recurrence_Type", sa.String(length=50), nullable=False),
        sa.Column("Recurrence_Interval", sa.Integer(), nullable=False),
        sa.Column("End_Date", sa.Date(), nullable=True),
        sa.Column("Excluded_Dates", sa.JSON(), nullable=False),
        sa.Column("Is_Active", sa.Boolean(), nullable=False),
        sa.Column("Created_At", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("Updated_At", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["Section_Id"], ["newsletter_sections.Id"]),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_table(
        "recurring_message_issue_overrides",
        sa.Column("Id", sa.String(length=36), nullable=False),
        sa.Column("Recurring_Message_Id", sa.String(length=36), nullable=False),
        sa.Column("Newsletter_Id", sa.String(length=36), nullable=False),
        sa.Column("Override_Action", sa.String(length=50), nullable=False),
        sa.Column("Created_At", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["Newsletter_Id"], ["newsletters.Id"]),
        sa.ForeignKeyConstraint(["Recurring_Message_Id"], ["recurring_messages.Id"]),
        sa.PrimaryKeyConstraint("Id"),
        sa.UniqueConstraint(
            "Recurring_Message_Id",
            "Newsletter_Id",
            name="uq_recurring_message_issue_override",
        ),
    )


def downgrade() -> None:
    op.drop_table("recurring_message_issue_overrides")
    op.drop_table("recurring_messages")
