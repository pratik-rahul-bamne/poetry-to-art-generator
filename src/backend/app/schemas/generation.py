"""
Generation schemas — request/response models for analyze/generate/compose endpoints.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Analysis ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    poem: str
    theme_override: Optional[str] = None


class AnalyzeResponse(BaseModel):
    theme: str
    mood: str
    image_prompt: str
    language: str


# ── Image Generation ──────────────────────────────────────────────────────────

class GenerateImageRequest(BaseModel):
    poem: Optional[str] = None
    image_prompt: Optional[str] = None
    style: Optional[str] = "aesthetic, soft lighting, photographic"
    provided_image_path: Optional[str] = None
    theme_override: Optional[str] = None
    provider: Optional[str] = None
    nlp_provider: Optional[str] = None
    sd_style: Optional[str] = "none"
    sd_width: Optional[int] = 512
    sd_height: Optional[int] = 512
    sd_steps: Optional[int] = 20
    sd_guidance: Optional[float] = 7.5
    sd_seed: Optional[int] = -1
    sd_negative_prompt: Optional[str] = (
        "blurry, bad quality, distorted, ugly, deformed, watermark, text, nsfw"
    )


class GenerateImageResponse(BaseModel):
    bg_filename: str


# ── Composition ───────────────────────────────────────────────────────────────

class ComposeRequest(BaseModel):
    poem: str
    bg_filename: Optional[str] = None
    bg_image_path: Optional[str] = None
    theme: Optional[str] = "Unknown"
    mood: Optional[str] = "Unknown"
    format: Optional[str] = "square"  # square | story


class ComposeResponse(BaseModel):
    final_filename: str
    url: str


# ── History ───────────────────────────────────────────────────────────────────

class GenerationHistoryItem(BaseModel):
    id: str
    image_prompt: Optional[str] = None
    provider_used: Optional[str] = None
    final_artwork_url: Optional[str] = None
    status: str
    generation_time: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
