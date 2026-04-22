"""
Generation Service
==================
Wraps real Gemini API calls for dialogue generation, scene generation,
streaming generation, and text polishing.

Reuses prompt-building patterns from the root ``app.py`` module.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Generator, Optional

# Make root-level modules importable
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Install Streamlit compat shim before importing root modules
from backend.services._compat import install as _install_compat
_install_compat()

from template_manager import TemplateManager

logger = logging.getLogger("scriptforge.generation")


# Provider → OpenAI-compatible base URL mapping
PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "kimi": "https://api.moonshot.cn/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "minimax": "https://api.minimax.chat/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
}


class GenerationService:
    """Stateless service for script generation. Supports Gemini (native SDK) and
    any OpenAI-compatible provider (OpenAI, DeepSeek, Kimi, Qwen, MiniMax, etc.)."""

    def __init__(self, templates_dir: str | None = None):
        if templates_dir is None:
            templates_dir = os.path.join(_ROOT, "templates")
        try:
            self.template_manager = TemplateManager(templates_dir=templates_dir)
        except Exception:
            logger.warning("TemplateManager 初始化失败，模版增强功能不可用")
            self.template_manager = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _gemini_client(api_key: str):
        import google.genai as genai
        return genai.Client(api_key=api_key)

    @staticmethod
    def _openai_client(api_key: str, base_url: str):
        from openai import OpenAI
        return OpenAI(api_key=api_key, base_url=base_url)

    @staticmethod
    def _resolve_base_url(provider: str, base_url: str = "") -> str:
        """Return the base_url for an OpenAI-compatible provider."""
        if base_url:
            return base_url
        url = PROVIDER_BASE_URLS.get(provider, "")
        if not url:
            raise ValueError(f"未知的 provider「{provider}」且未提供 base_url")
        return url

    @staticmethod
    def _generate_via_openai(client, model: str, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return (response.choices[0].message.content or "").strip()

    @staticmethod
    def _stream_via_openai(client, model: str, prompt: str, system_prompt: str = ""):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def _build_system_prompt(
        self,
        character: dict[str, str],
        characters: list[dict[str, str]],
        style: str = "default",
    ) -> str:
        """Build the system prompt with role identity and behavioral rules."""
        characters_text = "\n".join(
            f"- {c['name']}: {c.get('personality', '')}" for c in characters
        )

        return f"""你正在扮演角色：{character['name']}（性格：{character.get('personality', '')}）

所有角色：
{characters_text}

【行为规则】
- 严格保持你的性格特点
- 让对话自然流畅，不要生硬
- 只输出你要说的一句话，不要加角色名，不要有其他说明
- 不要旁白或描述动作，只说对白"""

    def _build_prompt(
        self,
        scene: str,
        character: dict[str, str],
        characters: list[dict[str, str]],
        context: str = "",
        style: str = "default",
    ) -> str:
        """Build the per-character generation prompt (user message with scene and context)."""
        if not context.strip():
            user_prompt = f"""场景：{scene}

你是第一个发言的角色。请打招呼并对场景做出反应。"""
        else:
            user_prompt = f"""场景：{scene}

最近的对话记录：
{context}

