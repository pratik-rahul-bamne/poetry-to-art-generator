import os
import io
import time
import uuid
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.services.image_service import (
    is_sd_ready,
    is_sd_loading,
    preload_sd_pipeline,
    get_sd_pipeline,
    SD_STYLE_PROMPTS,
)

log = logging.getLogger("imagegen")

router = APIRouter()

# ─── Paths ───────────────────────────────────────────────────────────────────
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

HISTORY_FILE = Path(__file__).parent.parent.parent / "imagegen_history.json"

# ─── Global State ────────────────────────────────────────────────────────────
jobs: dict = {}
current_job: Optional[str] = None

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

# ─── Job Store & Runner ──────────────────────────────────────────────────────
def run_generation(job_id: str, req: GenerateRequest):
    global jobs, current_job
    import torch

    jobs[job_id]["status"] = "generating"
    jobs[job_id]["progress"] = 5
    current_job = job_id
    start_time = time.time()

    try:
        # Load shared pipeline (thread-safe, checks if ready)
        pipe = get_sd_pipeline()

        # Build full prompt
        style_suffix = SD_STYLE_PROMPTS.get(req.style, "")
        full_prompt = req.prompt + style_suffix

        log.info(f"🎨 Generating ImageGen2: '{full_prompt[:60]}...' [{req.width}x{req.height}, {req.steps} steps]")

        # Seed
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

        images = pipe(
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
            filepath = OUTPUTS_DIR / filename
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

async def _wait_and_generate(job_id: str, req: GenerateRequest):
    """Wait for pipeline to load, then generate using threadpool to prevent blocking event loop."""
    for _ in range(120):  # wait up to 2 min
        if is_sd_ready():
            break
        await asyncio.sleep(1)
    if is_sd_ready():
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, run_generation, job_id, req)
    else:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = "Pipeline failed to load"

# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/status")
async def api_status():
    return {
        "pipeline_ready": is_sd_ready(),
        "pipeline_loading": is_sd_loading(),
        "current_job": current_job,
        "queue_size": len([j for j in jobs.values() if j["status"] == "pending"]),
    }

@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
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
    if not is_sd_ready() and not is_sd_loading():
        preload_sd_pipeline()
        # Wait for loading thread to start
        await asyncio.sleep(2)

    # Create job
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "status": "pending" if not is_sd_ready() else "queued",
        "progress": 0,
        "prompt": req.prompt,
        "images": [],
        "seed": req.seed,
        "created_at": datetime.now().isoformat(),
    }

    if not is_sd_ready():
        # Queue it — check back in a bit
        jobs[job_id]["status"] = "loading_model"
        background_tasks.add_task(_wait_and_generate, job_id, req)
    else:
        # Run sync function in thread pool directly via BackgroundTasks
        background_tasks.add_task(run_generation, job_id, req)

    return GenerateResponse(
        job_id=job_id,
        status=jobs[job_id]["status"],
        message="Generation started! CPU mode may take 2-5 minutes per image." if is_sd_ready() else "Loading model first (one-time, ~30-60s)..."
    )

@router.get("/job/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]

@router.get("/image/{filename}")
async def get_image(filename: str):
    filepath = OUTPUTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(str(filepath), media_type="image/png")

@router.get("/history")
async def get_history():
    return load_history()

@router.delete("/history/{item_id}")
async def delete_history_item(item_id: str):
    history = load_history()
    history = [h for h in history if h["id"] != item_id]
    save_history(history)
    return {"ok": True}

@router.get("/styles")
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
