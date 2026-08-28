"""add_upstream_changed_at_to_harvested_events

Revision ID: b9c1d3e5f7a2
Revises: a8b0c2d4e6f1
Create Date: 2026-08-28 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b9c1d3e5f7a2"
down_revision: Union[str, Sequence[str], None] = "a8b0c2d4e6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("harvested_events")}

    if "Upstream_Changed_At" not in columns:
        with op.batch_alter_table("harvested_events", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("Upstream_Changed_At", sa.DateTime(), nullable=True)
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("harvested_events", schema=None) as batch_op:
        batch_op.drop_column("Upstream_Changed_At")
