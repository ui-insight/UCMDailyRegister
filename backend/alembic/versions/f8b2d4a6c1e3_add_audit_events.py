"""add audit_events table

Revision ID: f8b2d4a6c1e3
Revises: e4a6c8b0d2f5
Create Date: 2026-11-20 12:00:00.000000

Append-only per-user audit trail: who (Entra object ID and role) read,
changed, deleted or exported which record, plus authorization failures and
sign-in outcomes. No content, query strings, IPs or user agents are stored.
See docs/audit-logging.md.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f8b2d4a6c1e3"
down_revision: str | Sequence[str] | None = "e4a6c8b0d2f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "audit_events"
INDEXED = ("Occurred_At", "Actor_Ref", "Event_Type")


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("Id", sa.String(36), primary_key=True),
        sa.Column("Occurred_At", sa.DateTime(), nullable=False),
        sa.Column("Actor_Ref", sa.String(64), nullable=True),
        sa.Column("Actor_Role", sa.String(20), nullable=False),
        sa.Column("Event_Type", sa.String(40), nullable=False),
        sa.Column("Reason_Code", sa.String(40), nullable=True),
        sa.Column("Http_Method", sa.String(10), nullable=False),
        sa.Column("Route_Template", sa.String(255), nullable=False),
        sa.Column("Record_Ids", sa.JSON(), nullable=True),
        sa.Column("Changed_Fields", sa.JSON(), nullable=True),
        sa.Column("Status_Code", sa.Integer(), nullable=True),
    )
    for column in INDEXED:
        op.create_index(f"ix_{TABLE}_{column}", TABLE, [column])


def downgrade() -> None:
    for column in INDEXED:
        op.drop_index(f"ix_{TABLE}_{column}", table_name=TABLE)
    op.drop_table(TABLE)
