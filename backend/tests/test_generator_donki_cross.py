"""Stochastic generator (phase 2), NASA DONKI integration (phase 3) and cross-diagnosis tree (phase 4)."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest import mock

import httpx
import numpy as np
import pytest

from app.engine import nasa_calibration as cal
from app.engine import nasa_feeds
from app.engine.cross_diagnosis import evaluate_cross_diagnosis
from app.engine.nasa_feeds import summarize_donki
from app.engine.telemetry_generator import CRISIS_PROFILES, TelemetryGenerator

ASTRONAUTS = ["elena_vance", "lucas_ferreira", "kenji_sato"]


def _now_str(hours_ago: float = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%MZ")


def _cross(st, message=None, space_weather=None):
    return evaluate_cross_diagnosis(
        st.vitals, st.mission_context, space_weather if space_weather is not None else st.space_weather,
        st.contextual_intelligence, st.clinical_evaluation, message,
    )


# ---------------- Phase 2: generator ----------------
@pytest.mark.parametrize("astro", ASTRONAUTS)
def test_nominal_series_stays_in_nasa_inflight_ranges(astro):
    from app.main import state_manager as sm

    gen = TelemetryGenerator(sm.astronauts_by_id[astro], "chronic_microgravity_cruise")
    _, series = gen.generate("nominal", 142)
    mean = lambda key: float(np.mean([r[key] for r in series]))  # noqa: E731
    assert 55 <= mean("hr") <= 85
    assert 105 <= mean("bp_sys") <= 125 and 60 <= mean("bp_dia") <= 75
    assert 36.3 <= mean("temp") <= 37.2
    assert 75 <= mean("glucose") <= 115
    assert 5.4 <= mean("sleep") <= 6.4  # ~5.8-6.0 h in-flight, with personal noise
    assert 0.02 <= mean("radiation") <= 0.045  # 0.6-0.9 mSv/day
    assert 240 <= mean("ctb") <= 310


def test_generation_is_reproducible_and_readings_are_stochastic():
    from app.main import state_manager as sm

    gen = TelemetryGenerator(sm.astronauts_by_id["elena_vance"], "chronic_microgravity_cruise")
    v1, s1 = gen.generate("systemic_infection", 145)
    v2, s2 = gen.generate("systemic_infection", 145)
    assert s1 == s2 and v1 == v2
    rng = np.random.default_rng(0)
    r1, r2 = gen.next_reading("systemic_infection", v1, rng), gen.next_reading("systemic_infection", v1, rng)
    assert r1["heart_rate_bpm"] != r2["heart_rate_bpm"]


def test_every_crisis_profile_triggers_its_syndrome_for_every_astronaut():
    from app.main import state_manager as sm

    mismatches = []
    for astro in ASTRONAUTS:
        sm.switch_astronaut(astro)
        for crisis in CRISIS_PROFILES:
            st = sm.switch_scenario(crisis)
            if st.clinical_evaluation.syndrome_code != crisis:
                mismatches.append((astro, crisis, st.clinical_evaluation.syndrome_code))
    sm.switch_astronaut("elena_vance")
    assert mismatches == []


def test_scenarios_file_has_no_static_vitals():
    from app.main import state_manager as sm

    for sc in sm.catalog["scenarios"]:
        assert "vitals" not in sc and "longitudinal_series" not in sc


def test_next_reading_endpoint(client):
    client.post("/api/scenario/nominal")
    a = client.post("/api/telemetry/next").json()["vitals"]["heart_rate_bpm"]
    b = client.post("/api/telemetry/next").json()["vitals"]["heart_rate_bpm"]
    assert a != b
    assert client.post("/api/telemetry/next?crisis_probability=2").status_code == 422


# ---------------- Phase 3: DONKI ----------------
def test_donki_summary_levels():
    sep = {"SEP": [{"sepID": "s", "eventTime": _now_str(2)}], "FLR": [], "RBE": []}
    assert summarize_donki(sep, source="live_nasa_donki", fetch_status="live").status_label == "SEP alert active"
    m = {"SEP": [], "FLR": [{"flrID": "f", "beginTime": _now_str(5), "classType": "M2.1"}], "RBE": []}
    s = summarize_donki(m, source="live_nasa_donki", fetch_status="live")
    assert s.alert_level == "WARNING" and "M2.1" in s.status_label
    old = {"SEP": [{"sepID": "s", "eventTime": "2020-01-01T00:00Z"}], "FLR": [], "RBE": []}
    assert summarize_donki(old, source="live_nasa_donki", fetch_status="live").alert_level == "NOMINAL"


class _Resp:
    def __init__(self, code, body):
        self.status_code, self._body, self.content = code, body, b"x"

    def json(self):
        return self._body


def test_donki_rate_limit_falls_back_then_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(nasa_feeds, "DONKI_CACHE_PATH", tmp_path / "donki_cache.json")

    async def limited(self, url, params=None):
        return _Resp(429, {})

    async def live(self, url, params=None):
        return _Resp(200, [{"flrID": "f", "beginTime": _now_str(1), "classType": "X1.0"}] if url.endswith("FLR") else [])

    with mock.patch.object(httpx.AsyncClient, "get", limited):
        s = asyncio.run(nasa_feeds.fetch_nasa_space_weather(force=True))
    assert s.source == "curated_local_fallback" and "429" in s.fetch_status

    with mock.patch.object(httpx.AsyncClient, "get", live):
        s = asyncio.run(nasa_feeds.fetch_nasa_space_weather(force=True))
    assert s.source == "live_nasa_donki" and s.alert_level == "CRITICAL"

    with mock.patch.object(httpx.AsyncClient, "get", limited):
        s = asyncio.run(nasa_feeds.fetch_nasa_space_weather(force=True))
    assert s.source == "cached_nasa_donki" and "X1.0" in s.status_label


def test_curated_fallback_is_in_donki_schema_and_never_active():
    raw = nasa_feeds.load_sample_donki_raw()
    assert set(raw) == {"SEP", "FLR", "RBE"}
    assert all("flrID" in e and "beginTime" in e for e in raw["FLR"])
    assert summarize_donki(raw, source="curated_local_fallback", fetch_status="x").alert_level == "NOMINAL"


# ---------------- Phase 4: cross diagnosis ----------------
@pytest.mark.parametrize(
    "scenario,layer,root",
    [
        ("nominal", 0, "NOMINAL"),
        ("solar_storm", 1, "EXTERNAL_SPACE_WEATHER"),
        ("systemic_infection", 2, "INTERNAL_PHYSIOLOGICAL"),
        ("orthostatic_intolerance", 2, "INTERNAL_PHYSIOLOGICAL"),
        ("cabin_co2_pocket", 2, "ONBOARD_ENVIRONMENT"),
        ("post_exercise_physiological", 2, "CONTEXTUAL_BENIGN"),
        ("behavioral_fatigue", 3, "PSYCHOLOGICAL_NEUROCOGNITIVE"),
    ],
)
def test_tree_layer_per_scenario(client, scenario, layer, root):
    c = client.post(f"/api/scenario/{scenario}").json()["cross_diagnosis"]
    assert (c["layer"], c["root_cause"]) == (layer, root)


def test_storm_layer_blocks_eva_and_notifies_earth(client):
    c = client.post("/api/scenario/solar_storm").json()["cross_diagnosis"]
    assert c["eva_hold_recommended"] and c["shelter_recommended"] and c["earth_priority"] == "IMMEDIATE"
    assert any("scenario simulation" in d for d in c["donki_events_considered"])


def test_active_flare_does_not_mask_an_infection():
    from app.main import state_manager as sm

    st = sm.switch_scenario("systemic_infection")
    flare = summarize_donki(
        {"SEP": [], "FLR": [{"flrID": "f", "beginTime": _now_str(2), "classType": "X2.0"}], "RBE": []},
        source="live_nasa_donki", fetch_status="live",
    )
    c = _cross(st, space_weather=flare)
    assert c.root_cause == "INTERNAL_PHYSIOLOGICAL" and "infection" in c.title.lower()


def test_dose_spike_without_donki_is_onboard_not_storm():
    from app.main import state_manager as sm

    st = sm.switch_scenario("solar_storm")
    nominal_sw = summarize_donki({"SEP": [], "FLR": [], "RBE": []}, source="live_nasa_donki", fetch_status="live")
    c = _cross(st, space_weather=nominal_sw)
    assert c.root_cause == "ONBOARD_ENVIRONMENT"


def test_psych_layer_reassures_with_real_values_and_escalates_severe_risk():
    from app.main import state_manager as sm

    st = sm.switch_scenario("nominal")
    c = _cross(st, "sinto um cheiro estranho e estou irritado")
    assert c.layer == 3 and c.psych_protocol and not c.psych_protocol.escalate_to_earth
    assert any("heart rate" in chk for chk in c.psych_protocol.verified_safe_checks)

    severe = _cross(st, "nada importa, nao quero mais viver")
    assert severe.psych_protocol.escalate_to_earth and severe.earth_priority == "IMMEDIATE"

    st = sm.switch_scenario("systemic_infection")
    physical_plus_risk = _cross(st, "quero me machucar")
    assert physical_plus_risk.root_cause == "INTERNAL_PHYSIOLOGICAL" and physical_plus_risk.earth_priority == "IMMEDIATE"


def test_light_flashes_without_radiation_are_not_sent_to_psych():
    from app.main import state_manager as sm

    st = sm.switch_scenario("nominal")
    c = _cross(st, "vejo flashes de luz")
    assert c.layer == 2 and c.root_cause == "INTERNAL_PHYSIOLOGICAL"


def test_status_question_does_not_dispatch_psych_alert(client):
    client.post("/api/scenario/behavioral_fatigue")
    before = len(client.get("/api/psych/central-alerts").json())
    r = client.post("/api/agent/chat", json={"message": "Qual o status dos casos de acompanhamento?"}).json()
    assert "Camada 3" in r["reply"]  # protocol text, not an alert
    assert len(client.get("/api/psych/central-alerts").json()) == before


def test_severe_message_sends_immediate_earth_alert(client):
    client.post("/api/scenario/nominal")
    r = client.post("/api/agent/chat", json={"message": "nada importa, nao quero mais viver"}).json()
    assert "Terra" in r["reply"]
    events = [e["event_type"] for e in client.get("/api/earth-sync/ledger").json()["audit_log"]]
    assert "PSYCH_CRITICAL_ESCALATION" in events


def test_thresholds_match_spec_table():
    assert (cal.HR_CRIT_LOW, cal.HR_CRIT_HIGH) == (45, 115)
    assert (cal.BP_SYS_CRIT_LOW, cal.BP_SYS_CRIT_HIGH) == (90, 145)
    assert cal.CTB_CRIT_MS == 390 and cal.SLEEP_CRIT_H == 4.5 and cal.SLEEP_CRIT_NIGHTS == 2
    assert cal.RADIATION_SPE_RATE_MSV_H == 0.5 and cal.CAREER_LIMIT_MSV == 600 and cal.SPE_EVENT_LIMIT_MSV == 250


# ---------------- ML trained on the generator ----------------
def test_ml_uses_new_features_and_states_its_data_source(client):
    m = client.get("/api/ml/validation").json()
    for f in ("ctb_reaction_time_ms", "personal_envelope_deviations", "donki_activity", "behavioural_symptom_flag"):
        assert f in m["feature_names"]
    assert "synthetic" in m["training_data_source"]
    assert m["training_samples"] >= 900 and m["macro_f1_score"] > 90


def test_ml_classifies_every_profile_for_every_roster_astronaut():
    from app.main import state_manager as sm

    misses = []
    for cid in sm.crew_records:
        sm.select_crew_member(cid)
        for crisis in CRISIS_PROFILES:
            got = sm.switch_scenario(crisis).ml_prediction.predicted_syndrome
            if got != crisis:
                misses.append((cid, crisis, got))
    sm.select_crew_member("elena_vance")
    assert misses == []


def test_ml_attribution_is_clinically_plausible():
    from app.main import state_manager as sm

    top = lambda sc: [f.feature for f in sm.switch_scenario(sc).ml_prediction.feature_importances[:3]]  # noqa: E731
    assert "ctb_reaction_time_ms" in top("behavioral_fatigue")
    assert "radiation_msv_h" in top("solar_storm")
    assert "glucose_mg_dl" in top("hypoglycemia")
