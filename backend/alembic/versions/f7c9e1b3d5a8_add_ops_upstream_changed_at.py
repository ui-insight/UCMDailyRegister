"""add_ops_upstream_changed_at

Revision ID: f7c9e1b3d5a8
Revises: e5a7c9d1f3b6
Create Date: 2026-09-01 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7c9e1b3d5a8"
down_revision: Union[str, Sequence[str], None] = "e5a7c9d1f3b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("harvested_events")}

    if "Ops_Upstream_Changed_At" not in columns:
        with op.batch_alter_table("harvested_events", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("Ops_Upstream_Changed_At", sa.DateTime(), nullable=True)
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("harvested_events", schema=None) as batch_op:
        batch_op.drop_column("Ops_Upstream_Changed_At")
