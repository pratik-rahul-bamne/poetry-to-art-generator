"""
Font Downloader — Downloads handwriting fonts from Google Fonts on first run.
Run directly: python -m backend.utils.font_downloader
"""

import urllib.request
import zipfile
import shutil
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

FONTS_TO_DOWNLOAD = [
    # (filename, direct_download_url)
    (
        "Caveat-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat%5Bwght%5D.ttf",
    ),
    (
        "NotoSansDevanagari-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf",
    ),
]


def download_fonts(force: bool = False) -> None:
    """Download fonts if they don't already exist."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in FONTS_TO_DOWNLOAD:
        dest = ASSETS_DIR / filename
        if dest.exists() and not force:
            print(f"  [✓] {filename} already present.")
            continue

        print(f"  [↓] Downloading {filename} ...")
        try:
            urllib.request.urlretrieve(url, str(dest))
            print(f"  [✓] Saved to {dest}")
        except Exception as e:
            print(f"  [!] Failed to download {filename}: {e}")
            print(f"      Please manually place the font at: {dest}")


if __name__ == "__main__":
    print("=== AI Poem Visualizer — Font Setup ===")
    download_fonts()
    print("Done.")
