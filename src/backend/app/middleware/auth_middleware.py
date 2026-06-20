"""
Auth Middleware — extracts JWT from Authorization header and sets request.state.user.
Non-blocking: public endpoints work without a token (user is None).
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.app.core.security import decode_access_token
from backend.app.core.logger import get_logger

logger = get_logger("auth")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Extracts the Bearer token from every request and populates request.state.user.

    - If token is valid: request.state.user = {"sub": user_id, "role": role}
    - If token is missing or invalid: request.state.user = None
    
    Routes that require auth should call get_current_user() dependency
    (in api/v1/auth.py) rather than reading state directly.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_access_token(token)
                request.state.user = payload
            except ValueError:
                # Invalid token — leave user as None (public access still works)
                pass

        return await call_next(request)
