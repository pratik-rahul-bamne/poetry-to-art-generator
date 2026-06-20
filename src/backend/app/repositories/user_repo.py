"""
User Repository — all database operations for the users table.
No business logic here — only data access.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.core.logger import get_logger

logger = get_logger("db")


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, email: str, password_hash: str, role: str = "user") -> User:
        """Create and persist a new user."""
        user = User(name=name, email=email, password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info("Created user id=%s email=%s", user.id, email)
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Find a user by their UUID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Find a user by email address."""
        return self.db.query(User).filter(User.email == email).first()

    def update_last_login(self, user_id: str) -> None:
        """Stamp the last_login timestamp after successful authentication."""
        self.db.query(User).filter(User.id == user_id).update(
            {"last_login": datetime.now(timezone.utc)}
        )
        self.db.commit()

    def update_name(self, user_id: str, name: str) -> Optional[User]:
        """Update user's display name."""
        user = self.get_by_id(user_id)
        if user:
            user.name = name
            self.db.commit()
            self.db.refresh(user)
        return user

    def list_all(self, skip: int = 0, limit: int = 50) -> tuple[list[User], int]:
        """Return paginated users list with total count (admin use)."""
        total = self.db.query(User).count()
        users = self.db.query(User).offset(skip).limit(limit).all()
        return users, total

    def count_active(self) -> int:
        """Count users with status='active'."""
        return self.db.query(User).filter(User.status == "active").count()
