"""
AIProviderLog model — tracks every AI API call for cost and performance monitoring.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database import Base


class AIProviderLog(Base):
    """Records each call to an AI provider (Gemini, Pollinations, SD, etc.)."""

    __tablename__ = "ai_provider_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    provider_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)  # analyze | generate_image

    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_time: Mapped[float | None] = mapped_column(Float, nullable=True)  # seconds
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success"
    )  # success | error | timeout
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    def __repr__(self) -> str:
        return f"<AIProviderLog provider={self.provider_name} status={self.status}>"
