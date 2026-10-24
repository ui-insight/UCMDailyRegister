"""Persist AI edit tasks and their committed results for restart recovery.

Revision ID: e9a1b3c5d7f2
Revises: d4f6a8c0e2b5
"""

from alembic import op
import sqlalchemy as sa

revision = "e9a1b3c5d7f2"
down_revision = "d4f6a8c0e2b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_edit_tasks",
        sa.Column("Id", sa.String(36), primary_key=True),
        sa.Column(
            "Submission_Id",
            sa.String(36),
            sa.ForeignKey("submissions.Id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("Newsletter_Type", sa.String(50), nullable=False),
        sa.Column("Editor_Instructions", sa.Text(), nullable=True),
        sa.Column("Status", sa.String(50), nullable=False),
        sa.Column("Source_Fingerprint", sa.String(64), nullable=False),
        sa.Column("Active_Key", sa.String(73), nullable=True, unique=True),
        sa.Column("Run_Id", sa.String(36), nullable=True),
        sa.Column("Result_JSON", sa.JSON(), nullable=True),
        sa.Column("Error_Message", sa.Text(), nullable=True),
        sa.Column("Created_At", sa.DateTime(), nullable=False),
        sa.Column("Updated_At", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_edit_tasks_Submission_Id", "ai_edit_tasks", ["Submission_Id"])
    op.create_index("ix_ai_edit_tasks_Status", "ai_edit_tasks", ["Status"])


def downgrade() -> None:
    op.drop_index("ix_ai_edit_tasks_Status", table_name="ai_edit_tasks")
    op.drop_index("ix_ai_edit_tasks_Submission_Id", table_name="ai_edit_tasks")
    op.drop_table("ai_edit_tasks")
