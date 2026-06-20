"""
Image Composer — Overlays handwritten poem text on a background image using Skia-Python.
Fixes Devanagari (Marathi/Hindi) shaping issues found in Pillow.
"""

import asyncio
import os
import skia
import numpy as np
from pathlib import Path
from PIL import Image, ImageFilter  # Keep PIL for some processing if needed, but Skia is primary
import re

# ---------------------------------------------------------------------------
# Font paths
# ---------------------------------------------------------------------------
ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

FONTS = {
    "devanagari": str(ASSETS_DIR / "NotoSansDevanagari-Regular.ttf"),
    "english":    str(ASSETS_DIR / "Caveat-Regular.ttf"),
}

def _detect_script(text: str) -> str:
    devanagari_re = re.compile(r"[\u0900-\u097F]")
    return "devanagari" if devanagari_re.search(text) else "english"

# ---------------------------------------------------------------------------
# Main compose function (Skia implementation)
# ---------------------------------------------------------------------------

async def compose_image(
    poem_text: str,
    bg_path: str,
    output_path: str,
    format: str = "square",
) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _compose_skia_sync, poem_text, bg_path, output_path, format)

def _compose_skia_sync(poem_text: str, bg_path: str, output_path: str, format: str):
    # --- Canvas dimensions ---
    W, H = (1080, 1920) if format == "story" else (1024, 1024)

    # --- Load & Prep Background using Skia ---
    data = skia.Data.MakeFromFileName(bg_path)
    if not data:
        raise ValueError(f"Could not load background image: {bg_path}")
    
    bg_image = skia.Image.MakeFromEncoded(data)
    
    surface = skia.Surface(W, H)
    canvas = surface.getCanvas()
    
    # Draw background with high-quality scaling
    rect = skia.Rect.MakeWH(W, H)
    canvas.drawImageRect(bg_image, rect, skia.SamplingOptions(skia.FilterMode.kLinear))

    # Apply a subtle dim for readability
    dim_paint = skia.Paint(
        Color=skia.ColorSetARGB(60, 0, 0, 0),
        AntiAlias=True
    )
    canvas.drawRect(rect, dim_paint)

    # --- Font Setup ---
    script = _detect_script(poem_text)
    font_path = FONTS.get(script, FONTS["english"])
    typeface = skia.Typeface.MakeFromFile(font_path)
    
    # Dynamic sizing logic
    char_count = len(poem_text)
    if char_count < 150: base_size = 54
    elif char_count < 300: base_size = 44
    elif char_count < 600: base_size = 34
    else: base_size = 28
    
    # --- Wrap & Layout ---
    max_line_width = W * 0.85
    lines = poem_text.strip().split("\n")
    final_lines = []
    
    font = skia.Font(typeface, base_size)
    
    # Simple wrap-by-word (since skia doesn't have a high-level manual wrapper like textwrap)
    for line in lines:
        words = line.split(" ")
        curr_line = ""
        for word in words:
            test_line = curr_line + (" " if curr_line else "") + word
            if font.measureText(test_line) <= max_line_width:
                curr_line = test_line
            else:
                final_lines.append(curr_line)
                curr_line = word
        final_lines.append(curr_line)

    line_height = base_size * 1.5
    total_height = len(final_lines) * line_height
    
    # Auto-shrink if too long
    while total_height > H * 0.8 and base_size > 18:
        base_size -= 2
        font = skia.Font(typeface, base_size)
        line_height = base_size * 1.5
        total_height = len(final_lines) * line_height

    # --- Draw Backdrop ---
    start_y = (H - total_height) // 2
    backdrop_margin = 40
    
    # Calculate max width for backdrop
    max_w = 0
    for l in final_lines:
        max_w = max(max_w, font.measureText(l))
    
    bd_rect = skia.Rect.MakeXYWH(
        (W - max_w) // 2 - backdrop_margin,
        start_y - backdrop_margin,
        max_w + (backdrop_margin * 2),
        total_height + (backdrop_margin * 1.5)
    )
    
    bd_paint = skia.Paint(
        Color=skia.ColorSetARGB(90, 0, 0, 0), # Semi-transparent black
        AntiAlias=True
    )
    canvas.drawRoundRect(bd_rect, 30, 30, bd_paint)

    # --- Draw Text ---
    text_paint = skia.Paint(
        Color=skia.ColorWHITE,
        AntiAlias=True,
    )
    
    shadow_paint = skia.Paint(
        Color=skia.ColorSetARGB(130, 0, 0, 0),
        AntiAlias=True
    )

    curr_y = start_y + base_size
    for line in final_lines:
        line_w = font.measureText(line)
        x = (W - line_w) // 2
        
        # Create a text blob for high-fidelity shaping (Devanagari support)
        blob = skia.TextBlob.MakeFromText(line, font)
        
        # Draw shadow
        canvas.drawTextBlob(blob, x + 2, curr_y + 2, shadow_paint)
        # Draw main text
        canvas.drawTextBlob(blob, x, curr_y, text_paint)
        
        curr_y += line_height

    # --- Save ---
    image = surface.makeImageSnapshot()
    result_data = image.encodeToData(skia.EncodedImageFormat.kPNG, 100)
    if result_data:
        with open(output_path, "wb") as f:
            f.write(bytes(result_data))
