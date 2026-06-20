"""
Image Generation Service — supports multiple providers:
- Local Stable Diffusion 1.5 (PRIMARY — fully local, no API key, GPU/CPU)
- Pollinations.ai Flux (cloud, free tier, fallback)
- HuggingFace Inference API (SDXL, cloud, requires token)
"""

import io
import os
import httpx
import random
import threading
import asyncio
import logging
from urllib.parse import quote
from pathlib import Path

log = logging.getLogger("image_service")

# ─── Stable Diffusion Pipeline (shared singleton) ────────────────────────────
_sd_pipeline = None
_sd_lock = threading.Lock()
_sd_loading = False
_sd_ready = False

# Style modifier prompts (matching imagegen styles)
SD_STYLE_PROMPTS = {
    "none":           "",
    "photorealistic": ", photorealistic, 8k uhd, sharp focus, professional photography, DSLR, high detail",
    "anime":          ", anime style, manga illustration, vibrant colors, Studio Ghibli, cel-shaded",
    "oil_painting":   ", oil painting, classical art, fine brushstrokes, rich texture, museum quality",
    "watercolor":     ", watercolor painting, soft washes, delicate colors, artistic, flowing",
    "digital_art":    ", digital art, concept art, artstation, highly detailed, cinematic lighting",
    "3d_render":      ", 3D render, octane render, unreal engine 5, ray tracing, photorealistic CGI",
    "cinematic":      ", cinematic shot, movie still, dramatic lighting, anamorphic lens, film grain",
    "sketch":         ", pencil sketch, hand-drawn, graphite, detailed linework, artistic",
    "pixel_art":      ", pixel art, 16-bit, retro game style, detailed pixels",
    # Auto-mapped from poem mood
    "romantic":       ", romantic, dreamy atmosphere, soft pink and gold tones, bokeh, cinematic",
    "dark":           ", dramatic dark mood, deep shadows, moody atmospheric lighting, gothic",
    "nature":         ", lush nature, golden hour, photorealistic landscape, green and warm tones",
    "joyful":         ", vibrant colors, warm sunlight, uplifting, bright cheerful atmosphere",
    "mystical":       ", mystical ethereal atmosphere, magical light, fantasy art, digital painting",
    "melancholic":    ", melancholic mood, muted colors, misty, emotional, cinematic lighting",
}

def is_sd_ready() -> bool:
    return _sd_ready

def is_sd_loading() -> bool:
    return _sd_loading

def _load_sd_pipeline_sync():
    """Load SD pipeline in a thread (called once, blocks until loaded)."""
    global _sd_pipeline, _sd_ready, _sd_loading
    with _sd_lock:
        if _sd_ready:
            return _sd_pipeline
        _sd_loading = True
        try:
            from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
            import torch

            log.info("🔄 Loading Stable Diffusion 1.5 pipeline...")
            pipe = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float32,
                safety_checker=None,
                requires_safety_checker=False,
            )
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
            pipe.enable_attention_slicing(1)
            pipe = pipe.to("cpu")
            _sd_pipeline = pipe
            _sd_ready = True
            log.info("✅ Stable Diffusion 1.5 ready!")
        except Exception as e:
            log.error(f"❌ SD pipeline load failed: {e}")
            _sd_loading = False
            raise
        finally:
            _sd_loading = False
    return _sd_pipeline

def preload_sd_pipeline():
    """Start loading SD pipeline in a background thread."""
    t = threading.Thread(target=_load_sd_pipeline_sync, daemon=True)
    t.start()
    return t

def get_sd_pipeline():
    """Get the loaded Stable Diffusion pipeline instance (blocks if loading/not ready)."""
    global _sd_pipeline
    if not _sd_ready:
        return _load_sd_pipeline_sync()
    return _sd_pipeline


async def _generate_with_stable_diffusion(
    prompt: str,
    negative_prompt: str = "blurry, bad quality, distorted, ugly, deformed, watermark, text, nsfw",
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    guidance_scale: float = 7.5,
    seed: int = -1,
    style: str = "none",
) -> bytes:
    """Generate image using local Stable Diffusion 1.5 (CPU-optimized)."""
    import torch

    loop = asyncio.get_event_loop()

    def _sync():
        # Load pipeline if needed (blocking)
        pipe = _load_sd_pipeline_sync()

        # Apply style suffix
        style_suffix = SD_STYLE_PROMPTS.get(style, "")
        full_prompt = prompt + style_suffix

        # Seed
        if seed != -1:
            generator = torch.Generator("cpu").manual_seed(seed)
            actual_seed = seed
        else:
            actual_seed = torch.randint(0, 2**32, (1,)).item()
            generator = torch.Generator("cpu").manual_seed(actual_seed)

        log.info(f"🎨 SD generating: '{full_prompt[:60]}...' [{width}x{height}, {steps} steps, seed={actual_seed}]")

        image = pipe(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator,
        ).images[0]

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        log.info("✅ SD generation complete")
        return buf.getvalue()

    return await loop.run_in_executor(None, _sync)


