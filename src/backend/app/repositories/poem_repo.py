"""
Poem Repository — all database operations for the poems table.
"""

from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.poem import Poem
from backend.app.core.logger import get_logger

logger = get_logger("db")


class PoemRepository:
    """Repository for Poem model operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        poem_text: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        language: Optional[str] = None,
        theme: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> Poem:
        """Create and persist a poem."""
        poem = Poem(
            poem_text=poem_text,
            user_id=user_id,
            title=title,
            language=language,
            theme=theme,
            mood=mood,
        )
        self.db.add(poem)
        self.db.commit()
        self.db.refresh(poem)
        logger.info("Created poem id=%s user_id=%s", poem.id, user_id)
        return poem

    def get_by_id(self, poem_id: str) -> Optional[Poem]:
        return self.db.query(Poem).filter(Poem.id == poem_id).first()

    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 20) -> tuple[list[Poem], int]:
        """Return paginated poems for a specific user."""
        q = self.db.query(Poem).filter(Poem.user_id == user_id)
        total = q.count()
        items = q.order_by(Poem.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def delete(self, poem_id: str, user_id: str) -> bool:
        """Delete a poem (only if it belongs to the requesting user)."""
        poem = self.db.query(Poem).filter(
            Poem.id == poem_id, Poem.user_id == user_id
        ).first()
        if poem:
            self.db.delete(poem)
            self.db.commit()
            logger.info("Deleted poem id=%s", poem_id)
            return True
        return False

    def count_all(self) -> int:
        return self.db.query(Poem).count()
