"""
User Routes — profile management.
GET   /api/v1/users/me
PATCH /api/v1/users/me
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.repositories.user_repo import UserRepository
from backend.app.schemas.user import UserResponse, UserUpdateRequest
from backend.app.api.v1.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_profile(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return the authenticated user's profile."""
    repo = UserRepository(db)
    db_user = repo.get_by_id(user["sub"])
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update the authenticated user's display name."""
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    repo = UserRepository(db)
    updated = repo.update_name(user["sub"], payload.name.strip())
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated
