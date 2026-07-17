"""restore clobbered submission originals

Finalizing an edit used to overwrite Submission.Original_Headline/Original_Body
with the editor's text. Where an 'original' EditVersion snapshot exists (created
by the AI edit pipeline before the overwrite happened), restore the submission's
original fields from the earliest such snapshot.

Revision ID: b8d4e6f1a2c3
Revises: 7d3e5f9a1b2c
Create Date: 2026-07-17 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8d4e6f1a2c3"
down_revision: Union[str, Sequence[str], None] = "7d3e5f9a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT ev."Submission_Id", ev."Headline", ev."Body"
            FROM edit_versions ev
            WHERE ev."Version_Type" = 'original'
              AND ev."Created_At" = (
                  SELECT MIN(ev2."Created_At")
                  FROM edit_versions ev2
                  WHERE ev2."Submission_Id" = ev."Submission_Id"
                    AND ev2."Version_Type" = 'original'
              )
            """
        )
    ).fetchall()

    for submission_id, headline, body in rows:
        bind.execute(
            sa.text(
                """
                UPDATE submissions
                SET "Original_Headline" = :headline, "Original_Body" = :body
                WHERE "Id" = :submission_id
                  AND ("Original_Headline" != :headline OR "Original_Body" != :body)
                """
            ),
            {"headline": headline, "body": body, "submission_id": submission_id},
        )


def downgrade() -> None:
    # The overwritten values are not recoverable once restored; nothing to undo.
    pass
