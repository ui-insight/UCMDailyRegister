"""add_verdicts_to_ops_need_assessments

Revision ID: e5a7c9d1f3b6
Revises: d4f6b8c0e2a5
Create Date: 2026-09-01 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5a7c9d1f3b6"
down_revision: Union[str, Sequence[str], None] = "d4f6b8c0e2a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"] for column in inspector.get_columns("ops_need_assessments")
    }

    with op.batch_alter_table("ops_need_assessments", schema=None) as batch_op:
        if "Verdict" not in columns:
            batch_op.add_column(
                sa.Column(
                    "Verdict",
                    sa.String(length=20),
                    nullable=False,
                    server_default="suggested",
                )
            )
        if "Source" not in columns:
            batch_op.add_column(
                sa.Column(
                    "Source",
                    sa.String(length=20),
                    nullable=False,
                    server_default="ai",
                )
            )
        batch_op.alter_column(
            "Confidence", existing_type=sa.String(length=20), nullable=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("ops_need_assessments", schema=None) as batch_op:
        batch_op.alter_column(
            "Confidence", existing_type=sa.String(length=20), nullable=False
        )
        batch_op.drop_column("Source")
        batch_op.drop_column("Verdict")
