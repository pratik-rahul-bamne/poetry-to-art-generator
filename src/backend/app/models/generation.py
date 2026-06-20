"""
Generation model — tracks each AI artwork generation attempt.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base


class Generation(Base):
    """One artwork generation run linked to a poem."""

    __tablename__ = "generations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    poem_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("poems.id", ondelete="SET NULL"), nullable=True, index=True
    )

    image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    final_artwork_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    generation_time: Mapped[float | None] = mapped_column(Float, nullable=True)  # seconds
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | completed | failed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    poem: Mapped["Poem"] = relationship("Poem", back_populates="generations")  # noqa: F821
    downloads: Mapped[list["Download"]] = relationship(  # noqa: F821
        "Download", back_populates="generation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Generation id={self.id} status={self.status}>"
