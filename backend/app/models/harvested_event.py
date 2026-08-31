"""Harvested external calendar events for SLC triage.

A HarvestedEvent is a read-only copy of a single event occurrence pulled from
an external calendar feed — today, the University of Idaho's Trumba calendar
JSON feed. The harvest runs on demand (and later on a schedule) and upserts
rows keyed by (Source_Type, Source_Id), so re-harvesting never duplicates
events: unchanged events simply get their Last_Seen_At bumped, while events
whose upstream content changed are updated in place and get a new Content_Hash.

Unlike Submission, which stores event details as free text in Original_Body,
HarvestedEvent keeps structured fields (real start/end datetimes, location,
category path) because the data arrives structured from the feed. The shape
mirrors NewsletterExternalItem, the app's existing pattern for externally
sourced items. Trumba emits one feed entry per occurrence of a repeating
event, each with its own eventID; Series_Id records the shared seriesID so
occurrences of the same event can be grouped.

SLC_Review_Status drives the Senior Leadership Council triage workflow: every
harvested event starts as "new"; the SLC coordinator reviews the list and
marks events "flagged" (relevant to SLC) or "dismissed". The vocabulary is
governed by the AllowedValue table under the SLC_Review_Status group.

Flagging promotes the event onto the SLC calendar by creating an SLC-only
Submission (the same shape the workbook importer produces), and records that
provenance in Promoted_Submission_Id. The FK uses ON DELETE SET NULL so a
staff deletion of the promoted submission leaves the harvested event intact.

Ops_Review_Status drives a second, fully independent triage lens over the
same rows: Event Services reviews upcoming public events for operational
demands on their staff (catering, alcohol service, room setup, tabling,
outdoor space). Every harvested event starts as "new" on the ops lens; the
Event Services reviewer marks events "reviewed" or "dismissed". The two
lenses never read or write each other's status — the SLC coordinator and
Event Services triage the same events without collision. The vocabulary is
governed by the AllowedValue table under the Ops_Review_Status group.

Upstream_Changed_At powers the "changed upstream" badges on the triage page:
it is stamped when a re-harvest finds that a flagged event's upstream data
changed, was canceled, or disappeared from the feed while still in the feed's
coverage window. The coordinator clears it by acknowledging the change (or by
un-flagging); it is only ever set on flagged events, since only those carry a
promoted submission that could go stale.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.submission import Submission


class HarvestedEvent(Base):
    """A single event occurrence harvested from an external calendar feed."""

    __tablename__ = "harvested_events"
    __table_args__ = (
        sa.UniqueConstraint(
            "Source_Type", "Source_Id", name="uq_harvested_event_source"
        ),
        sa.Index(
            "ix_harvested_events_SLC_Review_Status_Event_Start",
            "SLC_Review_Status",
            "Event_Start",
        ),
        sa.Index(
            "ix_harvested_events_Ops_Review_Status_Event_Start",
            "Ops_Review_Status",
            "Event_Start",
        ),
        sa.Index("ix_harvested_events_Event_Start", "Event_Start"),
    )

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Source_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Source_Id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Series_Id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    Source_Url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Title: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Location: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    Event_Start: Mapped[datetime] = mapped_column(sa.DateTime, nullable=False)
    Event_End: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    All_Day: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    Category_Path: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    Is_Canceled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    Content_Hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    SLC_Review_Status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="new", server_default="new"
    )
    Ops_Review_Status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="new", server_default="new"
    )
    Upstream_Changed_At: Mapped[datetime | None] = mapped_column(
        sa.DateTime, nullable=True
    )
    Promoted_Submission_Id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey("submissions.Id", ondelete="SET NULL"),
        nullable=True,
    )
    First_Seen_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    Last_Seen_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )

    Promoted_Submission_Rel: Mapped["Submission | None"] = relationship(lazy="selectin")
