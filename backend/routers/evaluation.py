"""
Evaluation Router
=================
Endpoints for evaluating dialogue quality using CPD/DE/OOC metrics.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

# Ensure root modules are importable
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

router = APIRouter(prefix="/evaluate", tags=["evaluation"])
logger = logging.getLogger("scriptforge.routers.evaluation")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DialogueMessage(BaseModel):
    speaker: str
    content: str


class EvaluateRequest(BaseModel):
    conversations: list[DialogueMessage] = Field(..., min_length=1)
    character_profiles: dict[str, str] = Field(
        default_factory=dict,
        description="Character name → personality description, needed for OOC detection",
    )
    api_key: str = ""
    model: str = "gemini-2.0-flash-exp"


class EvaluateResponse(BaseModel):
    overall_score: float
    cpd: dict
    de: dict
    ooc: dict
    summary: dict


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    """Evaluate dialogue quality — returns CPD, DE, and OOC scores."""
    try:
        from evaluation_system import EvaluationMetrics

        metrics = EvaluationMetrics(api_key=req.api_key or None)
        conversations = [{"speaker": m.speaker, "content": m.content} for m in req.conversations]

        result = metrics.comprehensive_evaluation(
            conversations=conversations,
            character_profiles=req.character_profiles if req.character_profiles else None,
        )

        return EvaluateResponse(
            overall_score=result.get("overall_score", 0),
            cpd=result.get("metrics", {}).get("cpd", {}),
            de=result.get("metrics", {}).get("de", {}),
            ooc=result.get("metrics", {}).get("ooc", {}),
            summary=result.get("summary", {}),
        )
    except ImportError:
        logger.warning("evaluation_system 导入失败")
        return EvaluateResponse(
            overall_score=0,
            cpd={"error": "评估系统不可用"},
            de={"error": "评估系统不可用"},
            ooc={"error": "评估系统不可用"},
            summary={"error": "evaluation_system.py 未找到"},
        )
    except Exception as e:
        logger.error("评估失败: %s", e)
        return EvaluateResponse(
            overall_score=0,
            cpd={"error": str(e)},
            de={"error": str(e)},
            ooc={"error": str(e)},
            summary={"error": str(e)},
        )
