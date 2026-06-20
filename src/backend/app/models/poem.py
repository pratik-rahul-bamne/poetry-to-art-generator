"""
Poem model — stores user-submitted poems with extracted metadata.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base


class Poem(Base):
    """A poem submitted by a user (or guest if user_id is None)."""

    __tablename__ = "poems"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    poem_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # AI-extracted metadata
    theme: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mood: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    generations: Mapped[list["Generation"]] = relationship(  # noqa: F821
        "Generation", back_populates="poem", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Poem id={self.id} theme={self.theme}>"
