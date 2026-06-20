"""
Auth Routes — register, login, logout, and current user.
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.repositories.user_repo import UserRepository
from backend.app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserMeResponse
from backend.app.models.activity_log import ActivityLog
from backend.app.core.logger import get_logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger("auth")


# ── Shared dependency ─────────────────────────────────────────────────────────

def get_current_user(request: Request) -> dict:
    """Dependency: returns the decoded JWT payload or raises 401."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    """Dependency: ensures the current user has admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


def _log_activity(db: Session, user_id: str | None, action: str, module: str, description: str = "") -> None:
    """Helper to write an activity log entry."""
    try:
        log = ActivityLog(user_id=user_id, action=action, module=module, description=description)
        db.add(log)
        db.commit()
    except Exception as e:
        logger.warning("Activity log write failed: %s", e)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    - Checks for duplicate email
    - Hashes password with bcrypt
    - Returns JWT access token
    """
    repo = UserRepository(db)

    if repo.get_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = repo.create(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    token = create_access_token(subject=user.id, role=user.role)
    _log_activity(db, user.id, "register", "auth", f"New user: {payload.email}")
    logger.info("User registered: %s", payload.email)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns a fresh JWT access token.
    """
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Please contact support.",
        )

    token = create_access_token(subject=user.id, role=user.role)
    repo.update_last_login(user.id)
    _log_activity(db, user.id, "login", "auth", f"Login: {payload.email}")
    logger.info("User logged in: %s", payload.email)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(user: dict = Depends(get_current_user)):
    """
    Logout — client should discard the token.
    (Stateless JWT — no server-side revocation in this implementation.
    For production, add a token blacklist in Redis.)
    """
    logger.info("User logged out: %s", user.get("sub"))
    return {"message": "Logged out successfully. Please discard your token."}


@router.get("/me", response_model=UserMeResponse)
def get_me(request: Request, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    repo = UserRepository(db)
    db_user = repo.get_by_id(user["sub"])
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")

    return UserMeResponse(
        id=db_user.id,
        name=db_user.name,
        email=db_user.email,
        role=db_user.role,
        status=db_user.status,
        created_at=db_user.created_at,
        last_login=db_user.last_login,
    )
