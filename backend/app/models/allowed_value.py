"""Allowed values for controlled vocabulary fields throughout the application.

The AllowedValue table provides a single, centralized location for all categorical
values used across the data model. Instead of hard-coding enums in SQLAlchemy models,
columns reference value groups in this table. This allows administrators to add,
rename, or deactivate values without code changes.

Value groups include Submission_Category, Newsletter_Type, Submission_Status,
Newsletter_Status, Version_Type, Headline_Case, Rule_Set, Severity, and Schedule_Mode.
Each value has a machine-readable Code, a human-readable Label, and optional Description.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AllowedValue(Base):
    """A single allowed value within a controlled vocabulary group.

    Unique constraint on (Value_Group, Code) ensures no duplicate codes within
    a group. Display_Order controls presentation ordering in UI dropdowns.
    """

    __tablename__ = "allowed_values"
    __table_args__ = (
        sa.UniqueConstraint("Value_Group", "Code", name="uq_allowed_value_group_code"),
    )

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Value_Group: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    Code: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Label: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Display_Order: Mapped[int] = mapped_column(sa.Integer, default=0)
    Is_Active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    Description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
