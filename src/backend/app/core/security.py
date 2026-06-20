"""
Security — JWT token creation/verification + bcrypt password hashing.
Uses python-jose for JWT and bcrypt directly for password hashing.
(Avoids passlib compatibility issues with bcrypt 5.x on Python 3.13+)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger("auth")

# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of the plain-text password."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain-text password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ── JWT tokens ────────────────────────────────────────────────────────────────
def create_access_token(
    subject: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: Typically the user's UUID as a string.
        role: User role embedded in the token (user | admin).
        expires_delta: Token lifetime. Defaults to settings value.

    Returns:
        Signed JWT string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug("Access token created for subject=%s role=%s", subject, role)
    return token


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Returns:
        Payload dict with 'sub' and 'role' keys.

    Raises:
        ValueError: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise ValueError("Invalid or expired token") from exc
