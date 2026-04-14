"""
Scriptforge Services
====================
This package exposes the core service classes used by the FastAPI routers.

Root-level Python modules are imported via ``sys.path`` manipulation
rather than symlinking.
"""

import sys
from pathlib import Path

# Ensure root-level modules (template_manager, director_system, …) are importable
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.services.generation_service import GenerationService

__all__ = ["GenerationService"]