请以你的身份和性格，在群聊中发言。仔细阅读上面的对话记录，理解整体对话的氛围和方向。"""

        # Apply template enhancement if available
        if self.template_manager and style != "default":
            try:
                templates = self.template_manager.list_templates()
                template_id = None
                for t in templates:
                    if t.get("genre", "").lower() == style.lower() or t.get("id", "").lower() == style.lower():
                        template_id = t["id"]
                        break
                if template_id:
                    user_prompt = self.template_manager.generate_enhanced_prompt(
                        template_id=template_id,
                        scene=scene,
                        character=character,
                        base_prompt=user_prompt,
                    )
            except Exception as e:
                logger.warning("模版增强失败，使用默认 Prompt: %s", e)

        return user_prompt

    @staticmethod
    def _mock_dialogues(characters: list[dict[str, str]], scene: str) -> list[dict[str, str]]:
        return [
            {
                "speaker": c["name"],
                "content": f"（模拟台词）这是场景「{scene[:20]}」中的对白。",
            }
            for c in characters[:3]
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_next(
        self,
        scene: str,
        characters: list[dict[str, str]],
        style: str = "default",
        context: str = "",
        api_key: str = "",
        model: str = "gemini-2.0-flash-exp",
        memory_context: dict[str, str] | None = None,
        provider: str = "gemini",
        base_url: str = "",
    ) -> list[dict[str, str]]:
        """Generate the next round of dialogue — one line per character.

        Returns ``[{speaker, content}]``.
        """
        if not api_key:
            return self._mock_dialogues(characters, scene)

        try:
            if provider == "gemini":
                client = self._gemini_client(api_key)
            else:
                client = self._openai_client(api_key, self._resolve_base_url(provider, base_url))

            dialogues: list[dict[str, str]] = []
            round_context = context

            for char in characters:
                enriched_context = round_context
                if memory_context and char["name"] in memory_context:
                    enriched_context += "\n\n【相关记忆】\n" + memory_context[char["name"]]
                system_prompt = self._build_system_prompt(char, characters, style)
                user_prompt = self._build_prompt(scene, char, characters, enriched_context, style)

                if provider == "gemini":
                    from google.genai import types
                    response = client.models.generate_content(
                        model=model,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(system_instruction=system_prompt),
                    )
                    text = (response.text or "").strip()
                else:
                    text = self._generate_via_openai(client, model, user_prompt, system_prompt=system_prompt)

                if text:
                    dialogues.append({"speaker": char["name"], "content": text})
                    round_context += f"\n{char['name']}: {text}"

            return dialogues if dialogues else self._mock_dialogues(characters, scene)

        except Exception as e:
            logger.error("%s 生成失败: %s", provider, e)
            raise RuntimeError(f"{provider} 生成失败: {e}") from e

    def generate_next_stream(
        self,
        scene: str,
        characters: list[dict[str, str]],
        style: str = "default",
        context: str = "",
        api_key: str = "",
        model: str = "gemini-2.0-flash-exp",
        provider: str = "gemini",
        base_url: str = "",
        memory_context: dict[str, str] | None = None,
    ) -> Generator[dict[str, str], None, None]:
        """Streaming generation — yields ``{speaker, content}`` chunks.

        Each chunk has *partial* content for the current speaker.
        A chunk with ``content == "[DONE]"`` signals speaker completion.
        """
        if not api_key:
            for d in self._mock_dialogues(characters, scene):
                yield {"speaker": d["speaker"], "content": d["content"]}
                yield {"speaker": d["speaker"], "content": "[DONE]"}
            return

        try:
            if provider == "gemini":
                client = self._gemini_client(api_key)
            else:
                client = self._openai_client(api_key, self._resolve_base_url(provider, base_url))

            round_context = context

            for char in characters:
                enriched_context = round_context
                if memory_context and char["name"] in memory_context:
                    enriched_context += "\n\n【相关记忆】\n" + memory_context[char["name"]]
                system_prompt = self._build_system_prompt(char, characters, style)
                user_prompt = self._build_prompt(scene, char, characters, enriched_context, style)

                full_text = ""
                if provider == "gemini":
                    from google.genai import types
                    stream = client.models.generate_content_stream(
                        model=model,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(system_instruction=system_prompt),
                    )
                    for chunk in stream:
                        text = chunk.text or ""
                        if text:
                            full_text += text
                            yield {"speaker": char["name"], "content": text}
                else:
                    for text in self._stream_via_openai(client, model, user_prompt, system_prompt=system_prompt):
                        if text:
                            full_text += text
                            yield {"speaker": char["name"], "content": text}

                yield {"speaker": char["name"], "content": "[DONE]"}
                if full_text.strip():
                    round_context += f"\n{char['name']}: {full_text.strip()}"

        except Exception as e:
            logger.error("%s 流式生成失败: %s", provider, e)
            yield {"speaker": "", "content": "[ERROR]", "error": str(e)}

    def generate_scene(
        self,
        scene: str,
        characters: list[dict[str, str]],
        style: str = "default",
        plot_goal: str = "",
        api_key: str = "",
        model: str = "gemini-2.0-flash-exp",
        provider: str = "gemini",
        base_url: str = "",
    ) -> str:
        """Generate a full scene in Fountain format."""
        if not api_key:
            lines = []
            for i, c in enumerate(characters[:6]):
                lines.append(f"\n{c['name']}\n（模拟续写）这是第 {i + 1} 句台词。")
            return "\n".join(lines)

        characters_text = "\n".join(
            f"- {c['name']}: {c.get('personality', '')}" for c in characters
        )
        prompt = f"""
你是一位专业的剧本编剧。请为以下场景编写一整场对白。

场景：{scene}
角色：
{characters_text}
{"剧情目标：" + plot_goal if plot_goal else ""}
{"风格：" + style if style != "default" else ""}

请使用 Fountain 剧本格式输出：
- 角色名大写单独一行
- 对白紧跟角色名下方
- 场景标题用 INT. 或 EXT. 开头
- 动作描写用普通段落

请直接输出剧本内容，不要加其他说明。
"""
        try:
            if provider == "gemini":
                client = self._gemini_client(api_key)
                response = client.models.generate_content(model=model, contents=prompt)
                return (response.text or "").strip()
            else:
                client = self._openai_client(api_key, self._resolve_base_url(provider, base_url))
                return self._generate_via_openai(client, model, prompt)
        except Exception as e:
            logger.error("%s 场景生成失败: %s", provider, e)
            raise RuntimeError(f"{provider} 场景生成失败: {e}") from e

    def polish(
        self,
        text: str,
        style: str = "default",
        instruction: str = "",
        api_key: str = "",
        model: str = "gemini-2.0-flash-exp",
        provider: str = "gemini",
        base_url: str = "",
    ) -> str:
        """Polish / refine the given text."""
        if not api_key:
            return f"【润色后】{text}"

        prompt = f"""
你是一位专业的剧本润色编辑。请对以下剧本文本进行润色和优化。

原文：
{text}

{"风格要求：" + style if style != "default" else ""}
{"具体指示：" + instruction if instruction else ""}

【要求】
- 保持原意不变，提升文学性和表现力
- 使对白更自然、更有张力
- 修正不通顺的表达
- 直接输出润色后的文本，不要加说明

润色结果：
"""
        try:
            if provider == "gemini":
                client = self._gemini_client(api_key)
                response = client.models.generate_content(model=model, contents=prompt)
                return (response.text or "").strip()
            else:
                client = self._openai_client(api_key, self._resolve_base_url(provider, base_url))
                return self._generate_via_openai(client, model, prompt)
        except Exception as e:
            logger.error("%s 润色失败: %s", provider, e)
            raise RuntimeError(f"{provider} 润色失败: {e}") from e
