import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsletterSection(Base):
    __tablename__ = "newsletter_sections"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    newsletter_type: Mapped[str] = mapped_column(
        sa.Enum("tdr", "myui", name="newsletter_type_section", native_enum=False),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    requires_image: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    image_dimensions: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    __table_args__ = (
        sa.UniqueConstraint("newsletter_type", "slug", name="uq_section_type_slug"),
    )
