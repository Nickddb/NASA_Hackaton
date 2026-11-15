from __future__ import annotations

import inspect
import re
from typing import Any, Callable

from app.models.schemas import (
    CompleteReassessmentRequest,
    ContextUpdateRequest,
    RecordActionRequest,
    RecordConfirmationRequest,
    ToolTraceItem,
)
from app.state_manager import MissionStateManager


class _FastTool:
    """Zero-overhead callable tool wrapper compatible with both offline edge and LangChain."""

    def __init__(self, fn: Callable[..., str]) -> None:
        self.fn = fn
        self.name = fn.__name__
        self.description = (fn.__doc__ or "").strip()
        self._sig = inspect.signature(fn)

    def invoke(self, args: dict[str, Any] | str | None = None) -> str:
        if args is None:
            return self.fn()
        if isinstance(args, str):
            return self.fn(args)
        valid_kwargs = {k: v for k, v in args.items() if k in self._sig.parameters}
        return self.fn(**valid_kwargs)

    def to_langchain_tool(self) -> Any:
        from langchain_core.tools import tool as lc_tool

        return lc_tool(self.fn)


def tool(fn: Callable[..., str]) -> _FastTool:
    return _FastTool(fn)

# Spaceflight-calibrated food database (per 1 unit/serving)
FOOD_DB: list[tuple[list[str], str, float, float, float, float, float, float, float]] = [
    # (keywords, label, kcal, water_ml, protein_g, carbs_g, fiber_g, sodium_mg, iron_mg)
    (["apple", "apples", "maça", "maçã", "macas", "maçãs"], "Fresh/Freeze-Dried Apple", 95, 80, 0.5, 25, 4.4, 2, 0.2),
    (["banana", "bananas"], "Banana Pouch", 105, 65, 1.3, 27, 3.1, 1, 0.3),
    (["bar", "protein bar", "barra"], "Space Nutrition Protein Bar", 240, 10, 20, 24, 4.0, 210, 2.2),
    (["glucose", "gel", "carb", "candy", "dextrose", "glicose"], "Rapid Glucose Gel Pouch", 90, 25, 0, 22, 0, 45, 0.0),
    (["salad", "veggie", "spinach", "lettuce", "salada"], "Hydroponic ISS Salad", 85, 120, 4.0, 12, 4.5, 95, 1.4),
    (["chicken", "beef", "meat", "teriyaki", "meal", "dinner", "lunch", "frango", "carne", "refeição", "almoço", "jantar"], "Thermostabilized Entree Pouch", 460, 110, 34, 42, 4.0, 680, 2.8),
    (["soup", "broth", "sopa", "caldo"], "Rehydrated Electrolyte Broth", 160, 260, 8.0, 18, 2.0, 740, 0.9),
    (["coffee", "tea", "café", "cafe", "chá"], "Space Beverage Pouch (No-Sugar)", 15, 240, 0, 2, 0, 10, 0.1),
    (["saline", "electrolyte", "isotonic", "soro", "isotônico"], "Isotonic Electrolyte Hydration", 45, 500, 0, 11, 0, 460, 0.0),
    (["oatmeal", "breakfast", "cereal", "aveia"], "Rehydrated Space Oatmeal", 290, 180, 10, 50, 6.0, 180, 1.8),
]


