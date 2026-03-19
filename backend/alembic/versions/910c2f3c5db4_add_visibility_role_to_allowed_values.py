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
    with op.batch_alter_table("allowed_values", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "Visibility_Role",
                sa.String(length=20),
                nullable=False,
                server_default="public",
            )
        )

    allowed_values = sa.table(
        "allowed_values",
        sa.column("Id", sa.String(length=36)),
        sa.column("Value_Group", sa.String(length=100)),
        sa.column("Code", sa.String(length=100)),
        sa.column("Label", sa.String(length=255)),
        sa.column("Display_Order", sa.Integer()),
        sa.column("Is_Active", sa.Boolean()),
        sa.column("Visibility_Role", sa.String(length=20)),
        sa.column("Description", sa.Text()),
    )
    op.bulk_insert(
        allowed_values,
        [
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
        ],
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
