"""add_edition_edit_tracking

Tracks whether staff changed an edition item's copy in the Builder
(newsletter_items.Edition_Edited) and which newer approved revision they
reviewed and chose not to apply (newsletter_items.Upstream_Reviewed_Version_Id).

Backfill: items with no source revision are marked edited. Their copy matched
no saved revision when tracking began, so it was written or changed in the
edition.

Revision ID: d4f6a8c0e2b5
Revises: a1c3e5f7b9d2
Create Date: 2026-10-22 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4f6a8c0e2b5"
down_revision: Union[str, Sequence[str], None] = "a1c3e5f7b9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("newsletter_items")}

    with op.batch_alter_table("newsletter_items", schema=None) as batch_op:
        if "Edition_Edited" not in columns:
            batch_op.add_column(
                sa.Column("Edition_Edited", sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if "Upstream_Reviewed_Version_Id" not in columns:
            batch_op.add_column(
                sa.Column("Upstream_Reviewed_Version_Id", sa.String(36), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_newsletter_items_Upstream_Reviewed_Version_Id",
                "edit_versions",
                ["Upstream_Reviewed_Version_Id"],
                ["Id"],
                ondelete="SET NULL",
            )

    bind.execute(
        sa.text(
            'UPDATE newsletter_items SET "Edition_Edited" = true '
            'WHERE "Source_Version_Id" IS NULL'
        )
    )
    edited, items = bind.execute(
        sa.text(
            'SELECT SUM(CASE WHEN "Edition_Edited" THEN 1 ELSE 0 END), COUNT(*) '
            "FROM newsletter_items"
        )
    ).one()
    print(f"[d4f6a8c0e2b5] {edited or 0} of {items} newsletter items marked edition-edited")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("newsletter_items", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_newsletter_items_Upstream_Reviewed_Version_Id", type_="foreignkey"
        )
        batch_op.drop_column("Upstream_Reviewed_Version_Id")
        batch_op.drop_column("Edition_Edited")
