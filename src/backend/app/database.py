"""
Database — SQLAlchemy 2.0 async-compatible engine + session factory.
Uses SQLite in development (swappable to PostgreSQL via DATABASE_URL env var).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger("db")

# ── Engine ────────────────────────────────────────────────────────────────────
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,  # Log SQL in dev
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass


# ── Dependency ─────────────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and ensures cleanup.

    Usage:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all database tables on first run.
    Import all models before calling this so metadata is populated.
    """
    # Import models so SQLAlchemy sees them before creating tables
    from backend.app.models import user, poem, generation, download, activity_log, ai_provider_log  # noqa: F401

    logger.info("Initializing database at %s", settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified ✓")
