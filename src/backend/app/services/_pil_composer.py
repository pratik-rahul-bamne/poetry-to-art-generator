"""
PIL Fallback Composer — Overlays poem text on a background image using Pillow.
Used when Skia-Python is not installed or functional.
"""

import asyncio
import os
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Font paths
ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets" / "fonts"

FONTS = {
    "devanagari": str(ASSETS_DIR / "NotoSansDevanagari-Regular.ttf"),
    "english":    str(ASSETS_DIR / "Caveat-Regular.ttf"),
}

def _detect_script(text: str) -> str:
    devanagari_re = re.compile(r"[\u0900-\u097F]")
    return "devanagari" if devanagari_re.search(text) else "english"

async def compose_image(
    poem_text: str,
    bg_path: str,
    output_path: str,
    format: str = "square",
) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _compose_pil_sync, poem_text, bg_path, output_path, format)

def _compose_pil_sync(poem_text: str, bg_path: str, output_path: str, format: str):
    # Canvas dimensions
    W, H = (1080, 1920) if format == "story" else (1024, 1024)

    # Load & Prep Background
    if not os.path.exists(bg_path):
        raise ValueError(f"Could not load background image: {bg_path}")
    
    bg_img = Image.open(bg_path).convert("RGBA")
    
    # Draw background with high-quality scaling
    bg_img = bg_img.resize((W, H), Image.Resampling.LANCZOS)
    
    # Create an overlay for drawing
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Apply a subtle dim to the entire canvas for readability
    draw.rectangle([0, 0, W, H], fill=(0, 0, 0, 60))

    # Font Setup
    script = _detect_script(poem_text)
    font_path = FONTS.get(script, FONTS["english"])
    
    # Dynamic sizing logic
    char_count = len(poem_text)
    if char_count < 150: base_size = 54
    elif char_count < 300: base_size = 44
    elif char_count < 600: base_size = 34
    else: base_size = 28

    def get_text_width(text: str, font) -> int:
        if not text:
            return 0
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    def get_text_height(text: str, font) -> int:
        if not text:
            return 0
        bbox = font.getbbox(text)
        return bbox[3] - bbox[1]

    # Wrap & Layout
    max_line_width = W * 0.85
    lines = poem_text.strip().split("\n")
    final_lines = []
    
    font = ImageFont.truetype(font_path, base_size)
    
    # Simple wrap-by-word
    for line in lines:
        words = line.split(" ")
        curr_line = ""
        for word in words:
            test_line = curr_line + (" " if curr_line else "") + word
            if get_text_width(test_line, font) <= max_line_width:
                curr_line = test_line
            else:
                final_lines.append(curr_line)
                curr_line = word
        final_lines.append(curr_line)

    # Filter out empty lines at the end if any
    final_lines = [l for l in final_lines if l.strip() != ""]

    # Calculate height
    # Use max height of single characters or standard line height
    sample_bbox = font.getbbox("Aygj")
    char_h = sample_bbox[3] - sample_bbox[1] if sample_bbox else base_size
    line_height = int(char_h * 1.5)
    total_height = len(final_lines) * line_height
    
    # Auto-shrink if too long
    while total_height > H * 0.8 and base_size > 18:
        base_size -= 2
        font = ImageFont.truetype(font_path, base_size)
        sample_bbox = font.getbbox("Aygj")
        char_h = sample_bbox[3] - sample_bbox[1] if sample_bbox else base_size
        line_height = int(char_h * 1.5)
        total_height = len(final_lines) * line_height

    # Draw Backdrop
    start_y = (H - total_height) // 2
    backdrop_margin = 40
    
    # Calculate max width for backdrop
    max_w = 0
    for l in final_lines:
        max_w = max(max_w, get_text_width(l, font))
    
    bd_rect = [
        (W - max_w) // 2 - backdrop_margin,
        start_y - backdrop_margin,
        (W - max_w) // 2 + max_w + backdrop_margin,
        start_y + total_height + backdrop_margin // 2
    ]
    
    # Semi-transparent black rounded rectangle for backdrop
    draw.rounded_rectangle(bd_rect, radius=20, fill=(0, 0, 0, 120))

    # Draw Text
    curr_y = start_y
    for line in final_lines:
        line_w = get_text_width(line, font)
        x = (W - line_w) // 2
        
        # Draw shadow (offset by 2 pixels)
        draw.text((x + 2, curr_y + 2), line, font=font, fill=(0, 0, 0, 200))
        # Draw main text
        draw.text((x, curr_y), line, font=font, fill=(255, 255, 255, 255))
        
        curr_y += line_height

    # Composite overlay on background
    final_img = Image.alpha_composite(bg_img, overlay)
    
    # Save as PNG
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_img.convert("RGB").save(output_path, "PNG")
