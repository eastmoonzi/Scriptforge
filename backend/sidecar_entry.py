"""
Scriptforge Sidecar Entry
=========================
Standalone launch script for PyInstaller bundling / Tauri sidecar usage.
Starts the FastAPI backend on a configurable port with an optional
data directory for SQLite persistence.
"""

import argparse
import os
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Scriptforge backend sidecar")
    parser.add_argument("--port", type=int, default=18080, help="Port to listen on")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory for SQLite DB")
    args = parser.parse_args()

    # Set environment variables before importing the app
    if args.data_dir:
        os.environ["SCRIPTFORGE_DATA_DIR"] = args.data_dir

    # CORS: allow Tauri origins
    existing = os.getenv("CORS_ORIGINS", "")
    tauri_origins = "tauri://localhost,https://tauri.localhost"
    if existing:
        os.environ["CORS_ORIGINS"] = f"{existing},{tauri_origins}"
    else:
        os.environ["CORS_ORIGINS"] = tauri_origins

    # Ensure project root is on sys.path so `backend.xxx` imports work
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
