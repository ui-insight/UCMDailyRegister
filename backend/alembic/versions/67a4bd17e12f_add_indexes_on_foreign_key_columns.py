"""add indexes on foreign key columns

Revision ID: 67a4bd17e12f
Revises: 792c4cd01807
Create Date: 2026-04-17 14:08:25.645062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "67a4bd17e12f"
down_revision: Union[str, Sequence[str], None] = "792c4cd01807"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Indexes added by this migration, grouped by table.
# Some long-running deployments already have these indexes from an earlier
# Base.metadata.create_all() bootstrap (models declare index=True on FK
# columns). The guarded helpers below let this migration replay safely
# against drifted DBs.
TABLE_INDEXES: list[tuple[str, str, str]] = [
    ("edit_versions", "ix_edit_versions_Submission_Id", "Submission_Id"),
    ("newsletter_external_items", "ix_newsletter_external_items_Newsletter_Id", "Newsletter_Id"),
    ("newsletter_external_items", "ix_newsletter_external_items_Section_Id", "Section_Id"),
    ("newsletter_items", "ix_newsletter_items_Newsletter_Id", "Newsletter_Id"),
    ("newsletter_items", "ix_newsletter_items_Section_Id", "Section_Id"),
    ("newsletter_items", "ix_newsletter_items_Submission_Id", "Submission_Id"),
    ("recurring_message_issue_overrides", "ix_recurring_message_issue_overrides_Newsletter_Id", "Newsletter_Id"),
    ("recurring_message_issue_overrides", "ix_recurring_message_issue_overrides_Recurring_Message_Id", "Recurring_Message_Id"),
    ("recurring_messages", "ix_recurring_messages_Section_Id", "Section_Id"),
    ("submission_links", "ix_submission_links_Submission_Id", "Submission_Id"),
    ("submission_schedule_requests", "ix_submission_schedule_requests_Submission_Id", "Submission_Id"),
]


def _existing_index_names(table: str) -> set[str]:
    return {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)
    }


def upgrade() -> None:
    for table, index_name, column_name in TABLE_INDEXES:
        if index_name in _existing_index_names(table):
            continue
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_index(index_name, [column_name], unique=False)


def downgrade() -> None:
    for table, index_name, _column_name in reversed(TABLE_INDEXES):
        if index_name not in _existing_index_names(table):
            continue
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(index_name)
