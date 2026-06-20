"""
Poem schemas — request/response models for poem CRUD.
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class PoemCreateRequest(BaseModel):
    """Payload for POST /api/v1/poems"""
    title: Optional[str] = None
    poem_text: str
    language: Optional[str] = None
    theme: Optional[str] = None
    mood: Optional[str] = None

    @field_validator("poem_text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Poem must be at least 10 characters")
        if len(v) > 5000:
            raise ValueError("Poem cannot exceed 5000 characters")
        return v


class PoemResponse(BaseModel):
    """Returned after creating or retrieving a poem."""
    id: str
    title: Optional[str] = None
    poem_text: str
    language: Optional[str] = None
    theme: Optional[str] = None
    mood: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PoemListResponse(BaseModel):
    """Paginated list of poems."""
    items: list[PoemResponse]
    total: int
