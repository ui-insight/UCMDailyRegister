"""add_slc_calendar_fields_to_submissions

Revision ID: a1b2c3d4e5f7
Revises: 67a4bd17e12f
Create Date: 2026-04-19 11:00:00.000000

"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "67a4bd17e12f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("submissions")}

    with op.batch_alter_table("submissions", schema=None) as batch_op:
        if "Show_In_SLC_Calendar" not in columns:
            batch_op.add_column(
                sa.Column(
                    "Show_In_SLC_Calendar",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        if "Event_Classification" not in columns:
            batch_op.add_column(
                sa.Column(
                    "Event_Classification",
                    sa.String(length=50),
                    nullable=True,
                )
            )

    rows = [
        {
            "Value_Group": "Event_Classification",
            "Code": "strategic",
            "Label": "Strategic Event",
            "Display_Order": 10,
            "Is_Active": True,
            "Visibility_Role": "staff",
            "Description": (
                "Advances university priorities, relationships, operations, "
                "or institutional goals."
            ),
        },
        {
            "Value_Group": "Event_Classification",
            "Code": "signature",
            "Label": "Signature Event",
            "Display_Order": 20,
            "Is_Active": True,
            "Visibility_Role": "staff",
            "Description": (
                "Highly visible, public-facing event that represents the "
                "university and shapes campus or community perception."
            ),
        },
        {
            "Value_Group": "Submission_Category",
            "Code": "slc_event",
            "Label": "SLC Calendar Event",
            "Display_Order": 50,
            "Is_Active": True,
            "Visibility_Role": "slc",
            "Description": (
                "Event intended for the Senior Leadership Council calendar, "
                "submitted via Auxiliary Services' vetting workflow."
            ),
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
            "DELETE FROM allowed_values "
            "WHERE \"Value_Group\" = 'Event_Classification' "
            "AND \"Code\" IN ('strategic', 'signature')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM allowed_values "
            "WHERE \"Value_Group\" = 'Submission_Category' "
            "AND \"Code\" = 'slc_event'"
        )
    )
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_column("Event_Classification")
        batch_op.drop_column("Show_In_SLC_Calendar")
