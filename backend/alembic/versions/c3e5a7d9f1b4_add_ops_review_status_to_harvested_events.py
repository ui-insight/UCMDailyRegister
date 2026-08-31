"""add_ops_review_status_to_harvested_events

Revision ID: c3e5a7d9f1b4
Revises: b9c1d3e5f7a2
Create Date: 2026-08-31 13:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3e5a7d9f1b4"
down_revision: Union[str, Sequence[str], None] = "b9c1d3e5f7a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "ix_harvested_events_Ops_Review_Status_Event_Start"


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("harvested_events")}
    indexes = {index["name"] for index in inspector.get_indexes("harvested_events")}

    if "Ops_Review_Status" not in columns:
        with op.batch_alter_table("harvested_events", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "Ops_Review_Status",
                    sa.String(length=50),
                    nullable=False,
                    server_default="new",
                )
            )

    if _INDEX_NAME not in indexes:
        op.create_index(
            _INDEX_NAME,
            "harvested_events",
            ["Ops_Review_Status", "Event_Start"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(_INDEX_NAME, table_name="harvested_events")
    with op.batch_alter_table("harvested_events", schema=None) as batch_op:
        batch_op.drop_column("Ops_Review_Status")
