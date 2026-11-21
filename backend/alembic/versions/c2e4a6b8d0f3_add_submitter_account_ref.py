"""add Submitter_Account_Ref to submissions

Revision ID: c2e4a6b8d0f3
Revises: 512cdfd1ec2e
Create Date: 2026-11-20 18:00:00.000000

Records which signed-in account sent each submission: the Microsoft Entra
object ID (`oid`) from the session token, the same reference the audit trail
uses. Existing rows stay null; nothing is backfilled because the account that
sent them was never recorded.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c2e4a6b8d0f3"
down_revision: str | Sequence[str] | None = "512cdfd1ec2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX = "ix_submissions_Submitter_Account_Ref"


def upgrade() -> None:
    with op.batch_alter_table("submissions") as batch:
        batch.add_column(
            sa.Column("Submitter_Account_Ref", sa.String(64), nullable=True)
        )
    op.create_index(INDEX, "submissions", ["Submitter_Account_Ref"])


def downgrade() -> None:
    op.drop_index(INDEX, table_name="submissions")
    with op.batch_alter_table("submissions") as batch:
        batch.drop_column("Submitter_Account_Ref")
