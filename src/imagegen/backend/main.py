"""
ImageGen2 Clone - FastAPI Backend
Powered by Stable Diffusion 1.5 (CPU optimized)
"""

import os
import io
import base64
import time
import uuid
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)s │ %(message)s")
log = logging.getLogger("imagegen")

# ─── App Setup ───────────────────────────────────────────────────────────────
app = FastAPI(title="ImageGen2 Clone API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
OUTPUT_DIR   = BASE_DIR / "outputs"
HISTORY_FILE = BASE_DIR / "history.json"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── Serve Frontend Static Files (must be at module level) ───────────────────
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# ─── Global State ────────────────────────────────────────────────────────────
pipeline = None
pipeline_loading = False
pipeline_ready = False
generation_queue: asyncio.Queue = None
current_job: dict = None

# ─── Models ──────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = "blurry, bad quality, distorted, ugly, deformed, low resolution, watermark, text, nsfw"
    width: int = 512
    height: int = 512
    steps: int = 20
    guidance_scale: float = 7.5
    seed: int = -1
    style: str = "none"
    num_images: int = 1

class GenerateResponse(BaseModel):
    job_id: str
    status: str
    message: str

# ─── Style Prompts ───────────────────────────────────────────────────────────
STYLE_PROMPTS = {
    "none": "",
    "photorealistic": ", photorealistic, 8k uhd, sharp focus, professional photography, DSLR, high detail",
    "anime": ", anime style, manga illustration, vibrant colors, Studio Ghibli, cel-shaded",
    "oil_painting": ", oil painting, classical art, fine brushstrokes, rich texture, museum quality",
    "watercolor": ", watercolor painting, soft washes, delicate colors, artistic, flowing",
    "digital_art": ", digital art, concept art, artstation, highly detailed, cinematic lighting",
    "3d_render": ", 3D render, octane render, unreal engine 5, ray tracing, photorealistic CGI",
    "sketch": ", pencil sketch, hand-drawn, graphite, detailed linework, artistic",
    "pixel_art": ", pixel art, 16-bit, retro game style, detailed pixels",
    "cinematic": ", cinematic shot, movie still, dramatic lighting, anamorphic lens, film grain, ultra wide",
}

# ─── History ─────────────────────────────────────────────────────────────────
def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except:
            return []
    return []

def save_history(history: list):
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")

# ─── Pipeline Loader ─────────────────────────────────────────────────────────
def load_pipeline():
    global pipeline, pipeline_ready, pipeline_loading
    pipeline_loading = True
    try:
        log.info("Loading Stable Diffusion pipeline (CPU mode)...")
        from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
        import torch

        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
        )

        # CPU Optimizations
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        pipe.enable_attention_slicing(1)

        pipe = pipe.to("cpu")
        pipeline = pipe
        pipeline_ready = True
        log.info("✅ Pipeline loaded and ready!")
    except Exception as e:
        log.error(f"❌ Pipeline load failed: {e}")
        pipeline_loading = False
        raise

# ─── Job Store ───────────────────────────────────────────────────────────────
jobs: dict = {}

async def run_generation(job_id: str, req: GenerateRequest):
    global jobs, current_job
    import torch

    jobs[job_id]["status"] = "generating"
    jobs[job_id]["progress"] = 5
    current_job = job_id
    start_time = time.time()

    try:
        # Build full prompt
        style_suffix = STYLE_PROMPTS.get(req.style, "")
        full_prompt = req.prompt + style_suffix

        log.info(f"🎨 Generating: '{full_prompt[:60]}...' [{req.width}x{req.height}, {req.steps} steps]")

        # Seed
        generator = None
        if req.seed != -1:
            generator = torch.Generator("cpu").manual_seed(req.seed)
            jobs[job_id]["seed"] = req.seed
        else:
            actual_seed = torch.randint(0, 2**32, (1,)).item()
            generator = torch.Generator("cpu").manual_seed(actual_seed)
            jobs[job_id]["seed"] = int(actual_seed)

        # Progress callback
        def step_callback(step, timestep, latents):
            progress = int(5 + (step / req.steps) * 85)
            jobs[job_id]["progress"] = progress
            jobs[job_id]["step"] = step
            jobs[job_id]["total_steps"] = req.steps

        images = pipeline(
            prompt=full_prompt,
            negative_prompt=req.negative_prompt,
            width=req.width,
            height=req.height,
            num_inference_steps=req.steps,
            guidance_scale=req.guidance_scale,
            generator=generator,
            num_images_per_prompt=req.num_images,
            callback=step_callback,
            callback_steps=1,
        ).images

        # Save images
        saved = []
        for i, img in enumerate(images):
            filename = f"{job_id}_{i}.png"
            filepath = OUTPUT_DIR / filename
            img.save(filepath, "PNG")
            saved.append(filename)

        elapsed = time.time() - start_time
        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["images"] = saved
        jobs[job_id]["time_taken"] = round(elapsed, 1)
        log.info(f"✅ Done in {elapsed:.1f}s → {saved}")

        # Save to history
        history = load_history()
        history.insert(0, {
            "id": job_id,
            "prompt": req.prompt,
            "full_prompt": full_prompt,
            "style": req.style,
            "width": req.width,
            "height": req.height,
            "steps": req.steps,
            "guidance_scale": req.guidance_scale,
            "seed": jobs[job_id]["seed"],
            "images": saved,
            "time_taken": round(elapsed, 1),
            "created_at": datetime.now().isoformat(),
        })
        save_history(history[:100])  # Keep last 100

    except Exception as e:
        log.error(f"❌ Generation error: {e}")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
    finally:
        current_job = None

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global generation_queue
    generation_queue = asyncio.Queue()
    log.info("🚀 ImageGen2 Clone API started")
    log.info(f"📂 Frontend dir: {FRONTEND_DIR} (exists={FRONTEND_DIR.exists()})")
    log.info("📌 SD pipeline will load on first Generate click")