def parse_nutrition_text(text: str) -> dict[str, Any]:
    lower = text.lower()
    total: dict[str, Any] = {
        "items": [],
        "calories_kcal": 0.0,
        "water_ml": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fiber_g": 0.0,
        "sodium_mg": 0.0,
        "iron_mg": 0.0,
    }

    water_ml_matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(ml|mL|l|liter|liters|litro|litros)\b", lower)
    for num_str, unit in water_ml_matches:
        val = float(num_str.replace(",", "."))
        ml = val * 1000.0 if unit.startswith("l") else val
        total["water_ml"] += ml
        total["items"].append(f"{ml:.0f}ml Potable Water (PWD)")

    if not water_ml_matches and any(w in lower for w in ["water", "agua", "água", "hydrate", "drank", "bebi"]):
        total["water_ml"] += 300.0
        total["items"].append("300ml Potable Water (PWD)")

    for keywords, label, kcal, w_ml, prot, carbs, fiber, na, fe in FOOD_DB:
        matched_kw = next((kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", lower)), None)
        if matched_kw:
            qty_match = re.search(rf"(\d+)\s+{re.escape(matched_kw)}\b", lower)
            qty = min(int(qty_match.group(1)), 10) if qty_match else 1
            total["calories_kcal"] += kcal * qty
            total["water_ml"] += w_ml * qty
            total["protein_g"] += prot * qty
            total["carbs_g"] += carbs * qty
            total["fiber_g"] += fiber * qty
            total["sodium_mg"] += na * qty
            total["iron_mg"] += fe * qty
            total["items"].append(f"{qty}x {label}")

    kcal_match = re.search(r"(\d+)\s*(kcal|cal|calories|calorias)\b", lower)
    if kcal_match and total["calories_kcal"] == 0:
        kcal_val = float(kcal_match.group(1))
        total["calories_kcal"] += kcal_val
        total["carbs_g"] += round(kcal_val * 0.12, 1)
        total["protein_g"] += round(kcal_val * 0.04, 1)
        total["items"].append(f"Custom Meal ({kcal_val:.0f} kcal)")

    return total


def parse_sleep_mood_context_text(text: str) -> dict[str, Any]:
    lower = text.lower()
    updates: dict[str, Any] = {}

    sleep_match = re.search(
        r"(?:slept|sleep|dormi|sono)[^\d]{0,14}(\d+(?:[.,]\d+)?)\s*(?:h|hr|hrs|hours|horas)?",
        lower,
    )
    if sleep_match:
        updates["sleep_hours"] = float(sleep_match.group(1).replace(",", "."))

    mood_match = re.search(r"(?:mood|humor)[^\d]{0,8}([1-5])", lower)
    if mood_match:
        updates["mood_score"] = int(mood_match.group(1))
    elif any(w in lower for w in ["exhausted", "dizzy", "anxious", "stressed", "terrible", "cansado", "exausto", "tonto"]):
        updates["mood_score"] = 2
        updates["stress_index"] = 78.0
    elif any(w in lower for w in ["great", "good", "energized", "calm", "nominal", "bem", "ótimo", "otimo"]):
        updates["mood_score"] = 5
        updates["stress_index"] = 22.0

    pain_match = re.search(r"(?:pain|dor|vas)[^\d]{0,8}(\d{1,2})\s*(?:/\s*10)?", lower)
    if pain_match:
        updates["shoulder_pain_score"] = min(10, int(pain_match.group(1)))
    elif any(w in lower for w in ["shoulder", "ombro", "rotator", "hut"]):
        updates["shoulder_pain_score"] = 6

    ex_match = re.search(
        r"(?:exercise|workout|ared|t2|treadmill|treino|exercício|exercicio)[^\d]{0,18}(\d+)\s*(?:min|minutes|minutos|m)\b",
        lower,
    )
    if ex_match:
        updates["minutes_since_last_exercise"] = float(ex_match.group(1))
        updates["exercise_modality"] = "T2_treadmill" if "t2" in lower or "treadmill" in lower else "ARED_resistive"
    elif any(w in lower for w in ["just finished exercise", "after exercise", "post-exercise", "acabei de treinar", "pós-treino", "pos-treino"]):
        updates["minutes_since_last_exercise"] = 15.0
        updates["exercise_modality"] = "ARED_resistive"

    co2_match = re.search(r"co2[^\d]{0,10}(\d+(?:[.,]\d+)?)\s*(?:mmhg)?", lower)
    if co2_match:
        updates["cabin_co2_mmhg"] = float(co2_match.group(1).replace(",", "."))

    return updates


def parse_followup_command_text(text: str) -> dict[str, Any]:
    lower = text.lower()
    cmd: dict[str, Any] = {}

    if any(w in lower for w in ["confirm", "confirmed", "recheck", "rechecked", "confirmei", "confirmação", "confirmacao", "repeti"]):
        cmd["action_type"] = "confirm"
        temp_m = re.search(r"(\d{2}[.,]\d)\s*(?:c|°c|graus)?", lower)
        bp_m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", lower)
        glu_m = re.search(r"(\d{2,3})\s*mg/dl", lower)
        hr_m = re.search(r"(\d{2,3})\s*bpm", lower)

        if temp_m:
            cmd["metric"] = "temperature_c"
            cmd["value"] = float(temp_m.group(1).replace(",", "."))
            cmd["unit"] = "C"
        elif bp_m:
            cmd["metric"] = "bp_systolic"
            cmd["value"] = float(bp_m.group(1))
            cmd["unit"] = "mmHg"
        elif glu_m:
            cmd["metric"] = "glucose_mg_dl"
            cmd["value"] = float(glu_m.group(1))
            cmd["unit"] = "mg/dL"
        elif hr_m:
            cmd["metric"] = "heart_rate_bpm"
            cmd["value"] = float(hr_m.group(1))
            cmd["unit"] = "bpm"

    elif any(w in lower for w in ["executed", "administered", "isolated", "applied", "executei", "realizei", "administrei", "protocolo aplicado"]):
        cmd["action_type"] = "action"
        cmd["description"] = text.strip()

    elif any(w in lower for w in ["resolve case", "reassessed", "reavaliação concluída", "reavaliacao concluida", "resolver caso", "encerrar caso"]):
        cmd["action_type"] = "reassess"
        cmd["resolve"] = any(w in lower for w in ["resolve", "resolved", "resolver", "encerrar", "normalizou"])

    return cmd


def build_agent_tools(state_manager: MissionStateManager, trace_log: list[ToolTraceItem]) -> list[Any]:
    """Create the 9 LangChain @tool functions bound to the 5-pillar MissionStateManager."""

    @tool
    def inspect_adaptive_baseline_tool(astronaut_query: str = "current") -> str:
        """
        Pillar 1: Inspect the astronaut's Adaptive Individual Baseline (EWMA, MAD, Ledoit-Wolf Mahalanobis
        distance, NASA OSDR phase adaptation offset, and individual_z_score vs population_z_score).
        Can also switch astronaut profile if 'elena', 'lucas', or 'kenji' is named.
        """
        q_low = astronaut_query.lower()
        if "lucas" in q_low and state_manager.astronaut_id != "lucas_ferreira":
            state_manager.switch_astronaut("lucas_ferreira")
        elif "kenji" in q_low and state_manager.astronaut_id != "kenji_sato":
            state_manager.switch_astronaut("kenji_sato")
        elif "elena" in q_low and state_manager.astronaut_id != "elena_vance":
            state_manager.switch_astronaut("elena_vance")

        state = state_manager.get_state()
        ab = state.adaptive_baseline
        top_devs = sorted(
            ab.metrics.values(),
            key=lambda m: abs(m.individual_z_score),
            reverse=True,
        )[:4]
        dev_str = "; ".join(
            f"{m.label}: {m.current_value}{m.unit} (Personal EWMA={m.rolling_ewma_baseline}{m.unit}, "
            f"Personal z={m.individual_z_score:+.1f}σ vs Pop z={m.population_z_score:+.1f}σ [{m.status_vs_personal}])"
            for m in top_devs
        )

        trace_log.append(
            ToolTraceItem(
                tool_name="inspect_adaptive_baseline",
                status="WARNING" if ab.is_personally_anomalous else "OK",
                summary=f"{ab.astronaut_name}: Personal Drift {ab.personal_drift_score:.1f}% (Mahalanobis {ab.multivariate_mahalanobis_distance:.2f})",
                rule_or_score=ab.osdr_reference_study,
            )
        )
        return (
            f"Astronaut: {ab.astronaut_name} | Phase: {ab.mission_phase} ({ab.gravitational_g:.2f}g) | "
            f"Mahalanobis Distance: {ab.multivariate_mahalanobis_distance:.2f} | "
            f"Personal Drift Score: {ab.personal_drift_score:.1f}% | "
            f"Top Personal vs Population Deltas: {dev_str}"
        )

    @tool
    def evaluate_contextual_intelligence_tool(context_note: str = "evaluate") -> str:
        """
        Pillar 2: Evaluate Contextual Mission Intelligence (correlations with sleep, ARED/T2/CEVIS exercise,
        EVA workload, gravitational phase, and cabin CO2/O2 environment) with mandatory non-causality guardrail.
        """
        state = state_manager.get_state()
        ctx = state.contextual_intelligence
        mc = ctx.mission_context

        assoc_str = (
            "; ".join(
                f"{a.factor_name} ({a.relationship_type}, r={a.association_strength:.2f}): {a.rationale}"
                for a in ctx.associations[:3]
            )
            if ctx.associations
            else "No acute operational or environmental confounders detected."
        )

        trace_log.append(
            ToolTraceItem(
                tool_name="evaluate_contextual_intelligence",
                status="OK" if ctx.context_explains_deviation else ("WARNING" if ctx.associations else "OK"),
                summary=ctx.primary_contextual_summary[:110],
                rule_or_score=f"Attenuation -{ctx.context_anomaly_attenuation_pct:.0f}% | Non-Causal",
            )
        )
        return (
            f"Context: Phase={mc.mission_phase} ({mc.gravitational_g:.2f}g), "
            f"Exercise={mc.exercise_modality} ({mc.minutes_since_last_exercise:.0f}m ago), "
            f"EVA={mc.eva_status}, Cabin ppCO2={mc.cabin_co2_mmhg:.1f} mmHg. "
            f"Summary: {ctx.primary_contextual_summary} | Associations: {assoc_str} | "
            f"Guardrail: {ctx.causal_disclaimer}"
        )

    @tool
    def predict_calibrated_ml_and_uncertainty_tool(horizon: str = "72h") -> str:
        """
        Pillar 4 (ML): Run the Calibrated HistGradientBoosting + RandomForest + IsolationForest ensemble,
        quantify epistemic + aleatoric sensor uncertainty, counterfactual feature attribution, and 72h Bayesian forecast.
        """
        state = state_manager.get_state()
        ml = state.ml_prediction
        unc = ml.uncertainty
        drivers = ", ".join(
            f"{f.label}: {f.current_value} (personal base {f.personal_baseline_value}, z={f.individual_z_score:+.1f}σ, weight {f.importance:.0f}%)"
            for f in ml.feature_importances[:4]
        )
        fc_str = ", ".join(
            f"{pt.label}: HR={pt.predicted_hr_bpm:.0f}bpm (80% CI {pt.hr_ci_80[0]:.0f}-{pt.hr_ci_80[1]:.0f}), "
            f"HRV={pt.predicted_hrv_ms:.0f}ms, Glu={pt.predicted_glucose_mg_dl:.0f}mg/dL, Risk={pt.predicted_anomaly_risk_pct:.0f}%"
            for pt in ml.forecast_72h
        )

        trace_log.append(
            ToolTraceItem(
                tool_name="predict_calibrated_ml_and_uncertainty",
                status="CRITICAL" if ml.anomaly_score >= 70 else ("WARNING" if ml.anomaly_score >= 45 else "OK"),
                summary=(
                    f"{ml.predicted_syndrome_label} ({ml.confidence_pct:.1f}% ± {unc.total_uncertainty_pct:.1f}% unc | "
                    f"Sensor Grade: {unc.reliability_grade})"
                ),
                rule_or_score=f"Ctx-Adj Anomaly {ml.anomaly_score:.1f}% (Pop {ml.raw_population_anomaly_score:.1f}%, Pers {ml.personal_baseline_anomaly_score:.1f}%)",
            )
        )
        return (
            f"Context-Adjusted Anomaly Score: {ml.anomaly_score:.1f}% "
            f"(Personal Drift: {ml.personal_baseline_anomaly_score:.1f}%, Population IsoForest: {ml.raw_population_anomaly_score:.1f}%) | "
            f"Predicted Class: {ml.predicted_syndrome_label} ({ml.confidence_pct:.1f}% confidence, "
            f"95% CI [{unc.confidence_interval_95_pct[0]:.1f}%, {unc.confidence_interval_95_pct[1]:.1f}%]) | "
            f"Uncertainty: Total={unc.total_uncertainty_pct:.1f}% (Epistemic Ensemble={unc.epistemic_ensemble_std_pct:.1f}%, "
            f"Aleatoric Sensor={unc.aleatoric_sensor_noise_pct:.1f}%, Grade={unc.reliability_grade}) | "
            f"Counterfactual Drivers: {drivers} | 72h Bayesian Forecast: {fc_str}"
        )

    @tool
    def audit_explainable_alerts_and_rules_tool(note: str = "audit") -> str:
        """
        Pillar 4 (Audit & Governance): Inspect deterministic NASA-STD-3001 / OCHMO rules,
        active ExplainableAlert records (originating signals, measurement quality, scientific citations),
        and verify the Medical Autonomy Guardrail (human-in-the-loop required).
        """
        state = state_manager.get_state()
        ev = state.clinical_evaluation
        q = state.measurement_quality

        alerts_summary = (
            " | ".join(
                f"[{a.alert_id}] {a.title} (Refs: {', '.join(r['code'] for r in a.scientific_references)}; "
                f"FollowUpCase: {a.followup_case_id})"
                for a in ev.explainable_alerts
            )
            if ev.explainable_alerts
            else "No active clinical alerts; all systems within personal & NASA-STD-3001 bounds."
        )

        trace_log.append(
            ToolTraceItem(
                tool_name="audit_explainable_alerts_and_rules",
                status="OK" if ev.overall_status == "NOMINAL" else ev.overall_status,
                summary=f"{ev.overall_status}: {ev.primary_diagnosis} | Quality {q.overall_quality_pct:.0f}% ({q.reliability_grade})",
                rule_or_score=", ".join(ev.matched_rules[:2]) if ev.matched_rules else "NASA-STD-3001 Nominal",
            )
        )
        return (
            f"Overall Status: {ev.overall_status} | Primary Assessment: {ev.primary_diagnosis} | "
            f"Matched Rules: {', '.join(ev.matched_rules)} | "
            f"Measurement Quality: {q.overall_quality_pct:.1f}% ({q.reliability_grade}; {q.sensor_notes}) | "
            f"Explainable Alerts: {alerts_summary} | "
            f"Verification Steps: {'; '.join(ev.stabilization_checklist)} | "
            f"Governance Lock: {ev.autonomy_guardrail.governance_notice}"
        )

    @tool
    def manage_closed_loop_followup_tool(
        operation: str = "status",
        metric_or_action: str = "",
        measured_value: float = 0.0,
    ) -> str:
        """
        Pillar 3: Manage the Closed-Loop Clinical Follow-Up Cycle.
        operation can be:
          - 'status': list active follow-up cases, pending confirmations, executed actions, and scheduled reassessments
          - 'confirm': record a confirmation measurement (metric_or_action=metric name, measured_value=number)
          - 'action': log an executed protocol action (metric_or_action=description of action performed)
          - 'reassess': complete the pending reassessment and update case status
        """
        state = state_manager.get_state()
        cases = state.followup_cases
        if not cases:
            trace_log.append(
                ToolTraceItem(
                    tool_name="manage_closed_loop_followup",
                    status="OK",
                    summary="0 open follow-up cases; all physiological systems nominal.",
                    rule_or_score="Closed-Loop Nominal",
                )
            )
            return "No active closed-loop follow-up cases. All prior alerts resolved or nominal."

        active_case = cases[0]
        op = operation.lower().strip()

        if op == "confirm" and metric_or_action:
            updated_case = state_manager.record_followup_confirmation(
                active_case.case_id,
                RecordConfirmationRequest(
                    metric=metric_or_action,
                    measured_value=measured_value,
                    device_used="CHeCS Reference Instrument (Tempus Pro / i-STAT)",
                    signal_quality_pct=98.5,
                    notes="Confirmation measurement logged via Medical Officer Chat.",
                ),
            )
            trace_log.append(
                ToolTraceItem(
                    tool_name="manage_closed_loop_followup",
                    status="OK" if updated_case.status == "DOWNGRADED_CONFOUNDER_OR_ARTIFACT" else "WARNING",
                    summary=f"Case {updated_case.case_id}: Confirmed {metric_or_action}={measured_value} -> {updated_case.status}",
                    rule_or_score=updated_case.status,
                )
            )
            return (
                f"Closed-Loop Case {updated_case.case_id} updated: Confirmation {metric_or_action}={measured_value} recorded. "
                f"New Status: {updated_case.status}. {updated_case.resolution_notes or ''}"
            )

        if op == "action" and metric_or_action:
            updated_case = state_manager.record_followup_action(
                active_case.case_id,
                RecordActionRequest(
                    performed_by=state.crew_member,
                    protocol_reference="NASA-STD-3001 / OCHMO-TB-044",
                    action_description=metric_or_action,
                    schedule_reassessment_in_minutes=30,
                ),
            )
            trace_log.append(
                ToolTraceItem(
                    tool_name="manage_closed_loop_followup",
                    status="OK",
                    summary=f"Case {updated_case.case_id}: Action logged & reassessment scheduled in T+30m",
                    rule_or_score=updated_case.status,
                )
            )
            return (
                f"Closed-Loop Case {updated_case.case_id}: Action '{metric_or_action}' logged. "
                f"Status: {updated_case.status}. Reassessment scheduled in T+30 minutes."
            )

        if op == "reassess":
            reassess_id = (
                active_case.reassessments_scheduled[-1].reassessment_id
                if active_case.reassessments_scheduled
                else "REASSESS-MANUAL"
            )
            resolve_flag = "resolve" in metric_or_action.lower()
            updated_case = state_manager.complete_followup_reassessment(
                active_case.case_id,
                CompleteReassessmentRequest(
                    reassessment_id=reassess_id,
                    resolve_case=resolve_flag,
                    summary=metric_or_action or "Scheduled reassessment completed by crew.",
                ),
            )
            trace_log.append(
                ToolTraceItem(
                    tool_name="manage_closed_loop_followup",
                    status="OK",
                    summary=f"Case {updated_case.case_id}: Reassessment completed -> {updated_case.status}",
                    rule_or_score=updated_case.status,
                )
            )
            return f"Closed-Loop Case {updated_case.case_id} reassessment completed. Status: {updated_case.status}."

        # Default: inspect status
        pending_re = sum(1 for r in active_case.reassessments_scheduled if r.status == "PENDING")
        trace_log.append(
            ToolTraceItem(
                tool_name="manage_closed_loop_followup",
                status="OK" if active_case.status == "RESOLVED" else "WARNING",
                summary=(
                    f"Case {active_case.case_id} [{active_case.status}]: "
                    f"{len(active_case.confirmations_recorded)} confirmations, {len(active_case.actions_executed)} actions, {pending_re} pending reassessments"
                ),
                rule_or_score="OCHMO-TB-044 Closed-Loop",
            )
        )
        return (
            f"Active Case {active_case.case_id} ({active_case.title}): Status={active_case.status} | "
            f"Required Confirmations: {'; '.join(active_case.required_confirmations)} | "
            f"Recorded Confirmations: {len(active_case.confirmations_recorded)} | "
            f"Executed Actions: {len(active_case.actions_executed)} | "
            f"Pending Reassessments: {pending_re} (next at T+{active_case.reassessments_scheduled[-1].scheduled_for_offset_minutes}m)."
        )

    @tool
    def sync_spacecraft_earth_continuity_tool(operation: str = "dossier_and_queue") -> str:
        """
        Pillar 5: Compile a Store-and-Forward Telemedicine Dossier & SHA-256 EarthSyncPackage
        for MCC-Houston Flight Surgeons, or synchronize queued offline packages ('sync').
        """
        if "sync" in operation.lower() and "dossier" not in operation.lower():
            pkgs = state_manager.earth_sync.synchronize_queued_packages()
            last_pkg = pkgs[-1] if pkgs else state_manager.create_earth_sync_package()
            trace_log.append(
                ToolTraceItem(
                    tool_name="sync_spacecraft_earth_continuity",
                    status="OK",
                    summary=f"Synchronized {len(pkgs)} package(s) with MCC-Houston (Latest: {last_pkg.package_id})",
                    rule_or_score=f"SHA256 {last_pkg.sha256_integrity_hash[:10]}",
                )
            )
            return (
                f"Synchronized store-and-forward queue with MCC-Houston. Latest Package: {last_pkg.package_id} "
                f"({last_pkg.sync_status}, SHA-256={last_pkg.sha256_integrity_hash[:16]}...)."
            )

        dossier = state_manager.compile_dossier()
        trace_log.append(
            ToolTraceItem(
                tool_name="sync_spacecraft_earth_continuity",
                status="OK" if dossier.urgency == "NOMINAL" else dossier.urgency,
                summary=f"Dossier {dossier.dossier_id} & Sync Package {dossier.earth_sync_package_id} ready ({dossier.one_way_latency_seconds}s light-time delay)",
                rule_or_score="OCHMO-TB-044 Store-and-Forward",
            )
        )
        return (
            f"Compiled Telemedicine Dossier {dossier.dossier_id} (Earth Sync Package: {dossier.earth_sync_package_id}) "
            f"for {', '.join(dossier.recipient_roles)}. Mode: {dossier.transmission_mode}. "
            f"Summary: {dossier.executive_summary}"
        )

    @tool
    def check_nasa_donki_and_horizons_tool(window_days: int = 14) -> str:
        """Check NASA DONKI Space Weather (FLR, SEP, CME, GST) and NASA JPL Horizons Earth-Spacecraft distance & light-time latency."""
        state = state_manager.get_state()
        sw = state.space_weather
        hz = state.horizons_link
        sw_status = sw.alert_level if sw else "NOMINAL"

        trace_log.append(
            ToolTraceItem(
                tool_name="check_nasa_donki_and_horizons",
                status="OK" if sw_status == "NOMINAL" else sw_status,
                summary=(
                    f"DONKI: {sw.active_flare_count if sw else 0} FLR, {sw.active_sep_count if sw else 0} SEP, "
                    f"{sw.active_cme_count if sw else 0} CME | Horizons: {hz.one_way_light_time_seconds if hz else 720:.0f}s delay"
                ),
                rule_or_score=f"ALARA {sw_status} | {hz.distance_au if hz else 1.44:.2f} AU",
            )
        )
        return (
            f"NASA DONKI ({sw.source if sw else 'fallback'}): Alert={sw_status}, "
            f"FLR={sw.active_flare_count if sw else 0}, SEP={sw.active_sep_count if sw else 0}, "
            f"CME={sw.active_cme_count if sw else 0}, GST={sw.active_gst_count if sw else 0}, "
            f"Comms Risk={sw.comms_degradation_risk if sw else 'NONE'}. "
            f"NASA JPL Horizons ({hz.target_body if hz else 'Deep Space'}): Distance={hz.distance_km if hz else 0:,.0f} km "
            f"({hz.distance_au if hz else 0:.4f} AU), One-Way Light Time={hz.one_way_light_time_seconds if hz else 720:.0f}s."
        )

    @tool
    def log_nutrition_hydration_tool(meal_description: str) -> str:
        """Parse natural language food/hydration logs, update daily calorie/water/macro goals, and check NASA Na/Fe limits."""
        parsed = parse_nutrition_text(meal_description)
        if not parsed["items"]:
            parsed["items"] = ["Space Ration Pack (200 kcal)"]
            parsed["calories_kcal"] = 200.0
            parsed["carbs_g"] = 32.0
            parsed["water_ml"] = 250.0

        state = state_manager.add_nutrition_entry(
            item_label=", ".join(parsed["items"]),
            calories=parsed["calories_kcal"],
            water_ml=parsed["water_ml"],
            protein_g=parsed["protein_g"],
            carbs_g=parsed["carbs_g"],
            fiber_g=parsed["fiber_g"],
            sodium_mg=parsed["sodium_mg"],
            iron_mg=parsed["iron_mg"],
        )
        n = state.nutrition
        trace_log.append(
            ToolTraceItem(
                tool_name="log_nutrition_hydration",
                status="OK" if n.sodium_mg <= n.max_sodium_mg and n.iron_mg <= n.max_iron_mg else "WARNING",
                summary=f"+{parsed['calories_kcal']:.0f} kcal, +{parsed['water_ml']:.0f} ml H2O logged",
                rule_or_score=f"Na {n.sodium_mg:.0f}/{n.max_sodium_mg:.0f}mg | Fe {n.iron_mg:.1f}/{n.max_iron_mg:.0f}mg",
            )
        )
        return (
            f"Logged: {', '.join(parsed['items'])}. Daily totals: {n.calories_kcal:.0f}/{n.goal_calories_kcal:.0f} kcal, "
            f"{n.water_ml:.0f}/{n.goal_water_ml:.0f} ml H2O, Sodium {n.sodium_mg:.0f}/{n.max_sodium_mg:.0f} mg, "
            f"Iron {n.iron_mg:.1f}/{n.max_iron_mg:.1f} mg. Blood Glucose now {state.vitals.glucose_mg_dl:.0f} mg/dL."
        )

    @tool
    def log_sleep_mood_context_tool(checkin_text: str) -> str:
        """Update sleep hours, mood score, stress, EVA shoulder pain, post-exercise timing, or cabin CO2 from natural language."""
        updates = parse_sleep_mood_context_text(checkin_text)
        if any(k in updates for k in ("sleep_hours", "mood_score", "shoulder_pain_score", "stress_index")):
            state_manager.update_sleep_mood(
                sleep_hours=updates.get("sleep_hours"),
                mood_score=updates.get("mood_score"),
                shoulder_pain_score=updates.get("shoulder_pain_score"),
                stress_index=updates.get("stress_index"),
            )
        if any(k in updates for k in ("minutes_since_last_exercise", "exercise_modality", "cabin_co2_mmhg")):
            state_manager.update_context(
                ContextUpdateRequest(
                    minutes_since_last_exercise=updates.get("minutes_since_last_exercise"),
                    exercise_modality=updates.get("exercise_modality"),
                    cabin_co2_mmhg=updates.get("cabin_co2_mmhg"),
                )
            )

        state = state_manager.get_state()
        v = state.vitals
        mc = state.mission_context
        trace_log.append(
            ToolTraceItem(
                tool_name="log_sleep_mood_context",
                status="OK" if state.clinical_evaluation.overall_status == "NOMINAL" else state.clinical_evaluation.overall_status,
                summary=(
                    f"Sleep {v.sleep_hours:.1f}h | Mood {v.mood_score}/5 | Shoulder {v.shoulder_pain_score}/10 | "
                    f"Ex T+{mc.minutes_since_last_exercise:.0f}m | CO2 {mc.cabin_co2_mmhg:.1f}mmHg"
                ),
                rule_or_score="OCHMO-MTB-009 / MTB-006 / Context",
            )
        )
        return (
            f"Updated check-in & context: Sleep {v.sleep_hours:.1f}h (REM {v.rem_sleep_pct:.0f}%), "
            f"Mood {v.mood_score}/5, Stress {v.stress_index:.0f}%, Shoulder VAS {v.shoulder_pain_score}/10, "
            f"Exercise: {mc.exercise_modality} ({mc.minutes_since_last_exercise:.0f}m ago), Cabin ppCO2: {mc.cabin_co2_mmhg:.1f} mmHg."
        )

    @tool
    def trigger_psychological_biofeedback_tool(reason: str = "biometric_and_behavioral_trigger") -> str:
        """
        Pillar 6: Psychological & Autonomic Biofeedback Countermeasure Tool.
        Uses the astronaut's personal baseline deviations (HR, BP, HRV, Sleep, REM, Mood, Stress, Isolation Latency)
        with weighted diagnostic scoring to automatically dispatch personalized stimuli from the astronaut's Crew Vault
        (family/friends video & audio, Earth nature/animal soundscapes, interactive games/interests + calming music),
        applies closed-loop vagal biofeedback normalization (HR, BP, HRV, Mood), schedules a T+15m reassessment,
        and sends an immediate alert + SHA-256 telemetry bundle to Central (MCC-Houston BHP & Flight Surgeon).
        """
        alert_rec = state_manager.trigger_psychological_biofeedback(reason=reason)
        stim_str = "; ".join(
            f"[{s.category}] {s.title} ({s.duration_min} min — {s.target_effect})"
            for s in alert_rec.dispatched_stimuli
        )
        weights_str = ", ".join(
            f"{w.label}: {w.current_value} (personal base {w.personal_baseline}, z={w.individual_z_score:+.1f}σ -> +{w.points_contributed:.1f} pts)"
            for w in alert_rec.triggering_indicator_weights[:4]
        )
        pre = alert_rec.pre_stimulus_vitals
        post = alert_rec.post_stimulus_vitals

        trace_log.append(
            ToolTraceItem(
                tool_name="trigger_psychological_biofeedback",
                status="WARNING" if alert_rec.weighted_score_0_100 >= 55.0 else "OK",
                summary=(
                    f"Central Alert {alert_rec.central_alert_id}: {alert_rec.primary_psych_label} "
                    f"({alert_rec.weighted_score_0_100:.1f}/100) -> Dispatched {len(alert_rec.dispatched_stimuli)} stimulus item(s) | "
                    f"HR {pre['heart_rate_bpm']:.0f}->{post['heart_rate_bpm']:.0f} bpm, "
                    f"BP {pre['bp_systolic']:.0f}->{post['bp_systolic']:.0f} mmHg, "
                    f"HRV {pre['hrv_ms']:.0f}->{post['hrv_ms']:.0f} ms"
                ),
                rule_or_score=f"MCC-BHP Alert + Sync {alert_rec.earth_sync_package_id}",
            )
        )
        return (
            f"Central BHP Alert Dispatched: {alert_rec.central_alert_id} (Earth Sync Package: {alert_rec.earth_sync_package_id}) | "
            f"Astronaut: {alert_rec.astronaut_name} | Window: {alert_rec.schedule_window} | "
            f"Weighted Diagnosis: {alert_rec.primary_psych_label} (Score: {alert_rec.weighted_score_0_100:.1f}/100) | "
            f"Triggering Personal Baseline Weights: {weights_str} | "
            f"Activated Crew Vault Stimuli: {stim_str} | "
            f"Closed-Loop Biofeedback Shift: HR {pre['heart_rate_bpm']:.0f}->{post['heart_rate_bpm']:.0f} bpm, "
            f"BP {pre['bp_systolic']:.0f}/{pre['bp_diastolic']:.0f}->{post['bp_systolic']:.0f}/{post['bp_diastolic']:.0f} mmHg, "
            f"HRV {pre['hrv_ms']:.0f}->{post['hrv_ms']:.0f} ms, Stress {pre['stress_index']:.0f}%->{post['stress_index']:.0f}%, "
            f"Mood {pre['mood_score']:.0f}-> {post['mood_score']:.0f}/5 | "
            f"Scheduled Reassessment: T+{alert_rec.reassessment_scheduled_in_minutes} min."
        )

    return [
        inspect_adaptive_baseline_tool,
        evaluate_contextual_intelligence_tool,
        predict_calibrated_ml_and_uncertainty_tool,
        audit_explainable_alerts_and_rules_tool,
        manage_closed_loop_followup_tool,
        sync_spacecraft_earth_continuity_tool,
        check_nasa_donki_and_horizons_tool,
        log_nutrition_hydration_tool,
        log_sleep_mood_context_tool,
        trigger_psychological_biofeedback_tool,
    ]
