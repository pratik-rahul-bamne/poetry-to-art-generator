"""
AI Poem Visualizer — FastAPI Backend
Entry point: run with `uvicorn backend.main:app --reload --port 8000`
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.api.routes import router
from backend.database import init_db

from fastapi.responses import RedirectResponse
from backend.api.imagegen import router as imagegen_router

# Initialize SQLite database
init_db()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Poem Visualizer",
    description="Turn poems into aesthetic AI-generated artwork",
    version="1.0.0",
)

# Allow all origins during development (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Ensure output directory exists
# ---------------------------------------------------------------------------
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
app.include_router(router, prefix="/api")
app.include_router(imagegen_router, prefix="/api/imagegen")


@app.get("/imagegen", include_in_schema=False)
async def imagegen_redirect():
    return RedirectResponse(url="/imagegen/")


# ---------------------------------------------------------------------------
# Serve frontend static files
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
IMAGEGEN_FRONTEND_DIR = Path(__file__).parent.parent / "imagegen" / "frontend"

# Mount imagegen static folder
if IMAGEGEN_FRONTEND_DIR.exists():
    app.mount("/imagegen", StaticFiles(directory=str(IMAGEGEN_FRONTEND_DIR), html=True), name="imagegen_frontend")

# Mount outputs so the frontend can display generated images
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# Serve the frontend SPA
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
