"""add_harvested_events_for_slc_triage

Revision ID: f4a6c8e0b2d5
Revises: d8a2f4b6c9e1
Create Date: 2026-08-28 09:00:00.000000

"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4a6c8e0b2d5"
down_revision: Union[str, Sequence[str], None] = "d8a2f4b6c9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "harvested_events" not in inspector.get_table_names():
        op.create_table(
            "harvested_events",
            sa.Column("Id", sa.String(length=36), primary_key=True),
            sa.Column("Source_Type", sa.String(length=50), nullable=False),
            sa.Column("Source_Id", sa.String(length=255), nullable=False),
            sa.Column("Series_Id", sa.String(length=255), nullable=True),
            sa.Column("Source_Url", sa.Text(), nullable=True),
            sa.Column("Title", sa.Text(), nullable=False),
            sa.Column("Description", sa.Text(), nullable=False),
            sa.Column("Location", sa.String(length=255), nullable=True),
            sa.Column("Event_Start", sa.DateTime(), nullable=False),
            sa.Column("Event_End", sa.DateTime(), nullable=True),
            sa.Column(
                "All_Day", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column("Category_Path", sa.String(length=255), nullable=True),
            sa.Column(
                "Is_Canceled", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column("Content_Hash", sa.String(length=64), nullable=False),
            sa.Column(
                "SLC_Review_Status",
                sa.String(length=50),
                nullable=False,
                server_default="new",
            ),
            sa.Column(
                "First_Seen_At",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "Last_Seen_At",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "Source_Type", "Source_Id", name="uq_harvested_event_source"
            ),
        )
        op.create_index(
            "ix_harvested_events_SLC_Review_Status_Event_Start",
            "harvested_events",
            ["SLC_Review_Status", "Event_Start"],
        )
        op.create_index(
            "ix_harvested_events_Event_Start",
            "harvested_events",
            ["Event_Start"],
        )

    rows = [
        {
            "Value_Group": "SLC_Review_Status",
            "Code": "new",
            "Label": "New",
            "Display_Order": 10,
            "Is_Active": True,
            "Visibility_Role": "slc",
            "Description": "Harvested from an external calendar and awaiting SLC review.",
        },
        {
            "Value_Group": "SLC_Review_Status",
            "Code": "flagged",
            "Label": "Flagged for SLC",
            "Display_Order": 20,
            "Is_Active": True,
            "Visibility_Role": "slc",
            "Description": "Marked relevant to the Senior Leadership Council.",
        },
        {
            "Value_Group": "SLC_Review_Status",
            "Code": "dismissed",
            "Label": "Dismissed",
            "Display_Order": 30,
            "Is_Active": True,
            "Visibility_Role": "slc",
            "Description": "Reviewed and judged not relevant to the Senior Leadership Council.",
        },
    ]

    for row in rows:
        existing = bind.execute(
            sa.text(
                'SELECT "Id" FROM allowed_values '
                'WHERE "Value_Group" = :value_group AND "Code" = :code'
            ),
            {"value_group": row["Value_Group"], "code": row["Code"]},
        ).scalar_one_or_none()
        if existing:
            bind.execute(
                sa.text(
                    'UPDATE allowed_values '
                    'SET "Label" = :label, "Display_Order" = :display_order, '
                    '"Is_Active" = :is_active, "Visibility_Role" = :visibility_role, '
                    '"Description" = :description '
                    'WHERE "Value_Group" = :value_group AND "Code" = :code'
                ),
                {
                    "label": row["Label"],
                    "display_order": row["Display_Order"],
                    "is_active": row["Is_Active"],
                    "visibility_role": row["Visibility_Role"],
                    "description": row["Description"],
                    "value_group": row["Value_Group"],
                    "code": row["Code"],
                },
            )
            continue

        bind.execute(
            sa.text(
                'INSERT INTO allowed_values '
                '("Id", "Value_Group", "Code", "Label", "Display_Order", "Is_Active", '
                '"Visibility_Role", "Description") '
                'VALUES (:Id, :Value_Group, :Code, :Label, :Display_Order, :Is_Active, '
                ':Visibility_Role, :Description)'
            ),
            {"Id": str(uuid.uuid4()), **row},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            "DELETE FROM allowed_values WHERE \"Value_Group\" = 'SLC_Review_Status'"
        )
    )
    op.drop_index("ix_harvested_events_Event_Start", table_name="harvested_events")
    op.drop_index(
        "ix_harvested_events_SLC_Review_Status_Event_Start",
        table_name="harvested_events",
    )
    op.drop_table("harvested_events")
