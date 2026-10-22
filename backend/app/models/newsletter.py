"""Newsletter assembly models for the UCM Newsletter Builder.

A Newsletter represents a single edition of either The Daily Register (TDR) or
My UI, identified by its type and publish date. The editor dashboard assembles
a newsletter by placing approved submissions into section slots, producing an
ordered collection of NewsletterItem rows.

Each NewsletterItem binds a submission to a specific section within the
newsletter, records its final (possibly editor-tweaked) headline and body, and
tracks its position within the section and its run number (how many times the
item has appeared in previous editions).

Source_Version_Id records which EditVersion an assembled item's text was
copied from, so staff can see exactly which approved revision an edition
carries. It is empty for items added with hand-supplied text and for items
whose text matched no revision when tracking began.

Edition_Edited marks copy staff changed in the Builder; reassembly never
overwrites an item, so those edits always survive. When the submission's
approved revision later differs from Source_Version_Id, the item reports an
Upstream_Change so staff can deliberately refresh the copy or keep it;
keeping records Upstream_Reviewed_Version_Id so that revision stops being
flagged. See app.services.editorial_content.

Newsletter_Type and Status values are governed by the AllowedValue table rather
than hard-coded enums. A unique constraint on (Newsletter_Type, Publish_Date)
prevents duplicate editions for the same day and newsletter.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.body_links import LinkFinding, check_body

if TYPE_CHECKING:
    from app.models.edit_history import EditVersion
    from app.models.section import NewsletterSection
    from app.models.submission import Submission


class Newsletter(Base):
    """A single edition of a UCM newsletter (TDR or My UI) for a specific publish date."""

    __tablename__ = "newsletters"

    __table_args__ = (
        sa.UniqueConstraint("Newsletter_Type", "Publish_Date", name="uq_newsletter_type_date"),
    )

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Newsletter_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Publish_Date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    Status: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="draft")
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    Updated_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()
    )

    Items: Mapped[list["NewsletterItem"]] = relationship(
        back_populates="Newsletter_Rel", cascade="all, delete-orphan", lazy="selectin"
    )
    External_Items: Mapped[list["NewsletterExternalItem"]] = relationship(
        back_populates="Newsletter_Rel", cascade="all, delete-orphan", lazy="selectin"
    )


class NewsletterItem(Base):
    """A placed submission within a newsletter edition, assigned to a section and position."""

    __tablename__ = "newsletter_items"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Newsletter_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("newsletters.Id"), nullable=False, index=True
    )
    Submission_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("submissions.Id"), nullable=False, index=True
    )
    Section_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("newsletter_sections.Id"), nullable=False, index=True
    )
    Position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    Final_Headline: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Final_Body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Run_Number: Mapped[int] = mapped_column(sa.Integer, default=1)
    # Set when staff move the item to a different section; re-assembly then
    # leaves the placement alone instead of re-syncing it to the category map.
    Manually_Placed: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    Source_Version_Id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey(
            "edit_versions.Id", name="fk_newsletter_items_Source_Version_Id", ondelete="SET NULL"
        ),
        nullable=True,
    )
    Edition_Edited: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    Upstream_Reviewed_Version_Id: Mapped[str | None] = mapped_column(
        sa.String(36),
        sa.ForeignKey(
            "edit_versions.Id",
            name="fk_newsletter_items_Upstream_Reviewed_Version_Id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    Newsletter_Rel: Mapped["Newsletter"] = relationship(
        back_populates="Items", lazy="selectin"
    )
    Submission_Rel: Mapped["Submission"] = relationship(lazy="selectin")
    Section_Rel: Mapped["NewsletterSection"] = relationship(lazy="selectin")

    @property
    def Link_Findings(self) -> list[LinkFinding]:
        """Link problems in this item's copy, including submitted links it lost."""
        submitted: list[str] = []
        state = sa.inspect(self)
        if "Submission_Rel" not in state.unloaded and self.Submission_Rel is not None:
            if "Links" not in sa.inspect(self.Submission_Rel).unloaded:
                submitted = [link.Url for link in self.Submission_Rel.Links]
        return check_body(self.Final_Body, submitted)

    @property
    def Upstream_Change(self) -> "EditVersion | None":
        """The newer approved revision this edition's copy does not reflect, if any."""
        from app.services.editorial_content import upstream_change

        return upstream_change(self)


class NewsletterExternalItem(Base):
    """A placed non-submission item imported from an external source such as a calendar."""

    __tablename__ = "newsletter_external_items"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Newsletter_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("newsletters.Id"), nullable=False, index=True
    )
    Section_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("newsletter_sections.Id"), nullable=False, index=True
    )
    Source_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Source_Id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Source_Url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Event_Start: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    Event_End: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    Location: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    Position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    Final_Headline: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Final_Body: Mapped[str] = mapped_column(sa.Text, nullable=False)

    Newsletter_Rel: Mapped["Newsletter"] = relationship(
        back_populates="External_Items", lazy="selectin"
    )
    Section_Rel: Mapped["NewsletterSection"] = relationship(lazy="selectin")

    @property
    def Link_Findings(self) -> list[LinkFinding]:
        """Link problems in this item's copy."""
        return check_body(self.Final_Body)
