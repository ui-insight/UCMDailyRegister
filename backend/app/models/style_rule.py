"""Style rule definitions for the UCM Newsletter Builder.

Style rules encode the UCM writing-guide requirements that the AI editing
pipeline enforces when revising submissions. Each rule belongs to a Rule_Set
(shared across both newsletters, or specific to TDR or My UI), a Category
grouping (e.g., "punctuation," "capitalization," "links"), and carries a
human-readable Rule_Text that is injected into the LLM system prompt.

The Severity column (error, warning, info) tells the AI how strongly to
enforce the rule and how prominently to flag violations in its structured
output. The Is_Active flag lets editors temporarily disable rules without
deleting them.

Rule_Set and Severity values are governed by the AllowedValue table rather
than hard-coded enums.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StyleRule(Base):
    """A single writing-style rule enforced by the AI editing pipeline."""

    __tablename__ = "style_rules"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Rule_Set: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Category: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Rule_Key: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Rule_Text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Is_Active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    Severity: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="warning")
