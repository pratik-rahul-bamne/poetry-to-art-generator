"""
Download model — records each time a final artwork is downloaded.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base


class Download(Base):
    """Tracks every image download event for analytics."""

    __tablename__ = "downloads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    generation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("generations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_info: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship
    generation: Mapped["Generation"] = relationship("Generation", back_populates="downloads")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Download id={self.id} generation_id={self.generation_id}>"
