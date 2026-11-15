"""Groq provider: tool schemas, multi-round tool calling and offline fallback, with the HTTP API faked."""

import asyncio
import json

import httpx
import pytest

from app import config
from app.agent import llm_groq
from app.agent.mission_tools import MissionAgentTools, build_mission_tools
from app.agent.orchestrator import AstraCareOrchestrator
from app.state_manager import MissionStateManager


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


def fake_groq(replies, sent):
    async def post(self, url, headers=None, json=None):
        sent.append({"url": url, "headers": headers, "body": json})
        return replies.pop(0)

    return post


def message(content=None, tool_calls=None):
    return FakeResponse({"choices": [{"message": {"role": "assistant", "content": content, "tool_calls": tool_calls}}]})


@pytest.fixture()
def groq(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(config, "LLM_MODEL", "qwen/qwen3.8-27b")


def test_chat_chains_tools_through_groq(groq, monkeypatch):
    sent = []
    call = {"id": "c1", "type": "function", "function": {"name": "run_monitoring_cycle", "arguments": json.dumps({"astronaut_id": "kenji_sato"})}}
    replies = [message(tool_calls=[call]), message(content="<think>internal</think>Kenji está estável.")]
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_groq(replies, sent))

    res = asyncio.run(AstraCareOrchestrator(MissionStateManager()).handle_chat("verificar o kenji agora"))

    assert res.mode == "groq" and res.reply == "Kenji está estável."
    assert "run_monitoring_cycle" in [t.tool_name for t in res.tool_trace]
    first, second = sent[0]["body"], sent[1]["body"]
    assert first["model"] == "qwen/qwen3.8-27b" and sent[0]["headers"]["Authorization"] == "Bearer test-key"
    assert {t["function"]["name"] for t in first["tools"]} >= {"schedule_smartwatch_exam", "trigger_central_alert"}
    tool_msg = second["messages"][-1]
    assert tool_msg["role"] == "tool" and json.loads(tool_msg["content"])["astronaut_id"] == "kenji_sato"


def test_groq_failure_falls_back_offline(groq, monkeypatch):
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_groq([FakeResponse({}, status=401)], []))
    res = asyncio.run(AstraCareOrchestrator(MissionStateManager()).handle_chat("como estou?"))
    assert res.mode == "offline_hybrid_edge"


def test_tool_schema_types():
    tools = build_mission_tools(MissionAgentTools(MissionStateManager()), [])
    schemas = {s["function"]["name"]: s["function"]["parameters"] for s in map(llm_groq.tool_schema, tools)}
    exam = schemas["schedule_smartwatch_exam"]
    assert exam["required"] == ["astronaut_id"]
    assert exam["properties"]["interval_minutes"]["type"] == "number"
    assert exam["properties"]["trigger_now"]["type"] == "boolean"
