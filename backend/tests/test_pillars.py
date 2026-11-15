"""Behavioural checks for the five backend pillars (run: python -m pytest -q from backend/)."""

from datetime import datetime, timedelta, timezone

from app.engine.earth_sync import EarthSyncManager
from app.engine.followup_loop import FollowUpCaseManager
from app.ml.adaptive_baseline import AdaptiveBaselineEngine
from app.models.schemas import EscalateCaseRequest, MissionContext, RecordActionRequest, VitalSigns


# ---------- Pillar 1: adaptive individual baseline ----------
def test_slow_pathological_ramp_is_quarantined_not_learned(client):
    st = client.post("/api/scenario/systemic_infection").json()
    hr = st["adaptive_baseline"]["metrics"]["heart_rate_bpm"]
    # Ramp days (78..104 bpm) must not drag the personal baseline upward.
    assert hr["history_points_quarantined"] >= 3
    assert hr["rolling_ewma_baseline"] < 72
    assert hr["status_vs_personal"] == "SIGNIFICANT_PERSONAL_DEVIATION"
    assert hr["trend_status"] == "SUSTAINED_DRIFT"


def test_nominal_scenario_stays_within_personal_band(client):
    st = client.post("/api/scenario/nominal").json()
    ab = st["adaptive_baseline"]
    assert not ab["is_personally_anomalous"]
    assert ab["drifting_metrics"] == []
    assert st["explainable_alerts"] == []


def test_acute_spike_is_deviation_but_not_multi_day_drift(client):
    st = client.post("/api/scenario/post_exercise_physiological").json()
    hr = st["adaptive_baseline"]["metrics"]["heart_rate_bpm"]
    assert hr["individual_z_score"] > 2.5
    assert hr["trend_status"] == "STABLE"


def test_baseline_is_reproducible_across_engine_instances(client):
    state = client.get("/api/state").json()
    from app.main import state_manager as sm

    astro = sm.astronauts_by_id[sm.astronaut_id]
    args = (astro, sm.vitals, sm.mission_context, sm.longitudinal_series, sm.mission_day)
    a = AdaptiveBaselineEngine().evaluate(*args)
    b = AdaptiveBaselineEngine().evaluate(*args)
    assert a.multivariate_mahalanobis_distance == b.multivariate_mahalanobis_distance
    assert state["adaptive_baseline"]["astronaut_id"] == a.astronaut_id


def test_phase_prior_shifts_the_anchor():
    astro = {"astronaut_id": "t", "name": "T", "pre_flight_baseline": {"heart_rate_bpm": 60}, "natural_std": {}}
    from app.main import state_manager as sm

    eng = AdaptiveBaselineEngine()
    v = VitalSigns(**sm.scenarios_by_id["nominal"]["vitals"])
    earth = eng.evaluate(astro, v, MissionContext(mission_phase="pre_flight_1g"), [], 1)
    cruise = eng.evaluate(astro, v, MissionContext(mission_phase="chronic_microgravity_cruise"), [], 1)
    assert (
        cruise.metrics["heart_rate_bpm"].phase_adapted_baseline
        != earth.metrics["heart_rate_bpm"].phase_adapted_baseline
    )


# ---------- Pillar 2: contextual intelligence ----------
def test_context_is_reported_without_claiming_causality(client):
    st = client.post("/api/scenario/post_exercise_physiological").json()
    ctx = st["contextual_intelligence"]
    assert any(a["factor_id"] == "CTX-EXERCISE-RECOVERY" for a in ctx["associations"])
    assert ctx["context_explains_deviation"] is True
    for alert in st["explainable_alerts"]:
        assert "causal" in alert["causal_disclaimer"].lower() or "causa" in alert["causal_disclaimer"].lower()


# ---------- Pillar 4: explainable & auditable alerts ----------
def test_every_alert_is_explainable_and_guardrailed(client):
    st = client.post("/api/scenario/systemic_infection").json()
    assert st["explainable_alerts"]
    for alert in st["explainable_alerts"]:
        assert alert["originating_signals"], "alert must show the data that triggered it"
        assert "overall_quality_pct" in alert["measurement_quality"]
        assert "total_uncertainty_pct" in alert["uncertainty"]
        assert alert["scientific_references"], "alert must cite a source/protocol"
        g = alert["autonomy_guardrail"]
        assert g["autonomous_diagnosis_blocked"] and g["autonomous_treatment_blocked"]
        assert g["human_in_the_loop_required"]
        assert alert["followup_case_id"], "every alert must open a follow-up case"


