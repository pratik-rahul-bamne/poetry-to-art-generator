"""
NLP Service — Uses Google Gemini or local FLAN-T5 for poem analysis.
Supports: Gemini (cloud), FLAN-T5 (local, free), Fallback (heuristic).
"""

import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

_api_key = os.getenv("GEMINI_API_KEY", "")
if _api_key:
    genai.configure(api_key=_api_key)

_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
_NLP_PROVIDER = os.getenv("NLP_PROVIDER", "gemini").strip().lower()  # 'gemini', 'flan-t5', or 'fallback'

_flan_pipeline = None

def _get_flan_pipeline():
    """Lazy-load FLAN-T5 on first use to avoid startup overhead."""
    global _flan_pipeline
    if _flan_pipeline is None:
        try:
            from transformers import pipeline
            _flan_pipeline = pipeline(
                "text2text-generation",
                model="google/flan-t5-base",
                device_map="auto"
            )
        except ImportError:
            raise ImportError(
                "transformers not installed. Install with: pip install transformers torch"
            )
    return _flan_pipeline

def _detect_language(poem: str) -> str:
    if re.search(r"[\u0900-\u097F]", poem):
        return "Hindi/Marathi"
    return "English"

def _fallback_analyze(poem: str, theme_override: str | None = None) -> dict:
    """Simple keyword-based theme extraction when APIs are unavailable."""
    theme = ""
    lower = poem.lower()

    # simple keyword-based theme extraction
    if "love" in lower or "प्रेम" in lower:
        theme = "Love"
    elif "nature" in lower or "प्रकृति" in lower or "garden" in lower:
        theme = "Nature"
    elif "night" in lower or "रात" in lower or "moon" in lower:
        theme = "Night"
    elif "hope" in lower or "आशा" in lower:
        theme = "Hope"
    elif "sad" in lower or "दुःख" in lower or "pain" in lower:
        theme = "Melancholy"
    else:
        theme = "Emotion"

    if theme_override:
        theme = theme_override.title()

    mood = "Peaceful and reflective"
    if "happy" in lower or "खुश" in lower or "joy" in lower:
        mood = "Joyful and uplifting"
    elif "sad" in lower or "दुःख" in lower or "lonely" in lower:
        mood = "Somber and contemplative"

    image_prompt = (
        f"A {mood.lower()} {theme.lower()} scene, soft lighting, atmospheric, high quality, painterly style"
    )

    return {
        "theme": theme,
        "mood": mood,
        "image_prompt": image_prompt,
        "language": _detect_language(poem),
    }

def _analyze_with_flan_t5(poem: str, theme_override: str | None = None) -> dict:
    """Analyze using local FLAN-T5 model (free, no API key required)."""
    try:
        pipeline = _get_flan_pipeline()
        
        prompt = f"""Analyze this poem and extract:
Theme (one word):
Mood (one phrase):
Image Prompt (detailed visual description):

Poem:
{poem}

Return ONLY these three lines, no extra text."""

        result = pipeline(prompt, max_length=300, do_sample=False)
        text = result[0]["generated_text"].strip()
        
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        theme = "Emotion"
        mood = "Peaceful"
        image_prompt = "A poetic scene with soft lighting and atmospheric mood"
        
        if len(lines) >= 1:
            theme = lines[0].split(":", 1)[-1].strip() or theme
        if len(lines) >= 2:
            mood = lines[1].split(":", 1)[-1].strip() or mood
        if len(lines) >= 3:
            image_prompt = lines[2].split(":", 1)[-1].strip() or image_prompt
        
        if theme_override:
            theme = theme_override.title()
        
        return {
            "theme": theme,
            "mood": mood,
            "image_prompt": image_prompt,
            "language": _detect_language(poem),
        }
    except Exception as e:
        print(f"FLAN-T5 analysis failed, falling back: {e}")
        return _fallback_analyze(poem, theme_override)

async def analyze_poem(
    poem: str,
    theme_override: str | None = None,
    provider: str | None = None
) -> dict:
    """
    Analyze the provided poem.
    
    Providers:
    - 'gemini': Google Gemini (requires GEMINI_API_KEY)
    - 'flan-t5': Local FLAN-T5 Base (free, no key required)
    - 'fallback': Simple keyword-based heuristic (always available)
    """
    provider = (provider or _NLP_PROVIDER).strip().lower()
    
    if provider == "flan-t5":
        return _analyze_with_flan_t5(poem, theme_override)
    
    if provider == "fallback":
        return _fallback_analyze(poem, theme_override)
    
    # Default: try Gemini, fall back to FLAN-T5 or heuristic
    if not _api_key:
        return _analyze_with_flan_t5(poem, theme_override)

    model = genai.GenerativeModel(_GEMINI_MODEL)
    
    system_instruction = (
        "Analyze the provided poem. Return ONLY valid JSON with keys: 'theme', 'mood', and 'visual_prompt'. "
        "IMPORTANT: The 'visual_prompt' MUST be written in detailed English, regardless of the poem's original language. "
        "Keep the prompt aesthetic and atmospheric."
    )
    
    prompt = f"{system_instruction}\n\nPoem:\n{poem}"
    if theme_override:
        prompt += f"\n\nNote: The user prefers a '{theme_override}' theme."

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
        ))
        
        data = json.loads(response.text)
        data["image_prompt"] = data.get("visual_prompt", data.get("image_prompt", ""))
        if "language" not in data:
            data["language"] = _detect_language(poem)
        return data
    except Exception as e:
        message = str(e).lower()
        if "not found" in message or "unsupported" in message or "model" in message:
            return _analyze_with_flan_t5(poem, theme_override)
        return _fallback_analyze(poem, theme_override)

