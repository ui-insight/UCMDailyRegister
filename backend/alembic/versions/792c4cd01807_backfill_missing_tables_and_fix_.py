"""backfill missing tables and fix nullable drift

Revision ID: 792c4cd01807
Revises: d2e3f4a5b6c7
Create Date: 2026-04-17 14:13:33.806009

Three tables and one NOT NULL constraint exist in the models but not in the
migration history — drift accumulated from edits that skipped
`alembic revision --autogenerate`. Existing deployments already have these
tables via `Base.metadata.create_all()` at app startup; fresh deployments
that rely only on `alembic upgrade head` will not. This migration is
idempotent — it inspects the live schema and only creates what's missing —
so it is safe to run against both.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "792c4cd01807"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_nullable(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    for col in inspector.get_columns(table):
        if col["name"] == column:
            return bool(col.get("nullable", True))
    return True


def upgrade() -> None:
    existing = _existing_tables()

    if "blackout_dates" not in existing:
        op.create_table(
            "blackout_dates",
            sa.Column("Id", sa.String(length=36), nullable=False),
            sa.Column("Blackout_Date", sa.Date(), nullable=False),
            sa.Column("Newsletter_Type", sa.String(length=50), nullable=True),
            sa.Column("Description", sa.Text(), nullable=True),
            sa.Column("Is_Active", sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint("Id"),
            sa.UniqueConstraint(
                "Blackout_Date", "Newsletter_Type", name="uq_blackout_date_newsletter"
            ),
        )

    if "custom_publish_dates" not in existing:
        op.create_table(
            "custom_publish_dates",
            sa.Column("Id", sa.String(length=36), nullable=False),
            sa.Column("Newsletter_Type", sa.String(length=50), nullable=False),
            sa.Column("Publish_Date", sa.Date(), nullable=False),
            sa.Column("Description", sa.Text(), nullable=True),
            sa.Column("Created_At", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("Id"),
            sa.UniqueConstraint(
                "Newsletter_Type", "Publish_Date", name="uq_custom_publish_date"
            ),
        )

    if "schedule_mode_overrides" not in existing:
        op.create_table(
            "schedule_mode_overrides",
            sa.Column("Id", sa.String(length=36), nullable=False),
            sa.Column("Newsletter_Type", sa.String(length=50), nullable=False),
            sa.Column("Override_Mode", sa.String(length=50), nullable=False),
            sa.Column("Start_Date", sa.Date(), nullable=False),
            sa.Column("End_Date", sa.Date(), nullable=False),
            sa.Column("Description", sa.Text(), nullable=True),
            sa.Column("Created_At", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("Id"),
        )

    if _column_nullable("schedule_configs", "Holiday_Shift_Enabled"):
        with op.batch_alter_table("schedule_configs", schema=None) as batch_op:
            batch_op.alter_column(
                "Holiday_Shift_Enabled",
                existing_type=sa.Boolean(),
                nullable=False,
                existing_server_default=sa.text("(false)"),
            )


def downgrade() -> None:
    with op.batch_alter_table("schedule_configs", schema=None) as batch_op:
        batch_op.alter_column(
            "Holiday_Shift_Enabled",
            existing_type=sa.Boolean(),
            nullable=True,
            existing_server_default=sa.text("(false)"),
        )

    op.drop_table("schedule_mode_overrides")
    op.drop_table("custom_publish_dates")
    op.drop_table("blackout_dates")
