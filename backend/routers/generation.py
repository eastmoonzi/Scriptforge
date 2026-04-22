"""
Generation Router
=================
Endpoints for AI dialogue generation: next segment, full scene, polish,
and SSE streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Header
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
# Dependency: extract API key from request header
# ---------------------------------------------------------------------------

async def get_api_key(x_api_key: str = Header("", alias="X-API-Key")) -> str:
    """Extract API key from request header. Falls back to empty string."""
    return x_api_key


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
    model: str = "gemini-2.0-flash-exp"
    provider: str = "gemini"
    base_url: str = ""
    session_id: str | None = None
    use_director: bool = False
    commit_memory: bool = True


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
    model: str = "gemini-2.0-flash-exp"
    provider: str = "gemini"
    base_url: str = ""


class GenerateSceneResponse(BaseModel):
    content: str


class PolishRequest(BaseModel):
    text: str = Field(..., description="Raw text to polish")
    style: str = "default"
    instruction: str = ""
    model: str = "gemini-2.0-flash-exp"
    provider: str = "gemini"
    base_url: str = ""


class PolishResponse(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/next", response_model=GenerateNextResponse)
async def generate_next(req: GenerateNextRequest, api_key: str = Depends(get_api_key)):
    """Generate the next dialogue segment."""
    chars = [{"name": c.name, "personality": c.personality} for c in req.characters]

    # Optionally retrieve RAG context per character (requires Gemini for embeddings)
    memory_context: dict[str, str] | None = None
    if req.session_id and api_key and req.provider == "gemini":
        memory_context = {}
        for c in chars:
            memories = _memory_service.get_context(
                session_id=req.session_id,
                api_key=api_key,
                character=c["name"],
                query=req.context[-200:] if req.context else req.scene,
            )
            if memories:
                memory_context[c["name"]] = "\n".join(
                    f"{m.get('speaker', '?')}: {m.get('content', '')}" for m in memories[:5]
                )

    dialogues = await asyncio.to_thread(
        _gen_service.generate_next,
        scene=req.scene,
        characters=chars,
        style=req.style,
        context=req.context,
        api_key=api_key,
        model=req.model,
        memory_context=memory_context,
        provider=req.provider,
        base_url=req.base_url,
    )

    # Store generated dialogues in memory (Gemini only — embeddings require Google API)
    if req.commit_memory and req.session_id and api_key and req.provider == "gemini":
        for d in dialogues:
            for c in chars:
                _memory_service.add_memory(
                    session_id=req.session_id,
                    api_key=api_key,
                    character=c["name"],
                    speaker=d["speaker"],
                    content=d["content"],
                    msg_type="group",
                )

    return GenerateNextResponse(
        dialogues=[DialogueTurn(**d) for d in dialogues]
    )


@router.post("/next/stream")
async def generate_next_stream(req: GenerateNextRequest, api_key: str = Depends(get_api_key)):
    """SSE streaming generation — yields partial dialogue chunks."""
    chars = [{"name": c.name, "personality": c.personality} for c in req.characters]

    # Retrieve RAG context before streaming (Gemini only — embeddings require Google API)
    memory_context: dict[str, str] | None = None
    if req.session_id and api_key and req.provider == "gemini":
        memory_context = {}
        for c in chars:
            memories = _memory_service.get_context(
                session_id=req.session_id,
                api_key=api_key,
                character=c["name"],
                query=req.context[-200:] if req.context else req.scene,
            )
            if memories:
                memory_context[c["name"]] = "\n".join(
                    f"{m.get('speaker', '?')}: {m.get('content', '')}" for m in memories[:5]
                )

    # Buffer per-speaker content so we can write memory when a speaker finishes
    speaker_buffer: dict[str, list[str]] = {}

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()

        def _run_stream():
            try:
                for chunk in _gen_service.generate_next_stream(
                    scene=req.scene,
                    characters=chars,
                    style=req.style,
                    context=req.context,
                    api_key=api_key,
                    model=req.model,
                    provider=req.provider,
                    base_url=req.base_url,
                    memory_context=memory_context,
                ):
                    queue.put_nowait(chunk)
                queue.put_nowait(None)  # sentinel: done
            except Exception as e:
                queue.put_nowait({"error": str(e), "speaker": "", "content": "[ERROR]"})
                queue.put_nowait(None)

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _run_stream)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield {"data": json.dumps(chunk, ensure_ascii=False)}

            # Write memory when a speaker's turn ends
            if req.commit_memory and chunk.get("content") == "[DONE]" and req.session_id and api_key and req.provider == "gemini":
                speaker = chunk["speaker"]
                full_content = "".join(speaker_buffer.pop(speaker, []))
                if full_content:
                    for c in chars:
                        _memory_service.add_memory(
                            session_id=req.session_id,
                            api_key=api_key,
                            character=c["name"],
                            speaker=speaker,
                            content=full_content,
                            msg_type="group",
                        )
            elif chunk.get("content") not in ("[DONE]", "[ERROR]"):
                speaker = chunk["speaker"]
                speaker_buffer.setdefault(speaker, []).append(chunk.get("content", ""))

    return EventSourceResponse(event_generator())


@router.post("/scene", response_model=GenerateSceneResponse)
async def generate_scene(req: GenerateSceneRequest, api_key: str = Depends(get_api_key)):
    """Generate a full scene worth of dialogue."""
    chars = [{"name": c.name, "personality": c.personality} for c in req.characters]
    content = await asyncio.to_thread(
        _gen_service.generate_scene,
        scene=req.scene,
        characters=chars,
        style=req.style,
        plot_goal=req.plot_goal,
        api_key=api_key,
        model=req.model,
        provider=req.provider,
        base_url=req.base_url,
    )
    return GenerateSceneResponse(content=content)


@router.post("/polish", response_model=PolishResponse)
async def polish_text(req: PolishRequest, api_key: str = Depends(get_api_key)):
    """Polish / refine selected text."""
    content = await asyncio.to_thread(
        _gen_service.polish,
        text=req.text,
        style=req.style,
        instruction=req.instruction,
        api_key=api_key,
        model=req.model,
        provider=req.provider,
        base_url=req.base_url,
    )
    return PolishResponse(content=content)


# ---------------------------------------------------------------------------
# Director mode
# ---------------------------------------------------------------------------

class DirectorRequest(BaseModel):
    scene: str = Field(..., description="Scene description / setting")
    characters: list[CharacterSpec] = Field(..., min_length=1)
    model: str = "gemini-2.0-flash-exp"
    provider: str = "gemini"
    base_url: str = ""
    user_message: str | None = None
    context: str = ""
    session_id: str | None = None


class DirectorResponse(BaseModel):
    plot_goal: str
    dialogues: list[DialogueTurn]
    review: dict


@router.post("/director", response_model=DirectorResponse)
async def generate_director(req: DirectorRequest, api_key: str = Depends(get_api_key)):
    """Run the director system pipeline (writer → director → character → reviewer)."""
    chars = [{"name": c.name, "personality": c.personality} for c in req.characters]
    result = await asyncio.to_thread(
        _director_service.run_director_round,
        scene=req.scene,
        characters=chars,
        api_key=api_key,
        model=req.model,
        user_message=req.user_message,
        context=req.context,
        provider=req.provider,
        base_url=req.base_url,
        session_id=req.session_id,
    )
    return DirectorResponse(
        plot_goal=result.get("plot_goal", ""),
        dialogues=[DialogueTurn(**d) for d in result.get("dialogues", [])],
        review=result.get("review", {}),
    )


# ---------------------------------------------------------------------------
# Memory commit
# ---------------------------------------------------------------------------

class CommitMemoryRequest(BaseModel):
    session_id: str
    characters: list[CharacterSpec]
    dialogues: list[DialogueTurn]


@router.post("/memory/commit")
async def commit_memory(req: CommitMemoryRequest, api_key: str = Depends(get_api_key)):
    """Persist accepted dialogues to RAG memory (Gemini only)."""
    chars = [{"name": c.name} for c in req.characters]
    for d in req.dialogues:
        for c in chars:
            _memory_service.add_memory(
                session_id=req.session_id,
                api_key=api_key,
                character=c["name"],
                speaker=d.speaker,
                content=d.content,
                msg_type="group",
            )
    return {"committed": len(req.dialogues)}
