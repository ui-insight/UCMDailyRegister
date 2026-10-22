"""add_approved_and_source_versions

Records which revision staff approved (submissions.Approved_Version_Id) and
which revision each assembled newsletter item was copied from
(newsletter_items.Source_Version_Id).

Backfill:
- Approved or scheduled submissions point at their newest editor_final.
  Submissions approved without one (SLC imports) stay empty and publish
  their original text, as before.
- Newsletter items point at the revision of their submission whose headline
  and body match the item exactly, preferring the approved revision, then the
  newest. Items that match nothing stay empty ("assembled before tracking").

Revision ID: a1c3e5f7b9d2
Revises: f7c9e1b3d5a8
Create Date: 2026-10-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1c3e5f7b9d2"
down_revision: Union[str, Sequence[str], None] = "f7c9e1b3d5a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BACKFILL_APPROVED = """
UPDATE submissions
SET "Approved_Version_Id" = (
    SELECT v."Id" FROM edit_versions v
    WHERE v."Submission_Id" = submissions."Id"
      AND v."Version_Type" = 'editor_final'
    ORDER BY v."Created_At" DESC, v."Id" DESC
    LIMIT 1
)
WHERE "Status" IN ('approved', 'scheduled')
  AND "Approved_Version_Id" IS NULL
"""

BACKFILL_SOURCE = """
UPDATE newsletter_items
SET "Source_Version_Id" = (
    SELECT v."Id" FROM edit_versions v
    JOIN submissions s ON s."Id" = v."Submission_Id"
    WHERE v."Submission_Id" = newsletter_items."Submission_Id"
      AND v."Headline" = newsletter_items."Final_Headline"
      AND v."Body" = newsletter_items."Final_Body"
    ORDER BY CASE WHEN v."Id" = s."Approved_Version_Id" THEN 0 ELSE 1 END,
             v."Created_At" DESC, v."Id" DESC
    LIMIT 1
)
WHERE "Source_Version_Id" IS NULL
"""


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    submission_columns = {c["name"] for c in inspector.get_columns("submissions")}
    if "Approved_Version_Id" not in submission_columns:
        with op.batch_alter_table("submissions", schema=None) as batch_op:
            batch_op.add_column(sa.Column("Approved_Version_Id", sa.String(36), nullable=True))
            batch_op.create_foreign_key(
                "fk_submissions_Approved_Version_Id",
                "edit_versions",
                ["Approved_Version_Id"],
                ["Id"],
                ondelete="SET NULL",
            )

    item_columns = {c["name"] for c in inspector.get_columns("newsletter_items")}
    if "Source_Version_Id" not in item_columns:
        with op.batch_alter_table("newsletter_items", schema=None) as batch_op:
            batch_op.add_column(sa.Column("Source_Version_Id", sa.String(36), nullable=True))
            batch_op.create_foreign_key(
                "fk_newsletter_items_Source_Version_Id",
                "edit_versions",
                ["Source_Version_Id"],
                ["Id"],
                ondelete="SET NULL",
            )

    bind.execute(sa.text(BACKFILL_APPROVED))
    bind.execute(sa.text(BACKFILL_SOURCE))
    approved = bind.execute(
        sa.text('SELECT COUNT(*) FROM submissions WHERE "Approved_Version_Id" IS NOT NULL')
    ).scalar()
    items, sourced = bind.execute(
        sa.text('SELECT COUNT(*), COUNT("Source_Version_Id") FROM newsletter_items')
    ).one()
    print(
        f"[a1c3e5f7b9d2] {approved} submissions have an approved revision; "
        f"{sourced} of {items} newsletter items have a source revision"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("newsletter_items", schema=None) as batch_op:
        batch_op.drop_constraint("fk_newsletter_items_Source_Version_Id", type_="foreignkey")
        batch_op.drop_column("Source_Version_Id")
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_submissions_Approved_Version_Id", type_="foreignkey")
        batch_op.drop_column("Approved_Version_Id")
