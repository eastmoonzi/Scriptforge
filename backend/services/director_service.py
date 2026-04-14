"""
Director Service
================
Wraps the root-level ``DirectorSystem`` for use in the FastAPI backend.
Four-phase pipeline: writer → director → character → reviewer.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

# Ensure root modules are importable
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.services._compat import install as _install_compat
_install_compat()

logger = logging.getLogger("scriptforge.director")


class DirectorService:
    """Thin wrapper around DirectorSystem with graceful fallback."""

    def run_director_round(
        self,
        scene: str,
        characters: list[dict[str, str]],
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        user_message: str | None = None,
        context: str = "",
    ) -> dict[str, Any]:
        """Run a single director conversation round.

        Returns ``{plot_goal, dialogues, review}`` or falls back to a
        simplified generation if CrewAI is unavailable.
        """
        if not api_key:
            return self._mock_result(characters, scene)

        try:
            from director_system import DirectorSystem

            ds = DirectorSystem(
                scene=scene,
                characters=characters,
                api_key=api_key,
                model_id=model,
            )
            result = ds.run_conversation_round(user_message=user_message)
            return {
                "plot_goal": result.get("plot_goal", ""),
                "dialogues": result.get("dialogues", []),
                "review": result.get("review_result", {}),
            }
        except ImportError:
            logger.warning("CrewAI 不可用，使用简化生成")
            return self._fallback_generate(scene, characters, api_key, model, context)
        except Exception as e:
            logger.error("导演系统执行失败: %s", e)
            return self._fallback_generate(scene, characters, api_key, model, context)

    def _fallback_generate(
        self,
        scene: str,
        characters: list[dict[str, str]],
        api_key: str,
        model: str,
        context: str,
    ) -> dict[str, Any]:
        """Fallback: use raw Gemini calls without CrewAI."""
        try:
            import google.genai as genai

            client = genai.Client(api_key=api_key)
            characters_text = "\n".join(
                f"- {c['name']}: {c.get('personality', '')}" for c in characters
            )

            # Generate plot goal
            goal_prompt = f"作为编剧，请为以下场景设定一个简短的剧情目标（一句话）。\n场景：{scene}\n角色：\n{characters_text}"
            goal_resp = client.models.generate_content(model=model, contents=goal_prompt)
            plot_goal = (goal_resp.text or "推进对话").strip()

            # Generate dialogues
            dialogues = []
            for char in characters:
                prompt = f"""场景：{scene}\n剧情目标：{plot_goal}\n\n你是{char['name']}（{char.get('personality', '')}）。\n{context}\n请以角色身份说一句话，只输出内容不加角色名。"""
                resp = client.models.generate_content(model=model, contents=prompt)
                dialogues.append({
                    "speaker": char["name"],
                    "content": (resp.text or "……").strip(),
                })

            return {
                "plot_goal": plot_goal,
                "dialogues": dialogues,
                "review": {"pass": True, "feedback": "（简化模式，跳过审稿）"},
            }
        except Exception as e:
            logger.error("Fallback 生成失败: %s", e)
            return self._mock_result(characters, scene)

    @staticmethod
    def _mock_result(characters: list[dict[str, str]], scene: str) -> dict[str, Any]:
        return {
            "plot_goal": "（模拟）推进对话",
            "dialogues": [
                {"speaker": c["name"], "content": f"（模拟导演模式台词）{scene[:20]}"}
                for c in characters[:3]
            ],
            "review": {"pass": True, "feedback": "模拟数据"},
        }
