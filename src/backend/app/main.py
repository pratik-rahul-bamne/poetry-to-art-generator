"""
AI Poem Visualizer — FastAPI Application v2.0
Production-ready entry point with Clean Architecture.

Run with:
    uvicorn backend.app.main:app --reload --port 8000

Legacy command (still works via the root main.py shim):
    uvicorn backend.main:app --reload --port 8000
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from backend.app.core.config import settings
from backend.app.core.logger import get_logger
from backend.app.database import init_db
from backend.app.middleware.auth_middleware import AuthMiddleware
from backend.app.middleware.rate_limit import RateLimitMiddleware

# API v1 routers
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.poems import router as poems_router
from backend.app.api.v1.generation import router as generation_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.admin import router as admin_router

# Legacy routers (backward compat)
from backend.api.routes import router as legacy_router
from backend.api.imagegen import router as imagegen_router

logger = get_logger("api")

# ── Initialize database ───────────────────────────────────────────────────────
init_db()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Transform poems into stunning AI-generated artwork. "
        "Supports English, Hindi, and Marathi. "
        "Powered by Gemini + Stable Diffusion."
    ),
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Custom middleware (order matters: outer → inner) ──────────────────────────
app.add_middleware(RateLimitMiddleware)  # runs after auth so user role is available
app.add_middleware(AuthMiddleware)       # runs first, populates request.state.user

# ── API v1 routes ─────────────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"
app.include_router(auth_router,       prefix=API_V1_PREFIX)
app.include_router(poems_router,      prefix=API_V1_PREFIX)
app.include_router(generation_router, prefix=API_V1_PREFIX)
app.include_router(users_router,      prefix=API_V1_PREFIX)
app.include_router(admin_router,      prefix=API_V1_PREFIX)

# ── Legacy /api/* routes (backward compatibility) ─────────────────────────────
app.include_router(legacy_router,   prefix="/api")
app.include_router(imagegen_router, prefix="/api/imagegen")

# ── Ensure output dir exists ──────────────────────────────────────────────────
settings.OUTPUTS_DIR.mkdir(exist_ok=True)

# ── Root redirect & health ────────────────────────────────────────────────────
@app.get("/imagegen", include_in_schema=False)
async def imagegen_redirect():
    return RedirectResponse(url="/imagegen/")


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }


# ── Static file serving ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.parent  # project root

FRONTEND_DIR = BASE_DIR / "frontend"
IMAGEGEN_FRONTEND_DIR = BASE_DIR / "imagegen" / "frontend"

# Mount imagegen sub-app
if IMAGEGEN_FRONTEND_DIR.exists():
    app.mount(
        "/imagegen",
        StaticFiles(directory=str(IMAGEGEN_FRONTEND_DIR), html=True),
        name="imagegen_frontend",
    )

# Mount output images
app.mount(
    "/outputs",
    StaticFiles(directory=str(settings.OUTPUTS_DIR)),
    name="outputs",
)

# Mount main frontend SPA (must be last)
app.mount(
    "/",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend",
)

logger.info(
    "%s v%s started in %s mode",
    settings.APP_NAME, settings.APP_VERSION, settings.APP_ENV,
)
