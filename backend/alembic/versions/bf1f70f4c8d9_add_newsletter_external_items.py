"""add_newsletter_external_items

Revision ID: bf1f70f4c8d9
Revises: 910c2f3c5db4
Create Date: 2026-03-19 07:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bf1f70f4c8d9"
down_revision: Union[str, Sequence[str], None] = "910c2f3c5db4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "newsletter_external_items",
        sa.Column("Id", sa.String(length=36), nullable=False),
        sa.Column("Newsletter_Id", sa.String(length=36), nullable=False),
        sa.Column("Section_Id", sa.String(length=36), nullable=False),
        sa.Column("Source_Type", sa.String(length=50), nullable=False),
        sa.Column("Source_Id", sa.String(length=255), nullable=False),
        sa.Column("Source_Url", sa.Text(), nullable=True),
        sa.Column("Event_Start", sa.DateTime(), nullable=True),
        sa.Column("Event_End", sa.DateTime(), nullable=True),
        sa.Column("Location", sa.String(length=255), nullable=True),
        sa.Column("Position", sa.Integer(), nullable=False),
        sa.Column("Final_Headline", sa.Text(), nullable=False),
        sa.Column("Final_Body", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["Newsletter_Id"], ["newsletters.Id"]),
        sa.ForeignKeyConstraint(["Section_Id"], ["newsletter_sections.Id"]),
        sa.PrimaryKeyConstraint("Id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("newsletter_external_items")
