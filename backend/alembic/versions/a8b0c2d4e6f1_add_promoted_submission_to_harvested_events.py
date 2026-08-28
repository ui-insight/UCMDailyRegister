"""add_promoted_submission_to_harvested_events

Revision ID: a8b0c2d4e6f1
Revises: f4a6c8e0b2d5
Create Date: 2026-08-28 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8b0c2d4e6f1"
down_revision: Union[str, Sequence[str], None] = "f4a6c8e0b2d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("harvested_events")}

    if "Promoted_Submission_Id" not in columns:
        with op.batch_alter_table("harvested_events", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("Promoted_Submission_Id", sa.String(length=36), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_harvested_events_promoted_submission",
                "submissions",
                ["Promoted_Submission_Id"],
                ["Id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("harvested_events", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_harvested_events_promoted_submission", type_="foreignkey"
        )
        batch_op.drop_column("Promoted_Submission_Id")
