"""
Generation Router
=================
Endpoints for AI dialogue generation: next segment, full scene, polish,
and SSE streaming.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.services.generation_service import GenerationService
from backend.services.director_service import DirectorService
from backend.services.memory_service import MemoryService

router = APIRouter(prefix="/generate", tags=["generation"])
logger = logging.getLogger("scriptforge.routers.generation")

# Module-level service instances (stateless, safe to share)
_gen_service = GenerationService()
_director_service = DirectorService()
_memory_service = MemoryService()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CharacterSpec(BaseModel):
    name: str
    personality: str = ""


class GenerateNextRequest(BaseModel):
    scene: str = Field(..., description="Scene description / setting")
    characters: list[CharacterSpec] = Field(..., min_length=1)
    style: str = "default"
    context: str = Field(default="", description="Recent script context")
    api_key: str = ""
    model: str = "gemini-2.0-flash-exp"
    provider: str = "gemini"
    session_id: str | None = None
    use_director: bool = False


class DialogueTurn(BaseModel):
    speaker: str
    content: str


class GenerateNextResponse(BaseModel):
    dialogues: list[DialogueTurn]


class GenerateSceneRequest(BaseModel):
    scene: str = Field(..., description="Scene description / setting")
    characters: list[CharacterSpec] = Field(..., min_length=1)
    style: str = "default"
    plot_goal: str = ""
    api_key: str = ""
    model: str = "gemini-2.0-flash-exp"
    provider: str = "gemini"


class GenerateSceneResponse(BaseModel):
    content: str


class PolishRequest(BaseModel):
    text: str = Field(..., description="Raw text to polish")
    style: str = "default"
    instruction: str = ""
    api_key: str = ""
    model: str = "gemini-2.0-flash-exp"
    provider: str = "gemini"


class PolishResponse(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/next", response_model=GenerateNextResponse)
async def generate_next(req: GenerateNextRequest):
    """Generate the next dialogue segment using Gemini."""
    chars = [{"name": c.name, "personality": c.personality} for c in req.characters]

    # Optionally retrieve RAG context per character
    memory_context: dict[str, str] | None = None
    if req.session_id and req.api_key:
        memory_context = {}
        for c in chars:
            memories = _memory_service.get_context(
                session_id=req.session_id,
                api_key=req.api_key,
                character=c["name"],
                query=req.context[-200:] if req.context else req.scene,
            )
            if memories:
                memory_context[c["name"]] = "\n".join(
                    f"{m.get('speaker', '?')}: {m.get('content', '')}" for m in memories[:5]
                )

    dialogues = _gen_service.generate_next(
        scene=req.scene,
        characters=chars,
        style=req.style,
        context=req.context,
        api_key=req.api_key,
        model=req.model,
        memory_context=memory_context,
        provider=req.provider,
    )

    # Store generated dialogues in memory
    if req.session_id and req.api_key:
        for d in dialogues:
            for c in chars:
                _memory_service.add_memory(
                    session_id=req.session_id,
                    api_key=req.api_key,
                    character=c["name"],
                    speaker=d["speaker"],
                    content=d["content"],
                    msg_type="group",
                )

    return GenerateNextResponse(
        dialogues=[DialogueTurn(**d) for d in dialogues]
    )


@router.post("/next/stream")
async def generate_next_stream(req: GenerateNextRequest):
    """SSE streaming generation — yields partial dialogue chunks."""
    chars = [{"name": c.name, "personality": c.personality} for c in req.characters]

    async def event_generator():
        for chunk in _gen_service.generate_next_stream(
            scene=req.scene,
            characters=chars,
            style=req.style,
            context=req.context,
            api_key=req.api_key,
            model=req.model,
            provider=req.provider,
        ):
            yield {"data": json.dumps(chunk, ensure_ascii=False)}

    return EventSourceResponse(event_generator())


@router.post("/scene", response_model=GenerateSceneResponse)
async def generate_scene(req: GenerateSceneRequest):
    """Generate a full scene worth of dialogue using Gemini."""
    chars = [{"name": c.name, "personality": c.personality} for c in req.characters]
    content = _gen_service.generate_scene(
        scene=req.scene,
        characters=chars,
        style=req.style,
        plot_goal=req.plot_goal,
        api_key=req.api_key,
        model=req.model,
        provider=req.provider,
    )
    return GenerateSceneResponse(content=content)


@router.post("/polish", response_model=PolishResponse)
async def polish_text(req: PolishRequest):
    """Polish / refine selected text using Gemini."""
    content = _gen_service.polish(
        text=req.text,
        style=req.style,
        instruction=req.instruction,
        api_key=req.api_key,
        model=req.model,
        provider=req.provider,
    )
    return PolishResponse(content=content)


# ---------------------------------------------------------------------------
# Director mode
# ---------------------------------------------------------------------------

class DirectorRequest(BaseModel):
    scene: str = Field(..., description="Scene description / setting")
    characters: list[CharacterSpec] = Field(..., min_length=1)
    api_key: str = ""
    model: str = "gemini-2.0-flash-exp"
    provider: str = "gemini"
    user_message: str | None = None
    context: str = ""


class DirectorResponse(BaseModel):
    plot_goal: str
    dialogues: list[DialogueTurn]
    review: dict


@router.post("/director", response_model=DirectorResponse)
async def generate_director(req: DirectorRequest):
    """Run the director system pipeline (writer → director → character → reviewer)."""
    chars = [{"name": c.name, "personality": c.personality} for c in req.characters]
    result = _director_service.run_director_round(
        scene=req.scene,
        characters=chars,
        api_key=req.api_key,
        model=req.model,
        user_message=req.user_message,
        context=req.context,
    )
    return DirectorResponse(
        plot_goal=result.get("plot_goal", ""),
        dialogues=[DialogueTurn(**d) for d in result.get("dialogues", [])],
        review=result.get("review", {}),
    )
