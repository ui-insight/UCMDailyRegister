"""renumber Builder section positions so no two items tie

Revision ID: c3f5a7e9b1d2
Revises: a8e4c2f6b1d9
Create Date: 2026-11-16 18:00:00.000000

Issue #509. Submissions (``newsletter_items``) and imported items
(``newsletter_external_items``) share one position sequence per newsletter
section, but several write paths gave items the same position: every import
into an empty section got 0, and assembly counted only submissions. The
Builder broke ties by headline and the Word export by table, so the two
could show different orders.

This data migration renumbers each section 0..n-1 in the order the Builder
showed: position, then headline as the browser's ``localeCompare`` orders
it (approximated here as case-insensitive, lowercase first on otherwise
equal text), then submissions before imported items, as the Builder listed
them. Id settles anything left. The application now keeps positions unique
on every write. Only ``Position`` changes. Downgrade is a no-op because the
old positions carried no extra meaning.
"""

from collections.abc import Sequence
from collections import defaultdict

from alembic import op
import sqlalchemy as sa


revision: str = "c3f5a7e9b1d2"
down_revision: str | Sequence[str] | None = "a8e4c2f6b1d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table(name: str) -> sa.TableClause:
    return sa.table(
        name,
        sa.column("Id", sa.String(36)),
        sa.column("Newsletter_Id", sa.String(36)),
        sa.column("Section_Id", sa.String(36)),
        sa.column("Position", sa.Integer),
        sa.column("Final_Headline", sa.Text),
    )


TABLES = (_table("newsletter_items"), _table("newsletter_external_items"))


def _builder_order(entry: tuple[int, str, int, str, sa.TableClause]) -> tuple:
    """Approximate the old Builder sort for tied positions (localeCompare)."""
    position, headline, table_rank, item_id, _table = entry
    return (position, headline.casefold(), headline.swapcase(), table_rank, item_id)


def upgrade() -> None:
    connection = op.get_bind()
    sections: dict[tuple[str, str], list[tuple[int, str, int, str, sa.TableClause]]] = defaultdict(list)
    for table_rank, table in enumerate(TABLES):
        rows = connection.execute(
            sa.select(
                table.c.Id,
                table.c.Newsletter_Id,
                table.c.Section_Id,
                table.c.Position,
                table.c.Final_Headline,
            )
        )
        for row in rows:
            sections[(row.Newsletter_Id, row.Section_Id)].append(
                (row.Position or 0, row.Final_Headline or "", table_rank, row.Id, table)
            )
    for items in sections.values():
        for index, (position, _headline, _rank, item_id, table) in enumerate(
            sorted(items, key=_builder_order)
        ):
            if position != index:
                connection.execute(
                    sa.update(table).where(table.c.Id == item_id).values(Position=index)
                )


def downgrade() -> None:
    pass
