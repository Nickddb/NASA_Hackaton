"""
Groq chat provider (OpenAI-compatible Chat Completions API) with multi-round tool calling.

Uses httpx, which the backend already depends on, so no SDK is needed. Each round sends the tool results back to
the model, which decides the next call (exam -> diagnosis -> central alert -> stimuli).
"""

from __future__ import annotations

import inspect
import json
import re
from typing import Any

import httpx

from app import config

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
JSON_TYPES = {"str": "string", "float": "number", "int": "integer", "bool": "boolean"}


def tool_schema(t: Any) -> dict[str, Any]:
    """OpenAI function schema from a _FastTool's signature and docstring."""
    props: dict[str, Any] = {}
    required: list[str] = []
    for name, param in t._sig.parameters.items():
        ann = param.annotation
        ann_name = ann if isinstance(ann, str) else getattr(ann, "__name__", "str")
        props[name] = {"type": JSON_TYPES.get(ann_name, "string")}
        if param.default is inspect.Parameter.empty:
            required.append(name)
    description = " ".join(t.description.split())[:1024]
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": description,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


def clean_reply(text: str | None) -> str:
    return THINK_BLOCK.sub("", text or "").strip()


async def run_groq_chat(system_prompt: str, user_message: str, tools: list[Any]) -> tuple[str, bool]:
    """Returns (reply, used_tools). Raises on HTTP/network errors so the caller can fall back offline."""
    tools_by_name = {t.name: t for t in tools}
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    body: dict[str, Any] = {
        "model": config.LLM_MODEL,
        "temperature": 0.15,
        "tools": [tool_schema(t) for t in tools],
        "tool_choice": "auto",
    }
    if config.GROQ_REASONING_FORMAT:
        body["reasoning_format"] = config.GROQ_REASONING_FORMAT
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}

    used_tools = False
    async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT_S) as client:
        for _ in range(config.LLM_MAX_TOOL_ROUNDS + 1):
            resp = await client.post(GROQ_CHAT_URL, headers=headers, json={**body, "messages": messages})
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            calls = msg.get("tool_calls") or []
            if not calls:
                return clean_reply(msg.get("content")), used_tools
            used_tools = True
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for call in calls:
                fn = tools_by_name.get(call["function"]["name"])
                try:
                    args = json.loads(call["function"].get("arguments") or "{}")
                except ValueError:
                    args = {}
                result = fn.invoke(args) if fn else json.dumps({"error": f"unknown tool {call['function']['name']}"})
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": str(result)})
        # round limit reached: ask for a final answer without tools
        resp = await client.post(
            GROQ_CHAT_URL, headers=headers, json={**{k: v for k, v in body.items() if k not in ("tools", "tool_choice")}, "messages": messages}
        )
        resp.raise_for_status()
        return clean_reply(resp.json()["choices"][0]["message"].get("content")), used_tools
