import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.submission import Submission


class EditVersion(Base):
    __tablename__ = "edit_versions"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    submission_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("submissions.id"), nullable=False
    )
    version_type: Mapped[str] = mapped_column(
        sa.Enum(
            "original",
            "ai_suggested",
            "editor_final",
            name="version_type",
            native_enum=False,
        ),
        nullable=False,
    )
    headline: Mapped[str] = mapped_column(sa.Text, nullable=False)
    body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    headline_case: Mapped[str | None] = mapped_column(
        sa.Enum("sentence_case", "title_case", name="headline_case", native_enum=False),
        nullable=True,
    )
    flags: Mapped[str | None] = mapped_column(sa.JSON, nullable=True)
    changes_made: Mapped[str | None] = mapped_column(sa.JSON, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )

    submission: Mapped["Submission"] = relationship(back_populates="edit_versions")
