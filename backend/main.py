"""
Scriptforge FastAPI Backend
============================
REST API backend for the Scriptforge AI multi-agent dialogue system.
Serves as the API layer between the frontend (Next.js) and the core
generation/export/project services.
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure root-level modules are importable
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.routers import generation, export, project, evaluation

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# ---------------------------------------------------------------------------
# Environment -- load .env from the project root (one level up from backend/)
# ---------------------------------------------------------------------------
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Scriptforge API",
    description="AI multi-agent character dialogue generation backend",
    version="0.2.0",
)

# ---------------------------------------------------------------------------
# CORS -- allow the Next.js dev server and common production origins
# ---------------------------------------------------------------------------
_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "tauri://localhost",
    "https://tauri.localhost",
]

# Support additional origins via environment variable
_extra_origins = os.getenv("CORS_ORIGINS", "")
if _extra_origins:
    _allowed_origins.extend(o.strip() for o in _extra_origins.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger("scriptforge").error("未处理异常: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"},
    )

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(generation.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(project.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    """Return basic service health and whether GEMINI_API_KEY is configured."""
    return {
        "status": "ok",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "version": "0.2.0",
    }
