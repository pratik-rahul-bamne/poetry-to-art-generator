"""
Unit tests for AI Provider abstraction.
Tests ProviderChain fallback behavior and LocalProvider fallback analyzer.
"""

import pytest
import asyncio

from backend.app.services.ai.base_provider import AIProvider, PoemAnalysis, ProviderChain
from backend.app.services.ai.local_provider import _fallback_analyze


# ── Mock providers ────────────────────────────────────────────────────────────

class AlwaysFailProvider(AIProvider):
    @property
    def name(self): return "fail"
    async def analyze_poem(self, poem, theme_override=None):
        raise RuntimeError("Simulated failure")
    async def generate_image(self, prompt, **kwargs):
        raise RuntimeError("Simulated failure")


class AlwaysSuccessProvider(AIProvider):
    @property
    def name(self): return "success"
    async def analyze_poem(self, poem, theme_override=None):
        return PoemAnalysis(theme="Nature", mood="Peaceful", image_prompt="A garden", language="English")
    async def generate_image(self, prompt, **kwargs):
        return b"fake_image_bytes"


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestProviderChain:
    def test_single_success_provider(self):
        chain = ProviderChain([AlwaysSuccessProvider()])
        result = asyncio.run(chain.analyze_poem("test poem"))
        assert result.theme == "Nature"
        assert result.mood == "Peaceful"

    def test_fallback_to_second_provider(self):
        chain = ProviderChain([AlwaysFailProvider(), AlwaysSuccessProvider()])
        result = asyncio.run(chain.analyze_poem("test poem"))
        assert result.theme == "Nature"

    def test_all_providers_fail(self):
        chain = ProviderChain([AlwaysFailProvider(), AlwaysFailProvider()])
        with pytest.raises(RuntimeError, match="All providers failed"):
            asyncio.run(chain.analyze_poem("test poem"))

    def test_empty_providers_raises(self):
        with pytest.raises(ValueError):
            ProviderChain([])

    def test_theme_override_propagated(self):
        class CaptureProvider(AIProvider):
            captured_override = None
            @property
            def name(self): return "capture"
            async def analyze_poem(self, poem, theme_override=None):
                CaptureProvider.captured_override = theme_override
                return PoemAnalysis("T","M","P","English")
            async def generate_image(self, prompt, **kwargs): return b""

        chain = ProviderChain([CaptureProvider()])
        asyncio.run(chain.analyze_poem("poem", theme_override="romantic"))
        assert CaptureProvider.captured_override == "romantic"

    def test_generate_image_fallback(self):
        chain = ProviderChain([AlwaysFailProvider(), AlwaysSuccessProvider()])
        result = asyncio.run(chain.generate_image("a beautiful garden"))
        assert result == b"fake_image_bytes"


class TestFallbackAnalyzer:
    def test_love_theme(self):
        result = _fallback_analyze("Our love blooms like roses in spring")
        assert result.theme == "Love"
        assert result.language == "English"

    def test_nature_theme(self):
        result = _fallback_analyze("The garden breathes in morning dew")
        assert result.theme == "Nature"

    def test_hindi_language_detection(self):
        result = _fallback_analyze("प्रेम का अहसास अनोखा है")
        assert result.language == "Hindi/Marathi"

    def test_theme_override(self):
        result = _fallback_analyze("some poem text", theme_override="mystical")
        assert result.theme == "Mystical"

    def test_image_prompt_not_empty(self):
        result = _fallback_analyze("A poem about hope and light")
        assert len(result.image_prompt) > 0
        assert isinstance(result.image_prompt, str)
