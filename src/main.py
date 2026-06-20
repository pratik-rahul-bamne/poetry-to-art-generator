import sys
from pathlib import Path

# Add src directory to PYTHONPATH programmatically
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn

if __name__ == "__main__":
    print("Starting AI Poem Visualizer...")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
