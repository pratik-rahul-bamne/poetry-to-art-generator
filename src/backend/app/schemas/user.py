"""
User schemas — request/response models for user management.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    """User data returned in API responses (never includes password_hash)."""
    id: str
    name: str
    email: str
    role: str
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Payload for PATCH /api/v1/users/me"""
    name: Optional[str] = None


class AdminUserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_poems: int
    total_generations: int
    total_downloads: int
    provider_breakdown: dict[str, int]
