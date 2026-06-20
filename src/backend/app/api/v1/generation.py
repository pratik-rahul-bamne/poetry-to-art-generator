"""
Generation Routes — the core AI pipeline: analyze → generate → compose → download.
All existing functionality preserved and migrated to /api/v1/.

POST /api/v1/analyze
POST /api/v1/generate-image
POST /api/v1/compose
GET  /api/v1/download/{filename}
GET  /api/v1/gallery
GET  /api/v1/sd-status
POST /api/v1/sd-preload
GET  /api/v1/history  (auth required)
"""

import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.services.image_service import (
    analyze_poem,
    generate_background_image,
    get_sd_status,
    trigger_sd_preload,
)
from backend.app.services.compose_service import compose_image
from backend.app.services.poem_service import PoemService
from backend.app.repositories.generation_repo import GenerationRepository
from backend.app.repositories.poem_repo import PoemRepository
from backend.app.schemas.generation import (
    AnalyzeRequest, AnalyzeResponse,
    GenerateImageRequest, GenerateImageResponse,
    ComposeRequest, ComposeResponse,
    GenerationHistoryItem,
)
from backend.app.core.config import settings
from backend.app.core.logger import get_logger
from backend.app.api.v1.auth import get_current_user

router = APIRouter(tags=["Generation"])
logger = get_logger("ai")

OUTPUTS_DIR = settings.OUTPUTS_DIR
OUTPUTS_DIR.mkdir(exist_ok=True)


# ── SD Status ─────────────────────────────────────────────────────────────────

@router.get("/sd-status")
async def sd_status():
    """Returns current Stable Diffusion pipeline status."""
    return get_sd_status()


@router.post("/sd-preload")
async def sd_preload():
    """Trigger background loading of the SD model."""
    return trigger_sd_preload()


