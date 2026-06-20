"""
Generation Repository — database operations for the generations table.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.generation import Generation
from backend.app.models.download import Download
from backend.app.core.logger import get_logger

logger = get_logger("db")


class GenerationRepository:
    """Repository for Generation and Download model operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        poem_id: Optional[str] = None,
        image_prompt: Optional[str] = None,
        provider_used: Optional[str] = None,
    ) -> Generation:
        """Create a pending generation record."""
        gen = Generation(
            poem_id=poem_id,
            image_prompt=image_prompt,
            provider_used=provider_used,
            status="pending",
        )
        self.db.add(gen)
        self.db.commit()
        self.db.refresh(gen)
        return gen

    def update_completed(
        self,
        gen_id: str,
        image_url: str,
        final_artwork_url: str,
        generation_time: float,
    ) -> Optional[Generation]:
        """Mark a generation as completed with final URLs."""
        gen = self.db.query(Generation).filter(Generation.id == gen_id).first()
        if gen:
            gen.image_url = image_url
            gen.final_artwork_url = final_artwork_url
            gen.generation_time = generation_time
            gen.status = "completed"
            self.db.commit()
            self.db.refresh(gen)
        return gen

    def mark_failed(self, gen_id: str, error: str = "") -> None:
        """Mark a generation as failed."""
        self.db.query(Generation).filter(Generation.id == gen_id).update(
            {"status": "failed"}
        )
        self.db.commit()

    def get_recent(self, limit: int = 12) -> list[Generation]:
        """Return the most recent completed generations (for gallery)."""
        return (
            self.db.query(Generation)
            .filter(Generation.status == "completed")
            .order_by(Generation.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 20) -> tuple[list[Generation], int]:
        """Return generations linked to a specific user via the poems table."""
        from backend.app.models.poem import Poem
        q = (
            self.db.query(Generation)
            .join(Poem, Generation.poem_id == Poem.id)
            .filter(Poem.user_id == user_id)
        )
        total = q.count()
        items = q.order_by(Generation.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def count_all(self) -> int:
        return self.db.query(Generation).count()

    def count_by_provider(self) -> dict[str, int]:
        """Return generation counts grouped by provider."""
        rows = self.db.query(
            Generation.provider_used, Generation.id
        ).filter(Generation.provider_used.isnot(None)).all()
        counts: dict[str, int] = {}
        for row in rows:
            p = row[0] or "unknown"
            counts[p] = counts.get(p, 0) + 1
        return counts

    def record_download(
        self,
        generation_id: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> Download:
        """Record a download event."""
        dl = Download(
            generation_id=generation_id,
            ip_address=ip_address,
            device_info=device_info,
        )
        self.db.add(dl)
        self.db.commit()
        return dl

    def count_downloads(self) -> int:
        return self.db.query(Download).count()
