"""add_ops_need_assessments

Revision ID: d4f6b8c0e2a5
Revises: c3e5a7d9f1b4
Create Date: 2026-08-31 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4f6b8c0e2a5"
down_revision: Union[str, Sequence[str], None] = "c3e5a7d9f1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("harvested_events")}

    if "Ops_Assessed_Content_Hash" not in columns:
        with op.batch_alter_table("harvested_events", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "Ops_Assessed_Content_Hash", sa.String(length=64), nullable=True
                )
            )

    if "ops_need_assessments" not in tables:
        op.create_table(
            "ops_need_assessments",
            sa.Column("Id", sa.String(length=36), nullable=False),
            sa.Column("Harvested_Event_Id", sa.String(length=36), nullable=False),
            sa.Column("Need", sa.String(length=50), nullable=False),
            sa.Column("Confidence", sa.String(length=20), nullable=False),
            sa.Column("Rationale", sa.Text(), nullable=False),
            sa.Column(
                "Created_At",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["Harvested_Event_Id"], ["harvested_events.Id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("Id"),
            sa.UniqueConstraint(
                "Harvested_Event_Id", "Need", name="uq_ops_need_assessment_event_need"
            ),
        )
        op.create_index(
            "ix_ops_need_assessments_Harvested_Event_Id",
            "ops_need_assessments",
            ["Harvested_Event_Id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_ops_need_assessments_Harvested_Event_Id",
        table_name="ops_need_assessments",
    )
    op.drop_table("ops_need_assessments")
    with op.batch_alter_table("harvested_events", schema=None) as batch_op:
        batch_op.drop_column("Ops_Assessed_Content_Hash")
