"""add edit_versions.Policy_Fingerprint

Revision ID: e7a9c1d3f5b8
Revises: d6e8f0a2b4c7
Create Date: 2026-11-04 15:30:00.000000

Record which editorial policy version and active rule set produced each AI
suggestion (#411). Nullable: earlier versions predate the field.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e7a9c1d3f5b8"
down_revision: str | Sequence[str] | None = "d6e8f0a2b4c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("edit_versions")}
    if "Policy_Fingerprint" not in columns:
        with op.batch_alter_table("edit_versions", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("Policy_Fingerprint", sa.String(64), nullable=True)
            )


def downgrade() -> None:
    with op.batch_alter_table("edit_versions", schema=None) as batch_op:
        batch_op.drop_column("Policy_Fingerprint")
