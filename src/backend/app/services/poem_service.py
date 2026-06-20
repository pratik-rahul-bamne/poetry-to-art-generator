"""
Poem Service — business logic for poem operations.
Orchestrates between repository, AI providers, and logging.
No database code here — delegates to repositories.
"""

from typing import Optional
from sqlalchemy.orm import Session

from backend.app.repositories.poem_repo import PoemRepository
from backend.app.repositories.generation_repo import GenerationRepository
from backend.app.models.poem import Poem
from backend.app.models.generation import Generation
from backend.app.core.logger import get_logger

logger = get_logger("poem")


class PoemService:
    """Service layer for poem CRUD and history operations."""

    def __init__(self, db: Session):
        self.poem_repo = PoemRepository(db)
        self.gen_repo = GenerationRepository(db)

    def save_poem(
        self,
        poem_text: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        language: Optional[str] = None,
        theme: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> Poem:
        """Save a poem and return the created record."""
        poem = self.poem_repo.create(
            poem_text=poem_text,
            user_id=user_id,
            title=title,
            language=language,
            theme=theme,
            mood=mood,
        )
        logger.info("Poem saved: id=%s user=%s theme=%s", poem.id, user_id, theme)
        return poem

    def get_user_poems(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Poem], int]:
        """Return paginated poems for a user."""
        skip = (page - 1) * per_page
        return self.poem_repo.get_by_user(user_id, skip=skip, limit=per_page)

    def delete_poem(self, poem_id: str, user_id: str) -> bool:
        """Delete a poem if it belongs to the requesting user."""
        success = self.poem_repo.delete(poem_id, user_id)
        if success:
            logger.info("Poem deleted: id=%s user=%s", poem_id, user_id)
        return success

    def get_generation_history(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Generation], int]:
        """Return paginated generation history for a user."""
        skip = (page - 1) * per_page
        return self.gen_repo.get_by_user(user_id, skip=skip, limit=per_page)

    def get_gallery(self, limit: int = 12) -> list[Generation]:
        """Return recent completed generations for the public gallery."""
        return self.gen_repo.get_recent(limit=limit)
