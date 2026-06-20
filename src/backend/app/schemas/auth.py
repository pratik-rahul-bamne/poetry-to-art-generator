"""
Auth schemas — request/response models for register, login, and token endpoints.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """Payload for POST /api/v1/auth/register"""
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class LoginRequest(BaseModel):
    """Payload for POST /api/v1/auth/login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned after successful register or login."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    role: str


class UserMeResponse(BaseModel):
    """Returned by GET /api/v1/auth/me"""
    id: str
    name: str
    email: str
    role: str
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None
