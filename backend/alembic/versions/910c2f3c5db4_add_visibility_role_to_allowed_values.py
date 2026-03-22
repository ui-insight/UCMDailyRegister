"""add_visibility_role_to_allowed_values

Revision ID: 910c2f3c5db4
Revises: 4cca2368e0ff
Create Date: 2026-03-19 06:40:00.000000

"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "910c2f3c5db4"
down_revision: Union[str, Sequence[str], None] = "4cca2368e0ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("allowed_values")}

    if "Visibility_Role" not in columns:
        with op.batch_alter_table("allowed_values", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "Visibility_Role",
                    sa.String(length=20),
                    nullable=False,
                    server_default="public",
                )
            )

    rows = [
        {
            "Id": str(uuid.uuid4()),
            "Value_Group": "Submission_Category",
            "Code": "news_release",
            "Label": "News Release",
            "Display_Order": 8,
            "Is_Active": True,
            "Visibility_Role": "staff",
            "Description": "Official news release prepared by UCM staff",
        },
        {
            "Id": str(uuid.uuid4()),
            "Value_Group": "Submission_Category",
            "Code": "ucm_feature_story",
            "Label": "UCM Feature Story",
            "Display_Order": 9,
            "Is_Active": True,
            "Visibility_Role": "staff",
            "Description": "Feature-story intake reserved for UCM staff",
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
                '("Id", "Value_Group", "Code", "Label", "Display_Order", "Is_Active", "Visibility_Role", "Description") '
                'VALUES (:Id, :Value_Group, :Code, :Label, :Display_Order, :Is_Active, :Visibility_Role, :Description)'
            ),
            row,
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            "DELETE FROM allowed_values "
            "WHERE Value_Group = 'Submission_Category' "
            "AND Code IN ('news_release', 'ucm_feature_story')"
        )
    )
    with op.batch_alter_table("allowed_values", schema=None) as batch_op:
        batch_op.drop_column("Visibility_Role")
