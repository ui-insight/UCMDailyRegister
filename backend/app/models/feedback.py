"""Product feedback captured from users inside the application.

Feedback records are operational support data for the UCM Daily Register
product itself. They let submitters, editors, and SLC users report bugs or
suggest improvements without needing a GitHub account or knowing where the
project tracker lives.

The model deliberately stores only lightweight diagnostic context about the
app surface where the report was filed. It does not collect submission body
text, submitter PII from newsletter records, editorial notes, or other content
payloads automatically. Staff can review these records and later attach a
GitHub issue URL once an item has been exported to the engineering tracker.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductFeedback(Base):
    """A bug report or feature idea submitted from the app UI."""

    __tablename__ = "product_feedback"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Feedback_Type: Mapped[str] = mapped_column(sa.String(20), nullable=False, index=True)
    Summary: Mapped[str] = mapped_column(sa.String(240), nullable=False)
    Details: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Contact_Email: Mapped[str | None] = mapped_column(sa.String(320), nullable=True)
    Submitter_Role: Mapped[str] = mapped_column(sa.String(20), nullable=False, index=True)
    Route: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    App_Environment: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Host: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Browser: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Viewport: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Status: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="new", index=True)
    GitHub_URL: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now(), index=True
    )
    Updated_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()
    )
