# 🎨 ImageGen AI — Your Own Local Image Generation

A **ChatGPT Image Gen 2-style** AI image generation app that runs **100% locally** on your machine using **Stable Diffusion 1.5**.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🧠 Model | Stable Diffusion 1.5 (runwayml) |
| 🖥️ Mode | CPU (no GPU required) |
| 🎨 Styles | 10 built-in styles (Anime, Photorealistic, Oil Paint, etc.) |
| 📐 Sizes | 256×256, 384×384, 512×512, 640×640, 512×768, 768×512 |
| 🔢 Batch | Generate 1, 2, or 4 images at once |
| 🎲 Seeds | Reproducible generation with fixed seeds |
| 📜 History | Auto-saved locally, browse past generations |
| 🔒 Privacy | Everything runs on your device — nothing sent to cloud |

---

## 🚀 Quick Start

### Option 1: Double-click (Windows)
```
Double-click: start.bat
```

### Option 2: Manual
```bash
# Install deps (first time only)
pip install -r requirements.txt

# Start server
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Open browser
http://localhost:8000
```

---

## ⏱ Performance on Your Machine

| Setting | Time per Image |
|---|---|
| 5 steps (draft) | ~30-60 seconds |
| 20 steps (default) | ~3-6 minutes |
| 50 steps (quality) | ~8-15 minutes |

> **Tip:** Use 10-15 steps for quick previews, 20-30 for final images.

---

## 🔧 Model Download

The first time you click "Generate", the model will automatically download:
- **Stable Diffusion 1.5** (~4 GB)
- Downloaded to: `~/.cache/huggingface/`
- Only happens once!

---

## 📁 Project Structure

```
imagegen/
├── backend/
│   ├── main.py          ← FastAPI server + SD pipeline
│   └── outputs/         ← Generated images saved here
├── frontend/
│   ├── index.html       ← ChatGPT-style UI
│   ├── style.css        ← Premium dark theme
│   └── app.js           ← Frontend logic
├── requirements.txt
├── start.bat            ← One-click launcher (Windows)
└── README.md
```

---

## 🎨 Style Guide

| Style | Best For |
|---|---|
| None | Raw model output |
| Photorealistic | Portrait/landscape photos |
| Anime | Manga/anime characters |
| Oil Painting | Classical art style |
| Watercolor | Soft, artistic scenes |
| Digital Art | Concept art, characters |
| 3D Render | Product/object visualization |
| Cinematic | Movie stills, dramatic scenes |
| Sketch | Line art, drawings |
| Pixel Art | Retro game art |

---

## 💡 Prompt Tips

**Good prompt structure:**
```
[subject], [scene/setting], [lighting], [style], [quality modifiers]
```

**Example:**
```
A beautiful cat sitting on a window sill, golden hour lighting, 
bokeh background, professional photography, sharp focus
```
