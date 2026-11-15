"""Multi-tool monitoring agent: each tool alone, the chaining decisions, the scheduler and the HTTP layer."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.agent.mission_tools import MissionAgentTools, build_mission_tools
from app.agent.orchestrator import AstraCareOrchestrator
from app.engine.smartwatch_scheduler import SmartwatchScheduler
from app.state_manager import MissionStateManager

PSYCH = {"mood_score": 2, "ctb_reaction_time_ms": 520, "sleep_hours": 4.0}


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


@pytest.fixture()
def sm(tmp_path, monkeypatch):
    monkeypatch.setenv("ASTRACARE_STATE_DIR", str(tmp_path))
    return MissionStateManager()


@pytest.fixture()
def clock():
    return Clock()


@pytest.fixture()
def agent(sm, clock):
    return MissionAgentTools(sm, SmartwatchScheduler(sm, clock=clock), clock=clock)


# ---------------------------------------------------------------- tool 1
def test_exam_collects_payload_and_points_to_analysis(agent):
    out = agent.schedule_smartwatch_exam("elena_vance", "cardio", trigger_now=True)
    assert out["collected"] and out["next_tool"] == "analyze_telemetry_and_diagnose"
    assert {"heart_rate_bpm", "bp_systolic", "radiation_msv_h", "mood_score"} <= set(out["telemetry_payload"])


def test_exam_rejects_bad_input(agent):
    with pytest.raises(KeyError):
        agent.schedule_smartwatch_exam("nobody", "cardio")
    with pytest.raises(ValueError):
        agent.schedule_smartwatch_exam("elena_vance", "xray")
    with pytest.raises(ValueError):
        agent.schedule_smartwatch_exam("elena_vance", "cardio", interval_minutes=None, trigger_now=False)


def test_scheduled_exam_runs_full_chain_when_due(agent, clock):
    agent.schedule_smartwatch_exam("kenji_sato", "cognitive_ctb", interval_minutes=15, trigger_now=False)
    assert agent.run_due_schedules() == []
    clock.now += timedelta(minutes=16)
    results = agent.run_due_schedules()
    assert len(results) == 1 and results[0]["chain"][:2] == ["schedule_smartwatch_exam", "analyze_telemetry_and_diagnose"]
    assert agent.scheduler.list_schedules("kenji_sato")[0]["runs"] == 1
    assert agent.run_due_schedules() == []  # next run moved 15 min ahead


# ---------------------------------------------------------------- tool 2
def test_nominal_reading_is_normal_none(agent):
    report = agent.analyze_telemetry_and_diagnose("elena_vance")
    assert report["status"] == "NORMAL" and report["category"] == "NONE"
    assert report["next_tools"] == []
    assert 0 <= report["confidence_score"] <= 1


def test_behaviour_change_without_physical_cause_is_psychological(agent):
    report = agent.analyze_telemetry_and_diagnose("kenji_sato", PSYCH)
    assert report["category"] == "PSYCHOLOGICAL"
    assert "activate_psychological_stimuli" in report["next_tools"]


def test_same_change_during_solar_storm_is_not_psychological(agent):
    report = agent.analyze_telemetry_and_diagnose(
        "kenji_sato", {**PSYCH, "radiation_msv_h": 0.9}, {"SEP": [{"class": "S2"}], "alert_level": "WARNING"}
    )
    assert report["category"] == "PHYSICAL_ENVIRONMENTAL"
    assert report["root_cause"] == "EXTERNAL_SPACE_WEATHER"
    assert "activate_psychological_stimuli" not in report["next_tools"]


def test_space_weather_counts_become_events(agent):
    report = agent.analyze_telemetry_and_diagnose("amara_okafor", {"radiation_msv_h": 1.4}, {"active_sep_count": 2})
    assert report["root_cause"] == "EXTERNAL_SPACE_WEATHER" and report["status"] == "CRITICAL"


# ---------------------------------------------------------------- tool 3
def test_central_alert_dispatches_once_then_cooldown(agent, sm, clock):
    report = agent.analyze_telemetry_and_diagnose("amara_okafor", {"radiation_msv_h": 1.4}, {"active_sep_count": 2})
    first = agent.trigger_central_alert("amara_okafor", report)
    assert first["dispatched"] and first["earth_package_id"]
    assert any(e["event_type"] == "AGENT_CENTRAL_ALERT" for e in sm.earth_sync.audit_log)
    assert sm.get_state("amara_okafor").active_alert is not None
    assert not agent.trigger_central_alert("amara_okafor", report)["dispatched"]
    clock.now += timedelta(minutes=31)
    assert agent.trigger_central_alert("amara_okafor", report)["dispatched"]


def test_central_alert_skips_mild_findings(agent):
    out = agent.trigger_central_alert("elena_vance", {"status": "WARNING", "earth_priority": "ROUTINE"})
    assert not out["dispatched"]


# ---------------------------------------------------------------- tool 4
def test_stimuli_withheld_for_physical_cause(agent):
    out = agent.activate_psychological_stimuli("amara_okafor", {"category": "PHYSICAL_ENVIRONMENTAL"})
    assert not out["activated"]


def test_stimuli_for_psychological_cause_keep_active_crew(agent, sm):
    sm.select_crew_member("elena_vance")
    out = agent.activate_psychological_stimuli("kenji_sato", {"category": "PSYCHOLOGICAL", "probable_diagnosis": "stress"})
    assert out["activated"] and out["stimuli"]
    assert sm.active_crew_id == "elena_vance"


# ---------------------------------------------------------------- chain + chat wrappers
def test_cycle_chains_alert_and_stimuli_for_psychological_case(agent, monkeypatch):
    real = agent.analyze_telemetry_and_diagnose
    monkeypatch.setattr(agent, "analyze_telemetry_and_diagnose", lambda cid, payload=None, ctx=None: real(cid, PSYCH))
    out = agent.run_monitoring_cycle("kenji_sato")
    assert out["category"] == "PSYCHOLOGICAL"
    assert out["chain"][-1] == "activate_psychological_stimuli"


def test_llm_wrappers_chain_from_stored_report(agent):
    log = []
    tools = {t.name: t for t in build_mission_tools(agent, log)}
    report = json.loads(tools["analyze_telemetry_and_diagnose"].invoke(
        {"astronaut_id": "amara_okafor", "telemetry_json": '{"radiation_msv_h": 1.4}', "space_weather_json": '{"active_sep_count": 1}'}
    ))
    alert = json.loads(tools["trigger_central_alert"].invoke({"astronaut_id": "amara_okafor"}))
    assert report["status"] == "CRITICAL" and alert["dispatched"]
    assert json.loads(tools["schedule_smartwatch_exam"].invoke({"astronaut_id": "nobody"}))["error"]
    assert [t.tool_name for t in log][:2] == ["analyze_telemetry_and_diagnose", "trigger_central_alert"]


def test_offline_chat_runs_exam_intent(sm, agent):
    orch = AstraCareOrchestrator(sm, agent)
    res = asyncio.run(orch.handle_chat("agendar exame cardio do kenji a cada 30 min"))
    names = [t.tool_name for t in res.tool_trace]
    assert "schedule_smartwatch_exam" in names and "analyze_telemetry_and_diagnose" in names
    sched = agent.scheduler.list_schedules("kenji_sato")[0]
    assert sched["exam_type"] == "cardio" and sched["interval_minutes"] == 30


# ---------------------------------------------------------------- HTTP
def test_http_endpoints():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.post("/api/agent/smartwatch/liam_soren", json={"exam_type": "dosimetry", "interval_minutes": 60})
    assert r.status_code == 200 and r.json()["schedule"]["interval_minutes"] == 60
    assert any(s["astronaut_id"] == "liam_soren" for s in client.get("/api/agent/smartwatch").json())
    assert client.delete("/api/agent/smartwatch/liam_soren/dosimetry").json() == {"cancelled": True}
    r = client.post("/api/agent/analyze/liam_soren", json={"telemetry_payload": {"heart_rate_bpm": 70}})
    assert r.status_code == 200 and r.json()["status"] in ("NORMAL", "WARNING", "CRITICAL")
    assert client.post("/api/agent/cycle/nobody").status_code == 404
    assert client.post("/api/agent/smartwatch/liam_soren", json={"exam_type": "xray"}).status_code == 422
