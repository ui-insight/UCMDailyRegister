import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StyleRule(Base):
    __tablename__ = "style_rules"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rule_set: Mapped[str] = mapped_column(
        sa.Enum("shared", "tdr", "myui", name="rule_set", native_enum=False),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    rule_key: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    rule_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    severity: Mapped[str] = mapped_column(
        sa.Enum("error", "warning", "info", name="rule_severity", native_enum=False),
        nullable=False,
        default="warning",
    )
