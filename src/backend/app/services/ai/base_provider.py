"""
Base AI Provider — Abstract interface that all AI providers must implement.

This abstraction layer prevents vendor lock-in. To switch from Gemini to
OpenAI or Claude, only the provider implementation changes — not the callers.

Usage:
    provider = GeminiProvider()
    analysis = await provider.analyze_poem("Roses are red...")
    image_bytes = await provider.generate_image("A garden at sunrise...")
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PoemAnalysis:
    """Structured result from poem analysis."""
    theme: str
    mood: str
    image_prompt: str
    language: str


class AIProvider(ABC):
    """
    Abstract base class for all AI provider implementations.

    Every provider (Gemini, OpenAI, Claude, Local) must implement:
    - analyze_poem: NLP analysis to extract theme, mood, visual prompt
    - generate_image: Text-to-image generation

    Providers should also implement graceful degradation — if the primary
    method fails, they should raise an exception so the caller can try the
    next provider in the chain.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging and provider logs."""
        ...

    @abstractmethod
    async def analyze_poem(
        self,
        poem: str,
        theme_override: str | None = None,
    ) -> PoemAnalysis:
        """
        Analyze a poem and extract visual metadata.

        Args:
            poem: The raw poem text (any language).
            theme_override: Optional user-selected theme to force.

        Returns:
            PoemAnalysis with theme, mood, image_prompt, language.
        """
        ...

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        **kwargs,
    ) -> bytes:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Descriptive visual prompt.
            **kwargs: Provider-specific parameters (size, steps, style, etc.)

        Returns:
            PNG/JPEG image bytes.
        """
        ...


class ProviderChain:
    """
    Fallback chain — tries providers in order until one succeeds.

    Example:
        chain = ProviderChain([GeminiProvider(), LocalProvider()])
        analysis = await chain.analyze_poem(poem)
    """

    def __init__(self, providers: list[AIProvider]):
        if not providers:
            raise ValueError("At least one provider is required")
        self.providers = providers

    async def analyze_poem(self, poem: str, theme_override: str | None = None) -> PoemAnalysis:
        """Try each provider in order, returning the first success."""
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                return await provider.analyze_poem(poem, theme_override)
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(
            f"All providers failed. Last error: {last_error}"
        ) from last_error

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """Try each provider in order, returning the first success."""
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                return await provider.generate_image(prompt, **kwargs)
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(
            f"All image providers failed. Last error: {last_error}"
        ) from last_error