# ---------- Pillar 3: closed-loop follow-up ----------
def test_followup_full_cycle_via_api(client):
    st = client.post("/api/scenario/hypoglycemia").json()
    case_id = st["explainable_alerts"][0]["followup_case_id"]
    case = next(c for c in st["followup_cases"] if c["case_id"] == case_id)
    assert case["status"] == "OPEN_PENDING_CONFIRMATION"
    assert case["reassessments_scheduled"][0]["due_at"]
    assert "Confirmation measurement not yet recorded." in case["pending_items"]

    case = client.post(
        f"/api/followup/{case_id}/confirm", json={"metric": "glucose_mg_dl", "measured_value": 58}
    ).json()
    assert case["status"] == "CONFIRMED_ACTIVE_MONITORING"

    case = client.post(
        f"/api/followup/{case_id}/action", json={"action_description": "15 g fast carbohydrate per protocol"}
    ).json()
    assert case["status"] == "ACTION_EXECUTED_AWAITING_REASSESSMENT"
    reassess_id = case["reassessments_scheduled"][-1]["reassessment_id"]

    case = client.post(
        f"/api/followup/{case_id}/reassess", json={"reassessment_id": reassess_id, "resolve_case": True}
    ).json()
    assert case["status"] == "RESOLVED"
    assert case["pending_items"] == []

    # A resolved case is closed: further changes are rejected, not silently re-opened.
    r = client.post(f"/api/followup/{case_id}/action", json={"action_description": "late entry"})
    assert r.status_code == 409


def test_confirmation_within_personal_band_downgrades_case(client):
    st = client.post("/api/scenario/systemic_infection").json()
    case_id = st["explainable_alerts"][0]["followup_case_id"]
    baseline = st["adaptive_baseline"]["metrics"]["temperature_c"]["rolling_ewma_baseline"]
    case = client.post(
        f"/api/followup/{case_id}/confirm", json={"metric": "temperature_c", "measured_value": baseline}
    ).json()
    assert case["status"] == "DOWNGRADED_CONFOUNDER_OR_ARTIFACT"


def test_overdue_reassessment_and_human_escalation(tmp_path):
    now = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    mgr = FollowUpCaseManager(store_path=tmp_path / "cases.json", clock=lambda: now[0])
    from app.main import state_manager as sm

    alerts = sm.get_state().explainable_alerts or []
    if not alerts:
        sm.switch_scenario("systemic_infection")
        alerts = sm.get_state().explainable_alerts
    alert = alerts[0].model_copy(deep=True)
    alert.severity = "CRITICAL"
    [case] = mgr.sync_alerts([alert], "elena_vance", "Elena", 1, [])

    now[0] += timedelta(minutes=16)  # CRITICAL reassessment is due at T+15
    case = mgr.list_cases_for_astronaut("elena_vance")[0]
    assert case.overdue_reassessments == 1
    assert case.reassessments_scheduled[0].status == "OVERDUE"
    assert any("Flight Surgeon escalation" in p for p in case.pending_items)
    assert case.status == "OPEN_PENDING_CONFIRMATION"  # the engine flags, it does not escalate by itself

    case = mgr.escalate(case.case_id, EscalateCaseRequest(reason="persistent fever"))
    assert case.status == "ESCALATED_TO_EARTH"
    mgr.record_action(case.case_id, RecordActionRequest(action_description="antipyretic per ground order"))
    assert mgr.cases[case.case_id].status == "ESCALATED_TO_EARTH"

    # Persisted offline: a fresh manager (onboard computer restart) sees the same case.
    reloaded = FollowUpCaseManager(store_path=tmp_path / "cases.json", clock=lambda: now[0])
    assert reloaded.cases[case.case_id].status == "ESCALATED_TO_EARTH"
    assert len(reloaded.cases[case.case_id].actions_executed) == 1


# ---------- Pillar 5: ship <-> Earth continuity ----------
def test_package_chain_verifies_and_detects_tampering(client):
    client.post("/api/scenario/solar_storm")
    p1 = client.post("/api/earth-sync/package").json()
    p2 = client.post("/api/earth-sync/package").json()
    assert p2["previous_package_hash"] == p1["sha256_integrity_hash"]
    assert client.get("/api/earth-sync/verify").json()["verified"] is True

    from app.main import state_manager as sm

    sm.earth_sync.packages[-1].executive_summary += " (edited)"
    report = client.get("/api/earth-sync/verify").json()
    assert report["verified"] is False
    assert any("content hash mismatch" in i for i in report["package_issues"])
    sm.earth_sync.packages.pop()  # restore for other tests


def test_packages_stay_queued_without_comms_window(tmp_path):
    from app.main import state_manager as sm

    esm = EarthSyncManager(ledger_path=tmp_path / "ledger.json")
    st = sm.get_state()
    link = st.horizons_link.model_copy(update={"comms_available": False})
    esm.build_and_queue_package(
        astronaut_id=st.astronaut_id,
        crew_member=st.crew_member,
        mission_day=st.mission_day,
        environment_id=st.environment_id,
        horizons_link=link,
        space_weather_alert="NOMINAL",
        adaptive_baseline=st.adaptive_baseline,
        contextual_report=st.contextual_intelligence,
        ml_prediction=st.ml_prediction,
        explainable_alerts=st.explainable_alerts,
        followup_cases=st.followup_cases,
        longitudinal_series=st.longitudinal_series,
        forecast_72h=st.ml_prediction.forecast_72h,
        auto_sync_if_low_latency=True,
    )
    esm.synchronize_queued_packages(comms_available=False)
    assert esm.pending_count() == 1
    esm.synchronize_queued_packages(comms_available=True)
    assert esm.pending_count() == 0
    # Ledger survives restart and the sync handshake did not break the chain.
    reloaded = EarthSyncManager(ledger_path=tmp_path / "ledger.json")
    assert reloaded.verify_integrity()["verified"] is True
