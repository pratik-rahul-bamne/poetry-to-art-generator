"""
Logger — Structured application logging.
Writes to console + rotating log files in logs/ directory.
"""

import logging
import logging.handlers
from pathlib import Path
from backend.app.core.config import settings


def _setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create and configure a named logger with console + file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # Already configured

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler ───────────────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # ── Rotating file handler ─────────────────────────────────────────────────
    log_file = settings.LOGS_DIR / f"{name.replace('.', '_')}.log"
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ── Named loggers for each module ────────────────────────────────────────────
api_logger      = _setup_logger("api")
auth_logger     = _setup_logger("auth")
poem_logger     = _setup_logger("poem")
ai_logger       = _setup_logger("ai")
compose_logger  = _setup_logger("compose")
db_logger       = _setup_logger("db")
perf_logger     = _setup_logger("performance")


def get_logger(name: str) -> logging.Logger:
    """Retrieve a pre-configured logger by name, or create a new one."""
    known = {
        "api": api_logger,
        "auth": auth_logger,
        "poem": poem_logger,
        "ai": ai_logger,
        "compose": compose_logger,
        "db": db_logger,
        "performance": perf_logger,
    }
    return known.get(name, _setup_logger(name))
