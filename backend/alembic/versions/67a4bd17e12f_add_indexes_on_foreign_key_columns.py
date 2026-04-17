"""add indexes on foreign key columns

Revision ID: 67a4bd17e12f
Revises: d2e3f4a5b6c7
Create Date: 2026-04-17 14:08:25.645062

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "67a4bd17e12f"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("edit_versions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_edit_versions_Submission_Id"), ["Submission_Id"], unique=False
        )

    with op.batch_alter_table("newsletter_external_items", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_newsletter_external_items_Newsletter_Id"),
            ["Newsletter_Id"], unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_newsletter_external_items_Section_Id"),
            ["Section_Id"], unique=False,
        )

    with op.batch_alter_table("newsletter_items", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_newsletter_items_Newsletter_Id"),
            ["Newsletter_Id"], unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_newsletter_items_Section_Id"),
            ["Section_Id"], unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_newsletter_items_Submission_Id"),
            ["Submission_Id"], unique=False,
        )

    with op.batch_alter_table("recurring_message_issue_overrides", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_recurring_message_issue_overrides_Newsletter_Id"),
            ["Newsletter_Id"], unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_recurring_message_issue_overrides_Recurring_Message_Id"),
            ["Recurring_Message_Id"], unique=False,
        )

    with op.batch_alter_table("recurring_messages", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_recurring_messages_Section_Id"),
            ["Section_Id"], unique=False,
        )

    with op.batch_alter_table("submission_links", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_submission_links_Submission_Id"),
            ["Submission_Id"], unique=False,
        )

    with op.batch_alter_table("submission_schedule_requests", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_submission_schedule_requests_Submission_Id"),
            ["Submission_Id"], unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("submission_schedule_requests", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_submission_schedule_requests_Submission_Id"))

    with op.batch_alter_table("submission_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_submission_links_Submission_Id"))

    with op.batch_alter_table("recurring_messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recurring_messages_Section_Id"))

    with op.batch_alter_table("recurring_message_issue_overrides", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recurring_message_issue_overrides_Recurring_Message_Id"))
        batch_op.drop_index(batch_op.f("ix_recurring_message_issue_overrides_Newsletter_Id"))

    with op.batch_alter_table("newsletter_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_newsletter_items_Submission_Id"))
        batch_op.drop_index(batch_op.f("ix_newsletter_items_Section_Id"))
        batch_op.drop_index(batch_op.f("ix_newsletter_items_Newsletter_Id"))

    with op.batch_alter_table("newsletter_external_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_newsletter_external_items_Section_Id"))
        batch_op.drop_index(batch_op.f("ix_newsletter_external_items_Newsletter_Id"))

    with op.batch_alter_table("edit_versions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_edit_versions_Submission_Id"))
