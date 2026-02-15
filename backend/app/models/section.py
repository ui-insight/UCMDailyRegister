"""Newsletter section definitions for the UCM Newsletter Builder.

Each newsletter type (TDR and My UI) is divided into named sections such as
"Announcements," "Kudos," "Job Opportunities," and so on. The NewsletterSection
model defines the catalog of available sections, their display order, and
whether they require an accompanying image (with specified dimensions).

Sections are referenced by NewsletterItem rows to place submissions into the
correct area of the built newsletter. A unique constraint on
(Newsletter_Type, Slug) prevents duplicate section slugs within the same
newsletter type. The Is_Active flag allows sections to be retired without
deleting historical data.

Newsletter_Type values are governed by the AllowedValue table rather than
hard-coded enums.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsletterSection(Base):
    """A named section within a newsletter type, defining layout slots for submissions."""

    __tablename__ = "newsletter_sections"

    __table_args__ = (
        sa.UniqueConstraint("Newsletter_Type", "Slug", name="uq_section_type_slug"),
    )

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Newsletter_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Slug: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Display_Order: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    Description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Requires_Image: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    Image_Dimensions: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    Is_Active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
