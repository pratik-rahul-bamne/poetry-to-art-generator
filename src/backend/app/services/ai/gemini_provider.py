"""
Gemini Provider — Google Gemini for NLP analysis.
Implements the AIProvider abstract interface.
"""

import asyncio
import json
import re
import os
from backend.app.services.ai.base_provider import AIProvider, PoemAnalysis
from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger("ai")

# Lazy import to avoid startup failure if not installed
_genai = None

def _get_genai():
    global _genai
    if _genai is None:
        import google.generativeai as genai
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        _genai = genai
    return _genai


def _detect_language(poem: str) -> str:
    """Simple regex-based script detection."""
    if re.search(r"[\u0900-\u097F]", poem):
        return "Hindi/Marathi"
    return "English"


class GeminiProvider(AIProvider):
    """
    Gemini Flash provider for poem analysis.
    
    Requires GEMINI_API_KEY in environment.
    Falls back gracefully with ValueError if key missing.
    """

    @property
    def name(self) -> str:
        return "gemini"

    async def analyze_poem(
        self,
        poem: str,
        theme_override: str | None = None,
    ) -> PoemAnalysis:
        """
        Use Gemini Flash to extract theme, mood, and visual prompt.
        Returns structured JSON enforced via response_mime_type.
        """
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        genai = _get_genai()
        model = genai.GenerativeModel(settings.GEMINI_MODEL)

        system = (
            "Analyze the provided poem. Return ONLY valid JSON with keys: "
            "'theme', 'mood', 'visual_prompt'. "
            "IMPORTANT: 'visual_prompt' MUST be in detailed English regardless of poem language. "
            "Keep the prompt atmospheric and artistic."
        )
        prompt = f"{system}\n\nPoem:\n{poem}"
        if theme_override:
            prompt += f"\n\nNote: User prefers a '{theme_override}' theme."

        logger.info("Gemini analyze_poem: model=%s poem_len=%d", settings.GEMINI_MODEL, len(poem))

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                ),
            ),
        )

        data = json.loads(response.text)
        image_prompt = data.get("visual_prompt") or data.get("image_prompt", "")

        if theme_override:
            theme = theme_override.title()
        else:
            theme = data.get("theme", "Emotion")

        return PoemAnalysis(
            theme=theme,
            mood=data.get("mood", "Peaceful"),
            image_prompt=image_prompt,
            language=_detect_language(poem),
        )

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """
        Gemini does not currently support direct image generation via the
        standard API. Raise NotImplementedError to trigger fallback to
        Pollinations or Stable Diffusion.
        """
        raise NotImplementedError(
            "GeminiProvider does not support image generation. "
            "Use PollinationsProvider or StableDiffusionProvider."
        )
