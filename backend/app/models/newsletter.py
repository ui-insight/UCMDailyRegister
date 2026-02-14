import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.section import NewsletterSection

if TYPE_CHECKING:
    from app.models.submission import Submission


class Newsletter(Base):
    __tablename__ = "newsletters"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    newsletter_type: Mapped[str] = mapped_column(
        sa.Enum("tdr", "myui", name="newsletter_type_nl", native_enum=False),
        nullable=False,
    )
    publish_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    status: Mapped[str] = mapped_column(
        sa.Enum(
            "draft",
            "in_progress",
            "ready_for_review",
            "submitted",
            "published",
            name="newsletter_status",
            native_enum=False,
        ),
        nullable=False,
        default="draft",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()
    )

    items: Mapped[list["NewsletterItem"]] = relationship(
        back_populates="newsletter", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.UniqueConstraint("newsletter_type", "publish_date", name="uq_newsletter_type_date"),
    )


class NewsletterItem(Base):
    __tablename__ = "newsletter_items"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    newsletter_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("newsletters.id"), nullable=False
    )
    submission_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("submissions.id"), nullable=False
    )
    section_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("newsletter_sections.id"), nullable=False
    )
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    final_headline: Mapped[str] = mapped_column(sa.Text, nullable=False)
    final_body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    run_number: Mapped[int] = mapped_column(sa.Integer, default=1)

    newsletter: Mapped["Newsletter"] = relationship(back_populates="items")
    submission: Mapped["Submission"] = relationship()
    section: Mapped["NewsletterSection"] = relationship()
