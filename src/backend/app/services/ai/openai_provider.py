"""
OpenAI Provider — stub implementation for future OpenAI GPT-4 + DALL-E integration.
Implements the AIProvider abstract interface.

To activate:
1. pip install openai
2. Set OPENAI_API_KEY in .env
3. Replace stub implementations below
"""

from backend.app.services.ai.base_provider import AIProvider, PoemAnalysis
from backend.app.core.logger import get_logger

logger = get_logger("ai")


class OpenAIProvider(AIProvider):
    """
    OpenAI provider — GPT-4o for analysis, DALL-E 3 for image generation.
    
    Currently a stub. Activate by implementing the methods below.
    """

    @property
    def name(self) -> str:
        return "openai"

    async def analyze_poem(
        self,
        poem: str,
        theme_override: str | None = None,
    ) -> PoemAnalysis:
        """
        TODO: Implement using GPT-4o with JSON mode.
        
        Example implementation:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = await client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}]
            )
        """
        raise NotImplementedError(
            "OpenAI provider is not yet implemented. "
            "Set OPENAI_API_KEY and implement this method."
        )

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """
        TODO: Implement using DALL-E 3.
        
        Example implementation:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
            )
            import httpx
            async with httpx.AsyncClient() as hc:
                img = await hc.get(response.data[0].url)
            return img.content
        """
        raise NotImplementedError(
            "OpenAI image generation is not yet implemented."
        )
