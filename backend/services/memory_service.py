"""
Memory Service
==============
Wraps the root-level ``RAGMemorySystem`` (ChromaDB + Google Embeddings)
for per-session context-aware generation.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.services._compat import install as _install_compat
_install_compat()

logger = logging.getLogger("scriptforge.memory")


class MemoryService:
    """Manages per-session RAGMemorySystem instances."""

    def __init__(self):
        self._sessions: dict[str, Any] = {}

    def _get_rag(self, session_id: str, api_key: str):
        """Lazily create a RAGMemorySystem for the given session."""
        if session_id in self._sessions:
            return self._sessions[session_id]
        try:
            from memory_rag import RAGMemorySystem

            persist_dir = str(Path(__file__).resolve().parent.parent / "data" / "chroma" / session_id)
            rag = RAGMemorySystem(api_key=api_key, persist_directory=persist_dir)
            self._sessions[session_id] = rag
            return rag
        except ImportError:
            logger.warning("RAGMemorySystem 不可用（缺少 chromadb 依赖）")
            return None
        except Exception as e:
            logger.error("RAG 初始化失败: %s", e)
            return None

    def add_memory(
        self,
        session_id: str,
        api_key: str,
        character: str,
        speaker: str,
        content: str,
        msg_type: str = "group",
    ) -> bool:
        rag = self._get_rag(session_id, api_key)
        if not rag:
            return False
        try:
            rag.add_memory(
                character_name=character,
                speaker=speaker,
                content=content,
                msg_type=msg_type,
            )
            return True
        except Exception as e:
            logger.error("添加记忆失败: %s", e)
            return False

    def get_context(
        self,
        session_id: str,
        api_key: str,
        character: str,
        query: str,
        recent_k: int = 10,
        relevant_k: int = 5,
    ) -> list[dict]:
        rag = self._get_rag(session_id, api_key)
        if not rag:
            return []
        try:
            return rag.get_hybrid_context(
                character_name=character,
                current_query=query,
                recent_k=recent_k,
                relevant_k=relevant_k,
            )
        except Exception as e:
            logger.error("获取上下文失败: %s", e)
            return []

    def clear(self, session_id: str) -> bool:
        rag = self._sessions.pop(session_id, None)
        if rag:
            try:
                rag.clear_memories()
            except Exception:
                pass
            return True
        return False
