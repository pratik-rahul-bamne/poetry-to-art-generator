"""
API Routes — handles all /api/* endpoints
"""

import uuid
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from backend.services.nlp_service import analyze_poem
from backend.services.image_service import (
    generate_background_image,
    is_sd_ready,
    is_sd_loading,
    preload_sd_pipeline,
    SD_STYLE_PROMPTS,
)
from backend.app.services.compose_service import compose_image
from backend.database import save_to_gallery, get_recent_art

router = APIRouter()

# Resolve outputs directory relative to project root
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    poem: str
    theme_override: Optional[str] = None


class GenerateImageRequest(BaseModel):
    poem: Optional[str] = None
    image_prompt: Optional[str] = None
    style: Optional[str] = "aesthetic, soft lighting, photographic"
    provided_image_path: Optional[str] = None
    theme_override: Optional[str] = None
    provider: Optional[str] = None         # 'stable-diffusion' (default), 'pollinations', 'huggingface'
    nlp_provider: Optional[str] = None
    # SD-specific params
    sd_style: Optional[str] = "none"       # style chip from imagegen
    sd_width: Optional[int] = 512
    sd_height: Optional[int] = 512
    sd_steps: Optional[int] = 20
    sd_guidance: Optional[float] = 7.5
    sd_seed: Optional[int] = -1
    sd_negative_prompt: Optional[str] = "blurry, bad quality, distorted, ugly, deformed, watermark, text, nsfw"


class ComposeRequest(BaseModel):
    poem: str
    bg_filename: Optional[str] = None
    bg_image_path: Optional[str] = None
    theme: Optional[str] = "Unknown"
    mood: Optional[str] = "Unknown"
    format: Optional[str] = "square"  # "square" (1:1) or "story" (9:16)


class PreloadRequest(BaseModel):
    pass


# ---------------------------------------------------------------------------
# 0. SD Status & Preload
# ---------------------------------------------------------------------------

@router.get("/sd-status")
async def sd_status():
    """Returns current Stable Diffusion pipeline status."""
    return {
        "ready": is_sd_ready(),
        "loading": is_sd_loading(),
        "provider": "Stable Diffusion 1.5 (CPU)",
        "styles": list(SD_STYLE_PROMPTS.keys()),
    }

@router.post("/sd-preload")
async def sd_preload():
    """Trigger background loading of the SD model (one-time ~30-60s download)."""
    if is_sd_ready():
        return {"status": "already_ready", "message": "Pipeline already loaded!"}
    if is_sd_loading():
        return {"status": "loading", "message": "Pipeline is currently loading..."}
    preload_sd_pipeline()
    return {"status": "started", "message": "Pipeline loading started in background..."}


# ---------------------------------------------------------------------------
# 1. Analyze poem with NLP
# ---------------------------------------------------------------------------

@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Analyzes poem text using Gemini Flash.
    Returns: theme, mood, image_prompt, language
    """
    try:
        result = await analyze_poem(request.poem, request.theme_override)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NLP analysis failed: {str(e)}")


# ---------------------------------------------------------------------------
# 2. Generate background image
# ---------------------------------------------------------------------------

@router.post("/generate-image")
async def generate_image(request: GenerateImageRequest):
    """
    Generates an aesthetic background image based on poem or prompt.
    Primary provider: Local Stable Diffusion 1.5.
    Fallback: Pollinations.ai (cloud).
    """
    try:
        if request.provided_image_path:
            image_bytes = await generate_background_image(
                "", provided_image_path=request.provided_image_path
            )
        else:
            prompt_src = request.image_prompt
            if not prompt_src and request.poem:
                print(f"[IMAGE GEN] Analyzing poem to generate prompt...")
                auto_analysis = await analyze_poem(
                    request.poem, request.theme_override, provider=request.nlp_provider
                )
                prompt_src = auto_analysis.get("image_prompt")
                print(f"[IMAGE GEN] Generated prompt: {prompt_src}")

            if not prompt_src:
                raise HTTPException(
                    status_code=400,
                    detail="image_prompt or poem is required when provided_image_path is not set"
                )

            # For non-SD providers, append style suffix to prompt
            provider = (request.provider or os.getenv("IMAGE_PROVIDER", "stable-diffusion")).lower()
            if provider not in ("stable-diffusion", "sd", "local"):
                prompt_src = f"{prompt_src}, {request.style}, no text, no people, minimal clutter, high quality, 4k"

            print(f"[IMAGE GEN] Provider: {provider} | Prompt: {prompt_src[:80]}...")

            image_bytes = await generate_background_image(
                prompt=prompt_src,
                provider=request.provider,
                sd_style=request.sd_style or "none",
                sd_width=request.sd_width or 512,
                sd_height=request.sd_height or 512,
                sd_steps=request.sd_steps or 20,
                sd_guidance=request.sd_guidance or 7.5,
                sd_seed=request.sd_seed if request.sd_seed is not None else -1,
                sd_negative_prompt=request.sd_negative_prompt or "blurry, bad quality, distorted, ugly, deformed, watermark, text, nsfw",
            )

        filename = f"bg_{uuid.uuid4().hex[:8]}.png"
        filepath = OUTPUTS_DIR / filename
        filepath.write_bytes(image_bytes)

        print(f"[IMAGE GEN] ✓ Saved: {filename}")
        return {"bg_filename": filename}

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


# ---------------------------------------------------------------------------
# 3. Compose — overlay poem text on background
# ---------------------------------------------------------------------------

@router.post("/compose")
async def compose(request: ComposeRequest):
    """
    Overlays handwritten poem text on the background image and saves to gallery.
    """
    if request.bg_image_path:
        bg_path = Path(request.bg_image_path)
    elif request.bg_filename:
        candidate = OUTPUTS_DIR / request.bg_filename
        if candidate.exists():
            bg_path = candidate
        else:
            alt = Path(request.bg_filename)
            bg_path = alt if alt.exists() else candidate
    else:
        raise HTTPException(status_code=400, detail="bg_filename or bg_image_path is required")

    if not bg_path.exists():
        raise HTTPException(status_code=404, detail=f"Background image not found: {bg_path}")

    try:
        final_filename = f"final_{uuid.uuid4().hex[:8]}.png"
        final_path = OUTPUTS_DIR / final_filename

        await compose_image(
            poem_text=request.poem,
            bg_path=str(bg_path),
            output_path=str(final_path),
            format=request.format,
        )

        save_to_gallery(
            poem_text=request.poem,
            theme=request.theme,
            mood=request.mood,
            image_path=f"/outputs/{final_filename}"
        )

        return {
            "final_filename": final_filename,
            "url": f"/outputs/{final_filename}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image composition failed: {str(e)}")


# ---------------------------------------------------------------------------
# 4. Gallery — fetch recent creations
# ---------------------------------------------------------------------------

@router.get("/gallery")
async def gallery(limit: int = 12):
    """Returns the most recent generated artworks from the SQLite database."""
    try:
        items = get_recent_art(limit=limit)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch gallery: {str(e)}")


# ---------------------------------------------------------------------------
# 5. Download final image
# ---------------------------------------------------------------------------

@router.get("/download/{filename}")
async def download(filename: str):
    """Serves a generated image file as a download attachment."""
    safe_name = Path(filename).name
    filepath = OUTPUTS_DIR / safe_name

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(filepath),
        media_type="image/png",
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
