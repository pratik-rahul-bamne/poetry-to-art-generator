import asyncio
import os
import sys

# Ensure backend can be imported
sys.path.append(os.getcwd())

from backend.app.services.compose_service import compose_image

async def test_hindi_marathi_shaping():
    print("Testing Hindi/Marathi shaping...")
    
    # Test text with typical conjuncts and vowels
    test_text = "मी मराठी मध्ये लिहित आहे.\n(I am writing in Marathi)\n\nहिंदी में भी: शुभ प्रभात!"
    
    from pathlib import Path
    output_dir = Path(__file__).parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    output_test = str(output_dir / "test_devanagari.png")
    
    # Check for a candidate background file
    bg_candidates = [
        str(output_dir / "sample_bg.png"),
        str(Path(__file__).parent.parent / "frontend" / "assets" / "bg.jpg")
    ]
    bg_path = None
    for path in bg_candidates:
        if os.path.exists(path):
            bg_path = path
            break
            
    if not bg_path:
        # Create a simple solid color background with PIL if no bg exists
        from PIL import Image
        bg_path = str(output_dir / "test_dummy_bg.png")
        img = Image.new('RGB', (1024, 1024), color = (73, 109, 137))
        img.save(bg_path)
        print(f"Created dummy background: {bg_path}")

    try:
        # Note: we need to use the full path for compose_image input/output
        abs_bg = os.path.abspath(bg_path)
        abs_output = os.path.abspath(output_test)
        
        await compose_image(test_text, abs_bg, abs_output, format="square")
        print(f"Success! Test image saved to: {abs_output}")
        print("Please check this file to verify vowel placements and conjuncts.")
    except Exception as e:
        print(f"Error during composition: {e}")

if __name__ == "__main__":
    asyncio.run(test_hindi_marathi_shaping())
