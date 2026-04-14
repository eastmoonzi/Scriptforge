"""
Project Router
==============
CRUD endpoints for managing Scriptforge projects, backed by SQLite.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.project_store import ProjectStore

router = APIRouter(prefix="/projects", tags=["projects"])

# Module-level store instance
_store = ProjectStore()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CharacterSpec(BaseModel):
    name: str
    description: str = ""
    personality: str = ""


class ProjectCreate(BaseModel):
    """Payload for creating a new project.
    Accepts both ``name`` (original) and ``title`` (frontend compat) fields.
    """
    name: str = Field(default="", description="Project name")
    title: str = Field(default="", description="Alias for name (frontend compat)")
    scene: str = ""
    characters: list[CharacterSpec] = Field(default_factory=list)
    style: str = "default"
    author: str = ""
    content: str = ""


class ProjectUpdate(BaseModel):
    """Payload for updating an existing project (all fields optional)."""
    name: Optional[str] = None
    title: Optional[str] = None
    scene: Optional[str] = None
    characters: Optional[list[CharacterSpec]] = None
    style: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None


class ProjectOut(BaseModel):
    """Project representation returned to the client."""
    id: str
    name: str
    scene: str = ""
    characters: list[CharacterSpec] = Field(default_factory=list)
    style: str = "default"
    content: str = ""
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ProjectOut])
async def list_projects():
    """List all projects."""
    return _store.list_all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(req: ProjectCreate):
    """Create a new project."""
    data = req.model_dump()
    # Resolve name from ``title`` if ``name`` is empty
    if not data.get("name") and data.get("title"):
        data["name"] = data["title"]
    if not data.get("name"):
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    # Serialize characters
    if data.get("characters"):
        data["characters"] = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in req.characters
        ]
    return _store.create(data)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str):
    """Get a single project by ID."""
    project = _store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, req: ProjectUpdate):
    """Update an existing project."""
    data = req.model_dump(exclude_unset=True)
    if "characters" in data and data["characters"] is not None:
        data["characters"] = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in req.characters
        ]
    project = _store.update(project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    if not _store.delete(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"detail": "已删除"}
