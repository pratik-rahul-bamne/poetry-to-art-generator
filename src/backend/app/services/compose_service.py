"""
Compose Service — wraps the Skia-Python image composition logic.
Thin adapter so routes don't import Skia directly.
"""

from backend.app.core.logger import get_logger

logger = get_logger("compose")

# Re-export compose_image from the original implementation
# This preserves all existing Devanagari + Skia logic without duplication
try:
    from backend.services.composer import compose_image
    logger.info("Using Skia-Python composer (Devanagari-safe) ✓")
except ImportError:
    logger.warning("Skia-Python not available — using PIL fallback composer")
    from backend.app.services._pil_composer import compose_image  # noqa: F401


__all__ = ["compose_image"]
