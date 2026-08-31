"""AI-suggested operational service needs for harvested calendar events.

An OpsNeedAssessment is one suggested operational need for one harvested
event: catering, alcohol service, room setup, tabling, or outdoor space
(the vocabulary lives in the AllowedValue table under Ops_Need_Type). The
Trumba feed carries no service metadata — the signal hides in free text
like "reception to follow" or "refreshments provided" — so an on-prem
MindRouter model reads each event's title, description, location, and
category and emits suggestions with a confidence level (Ops_Need_Confidence
vocabulary) and a one-line rationale quoting the event's own wording.

Assessments are produced by the classify-pending step that follows each
harvest apply. An event is classified at most once per content version:
HarvestedEvent.Ops_Assessed_Content_Hash records which Content_Hash the
current assessment saw, so unchanged events are never re-billed and events
whose upstream content changed are re-assessed on the next run. Re-assessing
replaces this event's suggestion rows wholesale (the verdict lifecycle that
will preserve staff judgments arrives with the confirm/reject slice).

Rows are children of their harvested event and disappear with it; nothing
else references them.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.harvested_event import HarvestedEvent


class OpsNeedAssessment(Base):
    """One AI-suggested operational need for one harvested event."""

    __tablename__ = "ops_need_assessments"
    __table_args__ = (
        sa.UniqueConstraint(
            "Harvested_Event_Id", "Need", name="uq_ops_need_assessment_event_need"
        ),
    )

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Harvested_Event_Id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("harvested_events.Id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    Need: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Confidence: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    Rationale: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )

    Harvested_Event_Rel: Mapped["HarvestedEvent"] = relationship(
        back_populates="Ops_Needs_Rel", lazy="selectin"
    )