@app.get("/")
async def root():
    idx = FRONTEND_DIR / "index.html"
    if idx.exists():
        return FileResponse(str(idx), media_type="text/html")
    return {"message": "ImageGen2 Clone API is running!", "docs": "/docs"}

@app.get("/style.css")
async def serve_css():
    f = FRONTEND_DIR / "style.css"
    return FileResponse(str(f), media_type="text/css") if f.exists() else JSONResponse({}, 404)

@app.get("/app.js")
async def serve_js():
    f = FRONTEND_DIR / "app.js"
    return FileResponse(str(f), media_type="application/javascript") if f.exists() else JSONResponse({}, 404)

@app.get("/api/status")
async def api_status():
    return {
        "pipeline_ready": pipeline_ready,
        "pipeline_loading": pipeline_loading,
        "current_job": current_job,
        "queue_size": len([j for j in jobs.values() if j["status"] == "pending"]),
    }

@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    global pipeline, pipeline_ready, pipeline_loading

    # Validate
    if not req.prompt.strip():
        raise HTTPException(400, "Prompt cannot be empty")
    if req.width not in [256, 384, 512, 640, 768]:
        req.width = 512
    if req.height not in [256, 384, 512, 640, 768]:
        req.height = 512
    req.steps = max(5, min(50, req.steps))
    req.num_images = max(1, min(4, req.num_images))

    # Load pipeline if needed
    if not pipeline_ready and not pipeline_loading:
        import threading
        t = threading.Thread(target=load_pipeline, daemon=True)
        t.start()
        # Wait for it to start loading
        await asyncio.sleep(2)

    # Create job
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "status": "pending" if not pipeline_ready else "queued",
        "progress": 0,
        "prompt": req.prompt,
        "images": [],
        "seed": req.seed,
        "created_at": datetime.now().isoformat(),
    }

    if not pipeline_ready:
        # Queue it — check back in a bit
        jobs[job_id]["status"] = "loading_model"
        background_tasks.add_task(_wait_and_generate, job_id, req)
    else:
        background_tasks.add_task(run_generation, job_id, req)

    return GenerateResponse(
        job_id=job_id,
        status=jobs[job_id]["status"],
        message="Generation started! CPU mode may take 2-5 minutes per image." if pipeline_ready else "Loading model first (one-time, ~30-60s)..."
    )

async def _wait_and_generate(job_id: str, req: GenerateRequest):
    """Wait for pipeline to load, then generate."""
    for _ in range(120):  # wait up to 2 min
        if pipeline_ready:
            break
        await asyncio.sleep(1)
    if pipeline_ready:
        await run_generation(job_id, req)
    else:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = "Pipeline failed to load"

@app.get("/api/job/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]

@app.get("/api/image/{filename}")
async def get_image(filename: str):
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(str(filepath), media_type="image/png")

@app.get("/api/history")
async def get_history():
    return load_history()

@app.delete("/api/history/{item_id}")
async def delete_history_item(item_id: str):
    history = load_history()
    history = [h for h in history if h["id"] != item_id]
    save_history(history)
    return {"ok": True}

@app.get("/api/styles")
async def get_styles():
    return [
        {"id": "none", "name": "None", "icon": "✨"},
        {"id": "photorealistic", "name": "Photorealistic", "icon": "📷"},
        {"id": "anime", "name": "Anime", "icon": "🎌"},
        {"id": "oil_painting", "name": "Oil Painting", "icon": "🎨"},
        {"id": "watercolor", "name": "Watercolor", "icon": "💧"},
        {"id": "digital_art", "name": "Digital Art", "icon": "🖥️"},
        {"id": "3d_render", "name": "3D Render", "icon": "🎲"},
        {"id": "sketch", "name": "Sketch", "icon": "✏️"},
        {"id": "pixel_art", "name": "Pixel Art", "icon": "👾"},
        {"id": "cinematic", "name": "Cinematic", "icon": "🎬"},
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
