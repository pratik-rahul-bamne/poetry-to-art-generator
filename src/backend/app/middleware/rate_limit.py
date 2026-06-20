"""
Rate Limiting Middleware — per-IP request throttling.
In-memory implementation (upgradeable to Redis for multi-worker deployments).
"""

import time
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger("api")

# ── In-memory rate limit store ─────────────────────────────────────────────────
# Structure: {ip: [(timestamp, count), ...]}
_WINDOW_SECONDS = 3600  # 1 hour
_store: dict[str, list[float]] = defaultdict(list)

# Only rate-limit generation endpoints (expensive AI calls)
_RATE_LIMITED_PREFIXES = ("/api/v1/generate-image", "/api/v1/compose", "/api/v1/analyze")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter.
    
    Limits:
        - Guest users: settings.RATE_LIMIT_GUEST requests / hour
        - Registered users: settings.RATE_LIMIT_REGISTERED requests / hour
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only rate-limit the AI generation endpoints
        path = request.url.path
        if not any(path.startswith(p) for p in _RATE_LIMITED_PREFIXES):
            return await call_next(request)

        # Determine limit based on auth status
        user = getattr(request.state, "user", None)
        limit = settings.RATE_LIMIT_REGISTERED if user else settings.RATE_LIMIT_GUEST

        ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Sliding window: remove entries older than 1 hour
        _store[ip] = [t for t in _store[ip] if now - t < _WINDOW_SECONDS]

        if len(_store[ip]) >= limit:
            logger.warning("Rate limit exceeded for IP=%s path=%s", ip, path)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded: {limit} requests per hour. "
                        "Please wait before generating again."
                    )
                },
            )

        _store[ip].append(now)
        return await call_next(request)
