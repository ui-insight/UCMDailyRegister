"""retire employee announcements from the public form; rename Employee News

Revision ID: f1b3d5e7a9c2
Revises: e7a9c1d3f5b8
Create Date: 2026-11-04 16:00:00.000000

UCM decided (#441) to retire the public "Employee (Faculty/Staff)" option and
rename Faculty/Staff to "Employee News (Faculty/Staff)". Employee
announcements are written by UCM, so the employee_announcement code stays
for staff and keeps routing to the Employee Announcements section. Stored
codes are unchanged, so earlier submissions stay readable.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f1b3d5e7a9c2"
down_revision: str | Sequence[str] | None = "e7a9c1d3f5b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CATEGORY_UPDATES = {
    "faculty_staff": {
        "Label": "Employee News (Faculty/Staff)",
        "Description": "News and announcements for faculty and staff",
        "Display_Order": 0,
        "Visibility_Role": "public",
    },
    "employee_announcement": {
        "Label": "Employee Announcement (UCM)",
        "Description": "Announcements UCM writes for all employees",
        "Display_Order": 10,
        "Visibility_Role": "staff",
    },
}

allowed_values = sa.table(
    "allowed_values",
    sa.column("Value_Group", sa.String(100)),
    sa.column("Code", sa.String(100)),
    sa.column("Label", sa.String(255)),
    sa.column("Description", sa.Text),
    sa.column("Display_Order", sa.Integer),
    sa.column("Visibility_Role", sa.String(50)),
)


def apply_category_updates(connection: sa.Connection) -> None:
    for code, values in CATEGORY_UPDATES.items():
        connection.execute(
            allowed_values.update()
            .where(
                allowed_values.c.Value_Group == "Submission_Category",
                allowed_values.c.Code == code,
            )
            .values(**values)
        )


def upgrade() -> None:
    apply_category_updates(op.get_bind())


def downgrade() -> None:
    # Vocabulary wording and visibility are owner decisions; not reverted.
    pass
