"""
Image Service — wraps the AI provider abstraction for image generation.
Delegates to GeminiProvider → LocalProvider chain.
"""

import time
from pathlib import Path
from typing import Optional

from backend.app.services.ai.base_provider import ProviderChain
from backend.app.services.ai.gemini_provider import GeminiProvider
from backend.app.services.ai.local_provider import LocalProvider, is_sd_ready, is_sd_loading, preload_sd_pipeline
from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger("ai")

# ── Provider chain (Gemini analyze → Local image) ─────────────────────────────
_analyze_chain = ProviderChain([GeminiProvider(), LocalProvider()])
_image_chain   = ProviderChain([LocalProvider()])


async def analyze_poem(poem: str, theme_override: Optional[str] = None, provider: Optional[str] = None) -> dict:
    """
    Analyze a poem using the configured provider chain.
    Returns a dict with theme, mood, image_prompt, language.
    """
    t0 = time.time()
    result = await _analyze_chain.analyze_poem(poem, theme_override)
    logger.info("analyze_poem: %.2fs theme=%s", time.time() - t0, result.theme)
    return {
        "theme": result.theme,
        "mood": result.mood,
        "image_prompt": result.image_prompt,
        "language": result.language,
    }


async def generate_background_image(
    prompt: str,
    provider: Optional[str] = None,
    provided_image_path: Optional[str] = None,
    **kwargs,
) -> bytes:
    """
    Generate a background image.
    - If provided_image_path is set, load and return that file directly.
    - Otherwise, delegate to the image provider chain.
    """
    if provided_image_path:
        p = Path(provided_image_path)
        if not p.exists():
            raise FileNotFoundError(f"Provided image not found: {provided_image_path}")
        return p.read_bytes()

    t0 = time.time()
    image_bytes = await _image_chain.generate_image(prompt, provider=provider, **kwargs)
    logger.info("generate_image: %.2fs provider=%s", time.time() - t0, provider or settings.IMAGE_PROVIDER)
    return image_bytes


def get_sd_status() -> dict:
    """Return current Stable Diffusion pipeline status."""
    from backend.app.services.ai.local_provider import SD_STYLE_PROMPTS
    return {
        "ready": is_sd_ready(),
        "loading": is_sd_loading(),
        "provider": "Stable Diffusion 1.5 (CPU)",
        "styles": list(SD_STYLE_PROMPTS.keys()),
    }


def trigger_sd_preload() -> dict:
    """Trigger SD model loading in background thread."""
    if is_sd_ready():
        return {"status": "already_ready", "message": "Pipeline already loaded!"}
    if is_sd_loading():
        return {"status": "loading", "message": "Pipeline is currently loading..."}
    preload_sd_pipeline()
    return {"status": "started", "message": "Pipeline loading started in background..."}