async def generate_background_image(
    prompt: str,
    provided_image_path: str | None = None,
    provider: str | None = None,
    # SD-specific params
    sd_style: str = "none",
    sd_width: int = 512,
    sd_height: int = 512,
    sd_steps: int = 20,
    sd_guidance: float = 7.5,
    sd_seed: int = -1,
    sd_negative_prompt: str = "blurry, bad quality, distorted, ugly, deformed, watermark, text, nsfw",
) -> bytes:
    """
    Generate an image from a text prompt.

    Providers:
    - 'stable-diffusion' / 'sd' / 'local': Local SD 1.5 (FREE, no API key — PRIMARY)
    - 'pollinations': Pollinations.ai Flux (cloud, free tier)
    - 'huggingface' / 'hf' / 'sdxl': HF SDXL inference API (requires HF_API_TOKEN)
    """
    # Existing image passthrough
    if provided_image_path:
        if os.path.exists(provided_image_path):
            with open(provided_image_path, "rb") as f:
                return f.read()
        raise FileNotFoundError(f"Provided image not found: {provided_image_path}")

    provider = (provider or os.getenv("IMAGE_PROVIDER", "stable-diffusion")).strip().lower()

    # Sanitize prompt
    if not prompt or prompt.strip() == "":
        prompt = "A beautiful abstract background, rich colors, atmospheric lighting, high detail"

    # ── LOCAL STABLE DIFFUSION (PRIMARY) ────────────────────────────────────
    if provider in ("stable-diffusion", "sd", "local"):
        return await _generate_with_stable_diffusion(
            prompt=prompt,
            negative_prompt=sd_negative_prompt,
            width=sd_width,
            height=sd_height,
            steps=sd_steps,
            guidance_scale=sd_guidance,
            seed=sd_seed,
            style=sd_style,
        )

    # ── HUGGINGFACE SDXL ─────────────────────────────────────────────────────
    if provider in ("huggingface", "hf", "sdxl"):
        hf_token = os.getenv("HF_API_TOKEN") or os.getenv("HUGGINGFACE_API_TOKEN")
        if not hf_token:
            raise ValueError("HF_API_TOKEN is required for HuggingFace image provider")

        api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {hf_token}", "Accept": "application/json"}
        payload = {
            "inputs": prompt,
            "options": {"wait_for_model": True},
            "parameters": {"width": 1024, "height": 1024, "guidance_scale": 7.5, "num_inference_steps": 25}
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)

        if response.status_code not in (200, 201):
            raise ValueError(f"HuggingFace image generation failed: {response.status_code} - {response.text}")

        if response.headers.get("content-type", "").startswith("application/json"):
            body = response.json()
            if isinstance(body, dict) and "generated_image" in body:
                import base64
                return base64.b64decode(body["generated_image"])
            if isinstance(body, list) and body and "generated_image" in body[0]:
                import base64
                return base64.b64decode(body[0]["generated_image"])
            raise ValueError("Unexpected HF response format")
        return response.content

    # ── POLLINATIONS (cloud fallback) ─────────────────────────────────────────
    enhanced_prompt = f"{prompt}, aesthetic, photographic, highly detailed, atmospheric lighting, 4k"
    encoded_prompt = quote(enhanced_prompt)
    seed_val = random.randint(1, 1000000)
    api_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={seed_val}&model=flux"

    try:
        async with httpx.AsyncClient(timeout=80.0) as client:
            response = await client.get(api_url)
        if response.status_code != 200 or not response.content:
            raise ValueError(f"Pollinations failed: {response.status_code}")
        return response.content
    except Exception as e:
        log.warning(f"Pollinations failed ({e}), using gradient fallback...")
        return _gradient_fallback(prompt)


def _gradient_fallback(prompt: str) -> bytes:
    """Mood-based gradient image when all providers fail."""
    from PIL import Image

    prompt_lower = prompt.lower()
    if "dark" in prompt_lower or "night" in prompt_lower or "sad" in prompt_lower:
        colors = [(20, 20, 40), (60, 40, 80), (100, 60, 120)]
    elif "warm" in prompt_lower or "sunset" in prompt_lower or "love" in prompt_lower:
        colors = [(139, 69, 19), (205, 133, 63), (255, 140, 0)]
    elif "nature" in prompt_lower or "forest" in prompt_lower:
        colors = [(34, 139, 34), (70, 130, 180), (100, 149, 237)]
    elif "ocean" in prompt_lower or "water" in prompt_lower or "sky" in prompt_lower:
        colors = [(135, 206, 235), (70, 130, 180), (25, 25, 112)]
    else:
        colors = [(30, 60, 110), (60, 100, 150), (100, 140, 180)]

    img = Image.new("RGB", (1024, 1024))
    pixels = img.load()
    for y in range(1024):
        idx = (y // 256) % len(colors)
        nxt = (idx + 1) % len(colors)
        c1, c2 = colors[idx], colors[nxt]
        blend = (y % 256) / 256.0
        r = int(c1[0] * (1 - blend) + c2[0] * blend)
        g = int(c1[1] * (1 - blend) + c2[1] * blend)
        b = int(c1[2] * (1 - blend) + c2[2] * blend)
        for x in range(1024):
            pixels[x, y] = (r, g, b)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