# ── 1. Analyze poem ───────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Analyze poem text using the configured NLP provider.
    Returns: theme, mood, image_prompt, language.
    """
    try:
        result = await analyze_poem(request.poem, request.theme_override)
        return AnalyzeResponse(**result)
    except Exception as e:
        logger.error("analyze_poem failed: %s", e)
        raise HTTPException(status_code=500, detail=f"NLP analysis failed: {str(e)}")


# ── 2. Generate background image ──────────────────────────────────────────────

@router.post("/generate-image", response_model=GenerateImageResponse)
async def generate_image(request: GenerateImageRequest):
    """
    Generate an aesthetic background image based on poem or prompt.
    Providers: stable-diffusion (local) | pollinations (cloud, free) | huggingface
    """
    try:
        if request.provided_image_path:
            image_bytes = await generate_background_image(
                "", provided_image_path=request.provided_image_path
            )
        else:
            prompt_src = request.image_prompt
            if not prompt_src and request.poem:
                auto = await analyze_poem(request.poem, request.theme_override)
                prompt_src = auto.get("image_prompt")

            if not prompt_src:
                raise HTTPException(
                    status_code=400,
                    detail="image_prompt or poem is required",
                )

            provider = (request.provider or settings.IMAGE_PROVIDER).lower()
            if provider not in ("stable-diffusion", "sd", "local"):
                prompt_src = f"{prompt_src}, {request.style}, no text, no people, high quality, 4k"

            image_bytes = await generate_background_image(
                prompt=prompt_src,
                provider=provider,
                sd_style=request.sd_style or "none",
                sd_width=request.sd_width or 512,
                sd_height=request.sd_height or 512,
                sd_steps=request.sd_steps or 20,
                sd_guidance=request.sd_guidance or 7.5,
                sd_seed=request.sd_seed if request.sd_seed is not None else -1,
                sd_negative_prompt=request.sd_negative_prompt,
            )

        filename = f"bg_{uuid.uuid4().hex[:8]}.png"
        filepath = OUTPUTS_DIR / filename
        filepath.write_bytes(image_bytes)
        logger.info("Background saved: %s", filename)
        return GenerateImageResponse(bg_filename=filename)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("generate_image failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


# ── 3. Compose artwork ────────────────────────────────────────────────────────

@router.post("/compose", response_model=ComposeResponse)
async def compose(
    request: ComposeRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """
    Overlay handwritten poem text on background image.
    Saves the generation record to the database.
    """
    # Resolve background image path
    if request.bg_image_path:
        bg_path = Path(request.bg_image_path)
    elif request.bg_filename:
        bg_path = OUTPUTS_DIR / request.bg_filename
        if not bg_path.exists():
            bg_path = Path(request.bg_filename)
    else:
        raise HTTPException(status_code=400, detail="bg_filename or bg_image_path is required")

    if not bg_path.exists():
        raise HTTPException(status_code=404, detail=f"Background image not found: {bg_path}")

    try:
        t0 = time.time()
        final_filename = f"final_{uuid.uuid4().hex[:8]}.png"
        final_path = OUTPUTS_DIR / final_filename

        await compose_image(
            poem_text=request.poem,
            bg_path=str(bg_path),
            output_path=str(final_path),
            format=request.format,
        )

        gen_time = round(time.time() - t0, 2)

        # Save generation record
        gen_repo = GenerationRepository(db)
        poem_repo = PoemRepository(db)

        # Get or create a poem record (guest)
        user_info = getattr(req.state, "user", None)
        user_id = user_info["sub"] if user_info else None

        poem = poem_repo.create(
            poem_text=request.poem,
            user_id=user_id,
            theme=request.theme,
            mood=request.mood,
        )

        gen = gen_repo.create(
            poem_id=poem.id,
            image_prompt=str(bg_path),
            provider_used=settings.IMAGE_PROVIDER,
        )
        gen_repo.update_completed(
            gen.id,
            image_url=f"/outputs/{request.bg_filename or ''}",
            final_artwork_url=f"/outputs/{final_filename}",
            generation_time=gen_time,
        )

        logger.info("Artwork composed: %s in %.2fs", final_filename, gen_time)

        return ComposeResponse(
            final_filename=final_filename,
            url=f"/outputs/{final_filename}",
        )

    except Exception as e:
        logger.error("compose failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Image composition failed: {str(e)}")


# ── 4. Gallery ────────────────────────────────────────────────────────────────

@router.get("/gallery")
async def gallery(limit: int = 12, db: Session = Depends(get_db)):
    """Returns the most recent generated artworks."""
    try:
        service = PoemService(db)
        items = service.get_gallery(limit=limit)
        return [
            {
                "id": g.id,
                "image_path": g.final_artwork_url,
                "theme": g.poem.theme if g.poem else None,
                "mood": g.poem.mood if g.poem else None,
                "poem_text": g.poem.poem_text[:120] if g.poem else "",
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in items
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gallery fetch failed: {str(e)}")


# ── 5. Download ───────────────────────────────────────────────────────────────

@router.get("/download/{filename}")
async def download(filename: str, request: Request, db: Session = Depends(get_db)):
    """Download a generated image. Records the download event."""
    safe_name = Path(filename).name
    filepath = OUTPUTS_DIR / safe_name

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Record download
    try:
        gen_repo = GenerationRepository(db)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")[:500]
        # Try to find generation by artwork URL
        gen_repo.record_download(generation_id="", ip_address=ip, device_info=ua)
    except Exception:
        pass  # Non-critical

    return FileResponse(
        path=str(filepath),
        media_type="image/png",
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


# ── 6. History (auth required) ────────────────────────────────────────────────

@router.get("/history")
async def generation_history(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return the authenticated user's generation history."""
    service = PoemService(db)
    items, total = service.get_generation_history(user["sub"], page=page, per_page=per_page)
    return {
        "items": [
            {
                "id": g.id,
                "final_artwork_url": g.final_artwork_url,
                "provider_used": g.provider_used,
                "generation_time": g.generation_time,
                "status": g.status,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in items
        ],
        "total": total,
        "page": page,
    }
