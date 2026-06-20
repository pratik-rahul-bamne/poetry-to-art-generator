# 🎨 Background Generation — Based on Poem Content

## What Changed

Previously, if image generation failed, the app would show a **solid blue fallback** (RGB 30, 60, 110) that had nothing to do with your poem.

Now, the fallback is **poem-aware** and generates a gradient background based on the mood/theme extracted from your poem.

---

## How It Works

### Pipeline
```
Poem Text
   ↓
NLP Analysis (Gemini/FLAN-T5/Fallback)
   ↓
Extract: Theme, Mood, Visual Prompt
   ↓
Generate Image (Pollinations/HF/Stable Diffusion)
   ↓
If generation fails → Poem-aware gradient fallback
```

### Mood-Based Color Palettes

Your background color now adapts to your poem:

| Mood Keywords | Colors | Style |
|---------------|--------|-------|
| `dark`, `night`, `sad`, `melancholy` | Purple → Deep purple | Dark contemplative |
| `warm`, `sunset`, `golden`, `love`, `romantic` | Brown → Orange → Gold | Warm & inviting |
| `nature`, `green`, `forest` | Green → Blue → Light Blue | Natural & serene |
| `ocean`, `water`, `sky` | Sky blue → Teal → Navy | Aquatic & calm |
| Default (no keywords) | Blue gradient | Neutral fallback |

---

## Example Flows

### Example 1: Love Poem
```
Input: "Roses are red, violets are blue, love fills my heart..."
↓
NLP: mood = "romantic"
↓
Prompt: "romantic scene with warmth and affection..."
↓
Image Generation: Pollinations API generates image
↓
If Pollinations fails → Golden/warm gradient (not blue!)
```

### Example 2: Night Poem
```
Input: "The moon whispers to the silent night, darkness falls..."
↓
NLP: mood = "melancholic, dark"
↓
Prompt: "dark mysterious night, soft moonlight..."
↓
Image Generation: Attempt API
↓
If fails → Dark purple gradient matching the mood
```

### Example 3: Nature Poem
```
Input: "Green forests, flowing rivers, birds sing..."
↓
NLP: mood = "peaceful, natural"
↓
Prompt: "serene forest with water and natural light..."
↓
Image Generation: Attempt API
↓
If fails → Green-to-blue nature gradient
```

---

## Technical Details

### Gradient Generation Algorithm

```python
# For each pixel y from 0 to 1023:
# 1. Pick two adjacent colors from mood palette
# 2. Blend between them (0.0 to 1.0)
# 3. Fill horizontal line with that color
# Result: smooth vertical gradient that evolves from one color to another
```

### Logging

Enable debug output to see what's happening:

```
[IMAGE GEN] Analyzing poem to generate prompt...
[IMAGE GEN] Generated prompt from poem: romantic scene with warmth...
[IMAGE GEN] Final prompt: romantic scene with warmth..., aesthetic, photographic...
[IMAGE GEN] Using provider: pollinations
```

If Pollinations fails:
```
Pollinations API failed (timeout/error), generating poem-themed fallback...
[IMAGE GEN] ✓ Image saved: bg_a1b2c3d4.png
```

---

## Configuration

To control background generation, use these env vars:

```bash
# .env

# Use free local Stable Diffusion (best quality, no API limits)
IMAGE_PROVIDER=stable-diffusion

# Or use Pollinations cloud free tier (faster but rate-limited)
IMAGE_PROVIDER=pollinations

# Or use HuggingFace (requires token)
IMAGE_PROVIDER=huggingface
HF_API_TOKEN=hf_xxxxx
```

---

## Comparison: Before vs After

### Before
```
❌ Poem: "Dark melancholy night..."
❌ Fallback: Solid blue (30, 60, 110)
❌ User sees: Generic blue, no mood match
```

### After
```
✅ Poem: "Dark melancholy night..."
✅ Fallback: Dark purple gradient (20→60→100 on each channel)
✅ User sees: Mood-matched aesthetic background
```

---

## Why This Matters

1. **No more generic blue** — Your background now reflects the poem's emotional tone
2. **Graceful fallback** — Even if APIs fail, the result looks intentional, not broken
3. **Always poem-aware** — Every background is generated from your poem's meaning
4. **Multiple providers** — Choose Pollinations (cloud), HuggingFace (SDXL), or local Stable Diffusion

---

## Next Steps

To get the **best quality** backgrounds:

1. **Free local (best for offline):**
   ```bash
   pip install diffusers transformers torch accelerate
   # Set: IMAGE_PROVIDER=stable-diffusion
   ```

2. **Cloud free tier (fast, limited):**
   ```bash
   # Set: IMAGE_PROVIDER=pollinations
   # No setup needed, uses free tier
   ```

3. **HuggingFace (highest quality):**
   ```bash
   # Get token from huggingface.co
   # Set: HF_API_TOKEN=hf_xxxxx
   # Set: IMAGE_PROVIDER=huggingface
   ```

---

**Summary:** Your backgrounds are now fully **poem-driven** — from the initial prompt generation to the fallback mood-based gradient. No more mysterious blue!
