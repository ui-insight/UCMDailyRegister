"""add submission listing indexes

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f7
Create Date: 2026-04-28 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_INDEXES: list[tuple[str, str, list[str]]] = [
    ("submissions", "ix_submissions_Status_Created_At", ["Status", "Created_At"]),
    ("submissions", "ix_submissions_Category_Created_At", ["Category", "Created_At"]),
    (
        "submissions",
        "ix_submissions_Target_Newsletter_Created_At",
        ["Target_Newsletter", "Created_At"],
    ),
    (
        "submissions",
        "ix_submissions_Show_In_SLC_Calendar_Created_At",
        ["Show_In_SLC_Calendar", "Created_At"],
    ),
    (
        "submission_schedule_requests",
        "ix_submission_schedule_requests_Requested_Date",
        ["Requested_Date"],
    ),
    (
        "submission_schedule_requests",
        "ix_submission_schedule_requests_Second_Requested_Date",
        ["Second_Requested_Date"],
    ),
    (
        "submission_schedule_requests",
        "ix_submission_schedule_requests_Recurrence_End_Date",
        ["Recurrence_End_Date"],
    ),
    (
        "submission_schedule_requests",
        "ix_submission_schedule_requests_Recurrence_Type",
        ["Recurrence_Type"],
    ),
]


def _existing_index_names(table: str) -> set[str]:
    return {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)
    }


def upgrade() -> None:
    for table, index_name, column_names in TABLE_INDEXES:
        if index_name in _existing_index_names(table):
            continue
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_index(index_name, column_names, unique=False)


def downgrade() -> None:
    for table, index_name, _column_names in reversed(TABLE_INDEXES):
        if index_name not in _existing_index_names(table):
            continue
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(index_name)
