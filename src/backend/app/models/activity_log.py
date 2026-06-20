"""
ActivityLog model — audit trail for user actions across the application.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database import Base


class ActivityLog(Base):
    """Audit log entry for user actions (login, generation, download, etc.)."""

    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g. "login", "generate"
    module: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g. "auth", "generation"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    def __repr__(self) -> str:
        return f"<ActivityLog action={self.action} user_id={self.user_id}>"
