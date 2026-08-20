"""place the completed Jobs workflow at the bottom of TDR

Revision ID: b5d7f9a1c3e4
Revises: a4c6e8f0b2d3
Create Date: 2026-08-19 16:00:00.000000

Issue #197 requires Job Opportunities to be a dedicated section at the bottom
of The Daily Register. The section already exists, so this focused data
migration updates only its order and provider-neutral description. It is
idempotent and leaves staff-created sections untouched.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b5d7f9a1c3e4"
down_revision: str | Sequence[str] | None = "a4c6e8f0b2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JOB_SECTION_DISPLAY_ORDER = 11
JOB_SECTION_DESCRIPTION = (
    "Jobs posted for two weeks from the official U of I jobs source. Can repost "
    "after two-week removal. Newest at top. Must be listed with HR."
)


newsletter_sections = sa.table(
    "newsletter_sections",
    sa.column("Newsletter_Type", sa.String(50)),
    sa.column("Slug", sa.String(255)),
    sa.column("Display_Order", sa.Integer),
    sa.column("Description", sa.Text),
)


def _apply_jobs_section_update(connection: sa.Connection) -> None:
    connection.execute(
        newsletter_sections.update()
        .where(
            newsletter_sections.c.Newsletter_Type == "tdr",
            newsletter_sections.c.Slug == "job-opportunities",
        )
        .values(
            Display_Order=JOB_SECTION_DISPLAY_ORDER,
            Description=JOB_SECTION_DESCRIPTION,
        )
    )


def upgrade() -> None:
    _apply_jobs_section_update(op.get_bind())


def downgrade() -> None:
    # Staff may reorder sections after deployment; do not overwrite that choice.
    pass
