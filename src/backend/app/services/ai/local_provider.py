"""
Local Provider — FLAN-T5 (NLP) + Stable Diffusion / Pollinations (image).
Implements the AIProvider abstract interface.
Zero cloud dependency — runs 100% locally or via free Pollinations API.
"""

import asyncio
import re
from typing import Optional
from backend.app.services.ai.base_provider import AIProvider, PoemAnalysis
from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger("ai")

# ── Lazy-loaded state ─────────────────────────────────────────────────────────
_flan_pipeline = None
_sd_pipeline = None
_sd_loading = False
_sd_ready = False


def _detect_language(poem: str) -> str:
    if re.search(r"[\u0900-\u097F]", poem):
        return "Hindi/Marathi"
    return "English"


def _fallback_analyze(poem: str, theme_override: Optional[str] = None) -> PoemAnalysis:
    """Keyword-based heuristic — always works, no dependencies."""
    lower = poem.lower()
    if "love" in lower or "प्रेम" in lower:
        theme = "Love"
    elif "nature" in lower or "garden" in lower or "प्रकृति" in lower:
        theme = "Nature"
    elif "night" in lower or "moon" in lower or "रात" in lower:
        theme = "Night"
    elif "hope" in lower or "आशा" in lower:
        theme = "Hope"
    elif "sad" in lower or "pain" in lower or "दुःख" in lower:
        theme = "Melancholy"
    else:
        theme = "Emotion"

    if theme_override:
        theme = theme_override.title()

    mood = "Peaceful and reflective"
    if "happy" in lower or "joy" in lower:
        mood = "Joyful and uplifting"
    elif "sad" in lower or "lonely" in lower:
        mood = "Somber and contemplative"

    image_prompt = (
        f"A {mood.lower()} {theme.lower()} scene, "
        "soft lighting, atmospheric, high quality, painterly style"
    )
    return PoemAnalysis(
        theme=theme, mood=mood,
        image_prompt=image_prompt,
        language=_detect_language(poem),
    )


def _get_flan_pipeline():
    global _flan_pipeline
    if _flan_pipeline is None:
        from transformers import pipeline
        _flan_pipeline = pipeline(
            "text2text-generation",
            model="google/flan-t5-base",
            device_map="auto",
        )
    return _flan_pipeline


def is_sd_ready() -> bool:
    return _sd_ready


def is_sd_loading() -> bool:
    return _sd_loading


def preload_sd_pipeline() -> None:
    """Start loading SD 1.5 in a background thread."""
    global _sd_loading
    if _sd_ready or _sd_loading:
        return
    _sd_loading = True
    import threading
    threading.Thread(target=_load_sd_blocking, daemon=True).start()


def _load_sd_blocking() -> None:
    global _sd_pipeline, _sd_ready, _sd_loading
    try:
        from diffusers import StableDiffusionPipeline
        import torch
        _sd_pipeline = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
        )
        _sd_pipeline = _sd_pipeline.to("cpu")
        _sd_ready = True
        logger.info("Stable Diffusion pipeline loaded ✓")
    except Exception as e:
        logger.error("SD pipeline load failed: %s", e)
    finally:
        _sd_loading = False


# ── SD Style prompts ──────────────────────────────────────────────────────────
SD_STYLE_PROMPTS = {
    "none":           "",
    "photorealistic": "photorealistic, DSLR, 85mm lens, sharp focus, bokeh",
    "anime":          "anime style, Makoto Shinkai, vibrant colors, detailed",
    "oil_painting":   "oil painting, impressionist, textured brushstrokes",
    "watercolor":     "watercolor painting, soft edges, translucent colors",
    "digital_art":    "digital art, concept art, artstation, highly detailed",
    "3d_render":      "3D render, octane render, subsurface scattering, ray tracing",
    "cinematic":      "cinematic, dramatic lighting, movie still, 4K",
    "sketch":         "pencil sketch, hand-drawn, detailed line art",
}


class LocalProvider(AIProvider):
    """
    Local provider: FLAN-T5 for NLP, SD 1.5 or Pollinations for images.
    No API keys required.
    """

    @property
    def name(self) -> str:
        return "local"

    async def analyze_poem(
        self,
        poem: str,
        theme_override: Optional[str] = None,
    ) -> PoemAnalysis:
        """Try FLAN-T5 first, fall back to keyword heuristic."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._flan_analyze, poem, theme_override)
            return result
        except Exception as e:
            logger.warning("FLAN-T5 failed, using fallback: %s", e)
            return _fallback_analyze(poem, theme_override)

    def _flan_analyze(self, poem: str, theme_override: Optional[str]) -> PoemAnalysis:
        pipeline = _get_flan_pipeline()
        prompt = (
            f"Analyze this poem and extract:\nTheme (one word):\nMood (one phrase):\n"
            f"Image Prompt (detailed visual):\n\nPoem:\n{poem}\n\nReturn ONLY these three lines."
        )
        result = pipeline(prompt, max_length=300, do_sample=False)
        text = result[0]["generated_text"].strip()
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        theme = lines[0].split(":", 1)[-1].strip() if lines else "Emotion"
        mood = lines[1].split(":", 1)[-1].strip() if len(lines) > 1 else "Peaceful"
        image_prompt = lines[2].split(":", 1)[-1].strip() if len(lines) > 2 else ""

        if theme_override:
            theme = theme_override.title()
        if not image_prompt:
            image_prompt = f"A {mood.lower()} {theme.lower()} scene, atmospheric, painterly"

        return PoemAnalysis(
            theme=theme, mood=mood,
            image_prompt=image_prompt,
            language=_detect_language(poem),
        )

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """
        Generate via Stable Diffusion (if ready) or Pollinations (free cloud).
        """
        provider = (kwargs.get("provider") or settings.IMAGE_PROVIDER).lower()

        if provider in ("stable-diffusion", "sd", "local") and _sd_ready:
            return await self._generate_sd(prompt, **kwargs)

        # Default: Pollinations.ai (free, no key required)
        return await self._generate_pollinations(prompt)

    async def _generate_pollinations(self, prompt: str) -> bytes:
        import httpx
        from urllib.parse import quote

        encoded = quote(prompt[:400])
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true"
        logger.info("Pollinations request: %s", url[:80])

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    async def _generate_sd(self, prompt: str, **kwargs) -> bytes:
        import asyncio
        from io import BytesIO

        loop = asyncio.get_event_loop()
        img_bytes = await loop.run_in_executor(
            None, self._run_sd_sync, prompt, kwargs
        )
        return img_bytes

    def _run_sd_sync(self, prompt: str, kwargs: dict) -> bytes:
        from io import BytesIO
        import torch

        style = kwargs.get("sd_style", "none")
        style_suffix = SD_STYLE_PROMPTS.get(style, "")
        full_prompt = f"{prompt}, {style_suffix}".strip(", ") if style_suffix else prompt

        neg = kwargs.get(
            "sd_negative_prompt",
            "blurry, bad quality, distorted, watermark, text, nsfw",
        )
        steps = int(kwargs.get("sd_steps", 20))
        guidance = float(kwargs.get("sd_guidance", 7.5))
        seed = int(kwargs.get("sd_seed", -1))
        w = int(kwargs.get("sd_width", 512))
        h = int(kwargs.get("sd_height", 512))

        generator = None
        if seed >= 0:
            generator = torch.Generator("cpu").manual_seed(seed)

        result = _sd_pipeline(
            prompt=full_prompt,
            negative_prompt=neg,
            num_inference_steps=steps,
            guidance_scale=guidance,
            width=w,
            height=h,
            generator=generator,
        )
        img = result.images[0]
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
