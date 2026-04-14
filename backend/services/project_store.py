"""
Project Store
=============
SQLite-backed persistence for Scriptforge projects.
Uses Python's built-in ``sqlite3`` — zero extra dependencies.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _resolve_db_path() -> Path:
    env_dir = os.environ.get("SCRIPTFORGE_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p / "scriptforge.db"
    return Path(__file__).resolve().parent.parent / "data" / "scriptforge.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectStore:
    """Thread-safe SQLite store for projects."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or _resolve_db_path())
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    scene       TEXT NOT NULL DEFAULT '',
                    characters  TEXT NOT NULL DEFAULT '[]',
                    style       TEXT NOT NULL DEFAULT 'default',
                    content     TEXT NOT NULL DEFAULT '',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
            """)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["characters"] = json.loads(d.get("characters") or "[]")
        return d

    def list_all(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC"
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, project_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def create(self, data: dict) -> dict:
        project_id = str(uuid.uuid4())
        now = _now_iso()
        record = {
            "id": project_id,
            "name": data.get("name") or data.get("title", "未命名剧本"),
            "scene": data.get("scene", ""),
            "characters": json.dumps(data.get("characters", []), ensure_ascii=False),
            "style": data.get("style", "default"),
            "content": data.get("content", ""),
            "created_at": now,
            "updated_at": now,
        }
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO projects (id, name, scene, characters, style, content, created_at, updated_at)
                   VALUES (:id, :name, :scene, :characters, :style, :content, :created_at, :updated_at)""",
                record,
            )
        record["characters"] = json.loads(record["characters"])
        return record

    def update(self, project_id: str, data: dict) -> Optional[dict]:
        existing = self.get(project_id)
        if not existing:
            return None

        # Merge fields
        if "name" in data or "title" in data:
            existing["name"] = data.get("name") or data.get("title", existing["name"])
        for field in ("scene", "style", "content"):
            if field in data:
                existing[field] = data[field]
        if "characters" in data:
            existing["characters"] = data["characters"]

        existing["updated_at"] = _now_iso()

        with self._conn() as conn:
            conn.execute(
                """UPDATE projects SET name=?, scene=?, characters=?, style=?, content=?, updated_at=?
                   WHERE id=?""",
                (
                    existing["name"],
                    existing["scene"],
                    json.dumps(existing["characters"], ensure_ascii=False),
                    existing["style"],
                    existing["content"],
                    existing["updated_at"],
                    project_id,
                ),
            )
        return existing

    def delete(self, project_id: str) -> bool:
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cursor.rowcount > 0
