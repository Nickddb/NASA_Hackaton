from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import numpy as np

from app.engine.clinical_rules import evaluate_clinical_and_explainable_rules, load_scenarios_catalog
from app.engine.cross_diagnosis import SEVERE_PSYCH, evaluate_cross_diagnosis
from app.engine.earth_sync import FOLLOWUP_STORE_PATH, EarthSyncManager
from app.engine.followup_loop import FollowUpCaseManager
from app.engine.telemetry_generator import CRISIS_PROFILES, TelemetryGenerator
from app.engine.nasa_feeds import (
    fetch_nasa_space_weather,
    load_sample_donki,
    load_sample_horizons,
)
from app.ml.adaptive_baseline import AdaptiveBaselineEngine
from app.ml.contextual_intelligence import ContextualIntelligenceEngine
from app.ml.predictor import AstraCareRealMLEngine
from app.ml.psych_biofeedback import PsychBiofeedbackEngine
from app.models.schemas import (
    CentralPsychAlertRecord,
    ClinicalFollowUpCase,
    CompleteReassessmentRequest,
    ContextUpdateRequest,
    EarthSyncPackage,
    EscalateCaseRequest,
    HorizonsLinkStatus,
    LoggedFoodItem,
    MeasurementQualityProfile,
    MeasurementResponse,
    MissionContext,
    MissionState,
    NutritionHydrationState,
    PsychBiofeedbackEvaluation,
    RecordActionRequest,
    RecordConfirmationRequest,
    SpaceWeatherSummary,
    TelemedicineDossier,
    VitalSigns,
)


class MissionStateManager:
    """
    Central orchestrator for AstraCare AI's 6 ML, Psychophysiological & Clinical Continuity Pillars:
      1. Adaptive Individual Baseline (EWMA + MAD + Ledoit-Wolf Mahalanobis + OSDR Phase Priors)
      2. Contextual Mission Intelligence (Sleep, Exercise, EVA, Gravity Phase, Cabin CO2/O2)
      3. Closed-Loop Follow-Up Cycle (Confirmation Measurements -> Actions -> Scheduled Reassessments)
      4. Explainable & Auditable Real ML (Calibrated HGB+RF Ensemble, Epistemic/Aleatoric Uncertainty, 72h Forecast)
      5. Spacecraft-Earth Store-and-Forward Continuity (SHA-256 Offline Ledger & MCC Sync Bundles)
      6. Individual-Weighted Psychophysiological Biofeedback Countermeasure & Central BHP Alert Dispatch
    """

    def __init__(self) -> None:
        self.catalog: dict[str, Any] = load_scenarios_catalog()
        self.baseline_engine = AdaptiveBaselineEngine(ewma_alpha=0.25)
        self.context_engine = ContextualIntelligenceEngine()
        self.ml_predictor = AstraCareRealMLEngine()
        self.psych_engine = PsychBiofeedbackEngine()
        self.followup_manager = FollowUpCaseManager(store_path=FOLLOWUP_STORE_PATH)
        self.earth_sync = EarthSyncManager()

        self.astronauts_by_id: dict[str, dict[str, Any]] = {
            a["astronaut_id"]: a for a in self.catalog.get("astronaut_profiles", [])
        }
        self.scenarios_by_id: dict[str, dict[str, Any]] = {
            s["id"]: s for s in self.catalog.get("scenarios", [])
        }
        self.environments_by_id: dict[str, dict[str, Any]] = {
            e["id"]: e for e in self.catalog.get("environments", [])
        }

        self.astronaut_id: str = "elena_vance"
        self.scenario_id: str = "nominal"
        self.environment_id: str = "transit"
        self.mission_day: int = 142
        self.mission_context: MissionContext = MissionContext(
            **self.scenarios_by_id["nominal"].get("mission_context", {})
        )
        self.measurement_quality: MeasurementQualityProfile = MeasurementQualityProfile(
            **self.scenarios_by_id["nominal"].get("measurement_quality", {})
        )
        self.nutrition: NutritionHydrationState = NutritionHydrationState(
            **self.scenarios_by_id["nominal"]["nutrition"]
        )
        self.telemetry_rng = np.random.default_rng()
        self.vitals: VitalSigns
        self.longitudinal_series: list[dict[str, Any]] = []
        self._generate_telemetry()
        self.space_weather: SpaceWeatherSummary = load_sample_donki(simulated=self._scenario_donki())
        self.horizons_link: HorizonsLinkStatus = load_sample_horizons(self.environment_id)
        self.last_updated: str = datetime.now(timezone.utc).isoformat()

    # ---------- Stochastic telemetry (replaces static scenario vitals) ----------
    def record_reported_symptom(self, text: str) -> None:
        """Keep crew-reported symptoms (from chat) so the cross-diagnosis tree and the dashboard see them."""
        text = text.strip()
        if text and text not in self.vitals.reported_symptoms:
            self.vitals.reported_symptoms = (self.vitals.reported_symptoms + [text])[-8:]
            self.earth_sync.record_audit_event(
                event_type="CREW_SYMPTOM_REPORTED", astronaut_id=self.astronaut_id, summary=f"Crew report: {text[:160]}"
            )
            self._touch()

    def escalate_psych_priority(self, reason: str) -> EarthSyncPackage:
        """Immediate Earth alert for severe psychological risk: audit entry + a store-and-forward package
        that goes first in the next communication window."""
        self.earth_sync.record_audit_event(
            event_type="PSYCH_CRITICAL_ESCALATION",
            astronaut_id=self.astronaut_id,
            summary=f"IMMEDIATE behavioral-health alert to Earth Flight Surgeon: {reason}",
            metadata={"priority": "IMMEDIATE"},
        )
        pkg = self.create_earth_sync_package()
        if self.horizons_link.comms_available:
            self.earth_sync.synchronize_queued_packages(comms_available=True)
        return pkg

    def _scenario_donki(self) -> dict[str, list[dict[str, Any]]]:
        """Scenario-only DONKI events (e.g. the solar-storm drill), stamped relative to now so they are active.
        Kept separate from real NASA data and labelled origin='scenario_simulation' downstream."""
        sim = self.scenarios_by_id.get(self.scenario_id, {}).get("donki_simulation") or {}
        now = datetime.now(timezone.utc)
        out: dict[str, list[dict[str, Any]]] = {}
        for kind, items in sim.items():
            if kind.startswith("_"):
                continue
            stamped = []
            for item in items:
                t = (now - timedelta(hours=float(item.get("hours_ago", 1)))).strftime("%Y-%m-%dT%H:%MZ")
                rec = {k: v for k, v in item.items() if k != "hours_ago"}
                rec["beginTime" if kind == "FLR" else "eventTime"] = t
                stamped.append(rec)
            out[kind] = stamped
        return out

    def _generator(self) -> TelemetryGenerator:
        return TelemetryGenerator(self.astronauts_by_id[self.astronaut_id], self.mission_context.mission_phase)

    def _generate_telemetry(self) -> None:
        sc = self.scenarios_by_id[self.scenario_id]
        vitals, series = self._generator().generate(sc.get("crisis_profile", self.scenario_id), self.mission_day)
        vitals["reported_symptoms"] = list(sc.get("reported_symptoms", []))
        self.vitals = VitalSigns(**vitals)
        self.longitudinal_series = series

    def next_telemetry_reading(self, crisis_probability: float = 0.0) -> MissionState:
        """New noisy reading from the generator. With crisis_probability > 0 a nominal mission can
        stochastically enter one of the crisis profiles (demo of unplanned events)."""
        if self.scenario_id == "nominal" and crisis_probability > 0 and self.telemetry_rng.random() < crisis_probability:
            crises = [k for k in CRISIS_PROFILES if k != "nominal" and k in self.scenarios_by_id]
            return self.switch_scenario(str(self.telemetry_rng.choice(crises)))

        sc = self.scenarios_by_id[self.scenario_id]
        reading = self._generator().next_reading(
            sc.get("crisis_profile", self.scenario_id), self.vitals.model_dump(), self.telemetry_rng
        )
        self.vitals = VitalSigns(**reading)
        today = self.longitudinal_series[-1] if self.longitudinal_series else None
        if today is not None:
            for metric, key in (("heart_rate_bpm", "hr"), ("hrv_ms", "hrv"), ("temperature_c", "temp"),
                                ("bp_systolic", "bp_sys"), ("bp_diastolic", "bp_dia"), ("radiation_msv_h", "radiation"),
                                ("glucose_mg_dl", "glucose"), ("spo2_pct", "spo2"), ("respiration_rpm", "rr")):
                today[key] = reading[metric]
        self._touch()
        return self.get_state()

    def _touch(self) -> None:
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def switch_astronaut(self, astronaut_id: str) -> MissionState:
        if astronaut_id not in self.astronauts_by_id:
            raise KeyError(f"Unknown astronaut_id: {astronaut_id}")
        self.astronaut_id = astronaut_id
        self._generate_telemetry()  # vitals are drawn around this astronaut's own baseline
        self.earth_sync.record_audit_event(
            event_type="ASTRONAUT_PROFILE_SWITCHED",
            astronaut_id=astronaut_id,
            summary=f"Switched active personal baseline profile to {self.astronauts_by_id[astronaut_id]['name']}.",
        )
        self._touch()
        return self.get_state()

    def switch_scenario(self, scenario_id: str) -> MissionState:
        if scenario_id not in self.scenarios_by_id:
            raise KeyError(f"Unknown scenario_id: {scenario_id}")
        sc = self.scenarios_by_id[scenario_id]
        self.scenario_id = scenario_id
        self.mission_day = int(sc.get("mission_day", 142))
        self.mission_context = MissionContext(**sc.get("mission_context", {}))
        self.measurement_quality = MeasurementQualityProfile(**sc.get("measurement_quality", {}))
        self.nutrition = NutritionHydrationState(**sc["nutrition"])
        self._generate_telemetry()
        self.space_weather = load_sample_donki(simulated=self._scenario_donki())
        self.earth_sync.record_audit_event(
            event_type="SCENARIO_LOADED",
            astronaut_id=self.astronaut_id,
            summary=f"Loaded scenario '{sc['name']}' (Day {self.mission_day}).",
            metadata={"scenario_id": scenario_id},
        )
        self._touch()
        return self.get_state()

    def switch_environment(self, env_id: str) -> MissionState:
        if env_id not in self.environments_by_id:
            raise KeyError(f"Unknown environment_id: {env_id}")
        self.environment_id = env_id
        env_info = self.environments_by_id[env_id]
        self.mission_context.gravitational_g = float(env_info.get("gravitational_g", 0.0))
        if "mission_phase" in env_info:
            self.mission_context.mission_phase = env_info["mission_phase"]
        self.horizons_link = load_sample_horizons(env_id)
        self._generate_telemetry()  # gravity phase shifts the nominal centre
        self.earth_sync.record_audit_event(
            event_type="ENVIRONMENT_CALIBRATION_CHANGED",
            astronaut_id=self.astronaut_id,
            summary=f"Updated mission environment to {env_info['name']} ({self.mission_context.gravitational_g:.2f}g).",
            metadata={"environment_id": env_id},
        )
        self._touch()
        return self.get_state()

    def update_context(self, req: ContextUpdateRequest) -> MissionState:
        if req.exercise_minutes_24h is not None:
            self.mission_context.exercise_minutes_24h = req.exercise_minutes_24h
        if req.exercise_modality is not None:
            self.mission_context.exercise_modality = req.exercise_modality
        if req.minutes_since_last_exercise is not None:
            self.mission_context.minutes_since_last_exercise = req.minutes_since_last_exercise
        if req.eva_status is not None:
            self.mission_context.eva_status = req.eva_status
        if req.hours_since_last_eva is not None:
            self.mission_context.hours_since_last_eva = req.hours_since_last_eva
        if req.cabin_co2_mmhg is not None:
            self.mission_context.cabin_co2_mmhg = req.cabin_co2_mmhg
        if req.cabin_o2_pct is not None:
            self.mission_context.cabin_o2_pct = req.cabin_o2_pct
        if req.cabin_temp_c is not None:
            self.mission_context.cabin_temp_c = req.cabin_temp_c
        if req.signal_quality_pct is not None:
            self.measurement_quality.overall_quality_pct = req.signal_quality_pct
            self.measurement_quality.wearable_ppg_quality_pct = req.signal_quality_pct
        if req.motion_artifact_detected is not None:
            self.measurement_quality.motion_artifact_detected = req.motion_artifact_detected
        if req.nibp_cuff_verified is not None:
            self.measurement_quality.nibp_cuff_verified = req.nibp_cuff_verified

        self.earth_sync.record_audit_event(
            event_type="CONTEXT_COVARIATES_UPDATED",
            astronaut_id=self.astronaut_id,
            summary="Updated operational/environmental context covariates.",
            metadata=req.model_dump(exclude_none=True),
        )
        self._touch()
        return self.get_state()

    def trigger_measurement(self, system_id: str) -> MeasurementResponse:
        state_before = self.get_state()
        if system_id not in state_before.clinical_evaluation.systems:
            raise KeyError(f"Unknown system_id: {system_id}")

        # Active confirmation measurement improves sensor quality & NIBP verification
        self.measurement_quality.overall_quality_pct = min(99.0, max(94.0, self.measurement_quality.overall_quality_pct + 4.0))
        self.measurement_quality.motion_artifact_detected = False

        if system_id == "cardiovascular":
            self.measurement_quality.nibp_cuff_verified = True
            reading = (
                f"Anchored NIBP + Astroskin ECG Sync: {self.vitals.heart_rate_bpm:.0f} bpm, "
                f"HRV {self.vitals.hrv_ms:.0f} ms, BP {self.vitals.bp_systolic:.0f}/{self.vitals.bp_diastolic:.0f} mmHg "
                f"(SNR {self.measurement_quality.overall_quality_pct:.0f}%)"
            )
        elif system_id == "nervous_sleep":
            reading = (
                f"EEG/Actigraphy + Tonometry: Sleep {self.vitals.sleep_hours:.1f}h (REM {self.vitals.rem_sleep_pct:.0f}%), "
                f"Mood {self.vitals.mood_score}/5, IOP {self.vitals.intraocular_pressure_mmhg:.1f} mmHg"
            )
        elif system_id == "respiratory":
            self.measurement_quality.ambient_temp_compensated = True
            reading = (
                f"Tempus Pro Capnography/IR: SpO2 {self.vitals.spo2_pct:.1f}%, RR {self.vitals.respiration_rpm:.0f} rpm, "
                f"Core Temp {self.vitals.temperature_c:.1f} C, Cabin CO2 {self.mission_context.cabin_co2_mmhg:.1f} mmHg"
            )
        elif system_id == "metabolic":
            self.measurement_quality.cgm_calibration_age_hours = 0.5
            reading = (
                f"i-STAT / Shielded Capillary Check: Glucose {self.vitals.glucose_mg_dl:.0f} mg/dL | "
                f"Intake {self.nutrition.calories_kcal:.0f}/{self.nutrition.goal_calories_kcal:.0f} kcal, {self.nutrition.water_ml:.0f} ml H2O"
            )
        elif system_id == "musculoskeletal":
            reading = (
                f"Ultrasound 2 & Urolux Scan: Shoulder VAS {self.vitals.shoulder_pain_score}/10, "
                f"Urinary Ca {self.vitals.urinary_calcium_mg_d:.0f} mg/day"
            )
        else:
            reading = (
                f"BLE Dosimeter Sync: {self.vitals.radiation_msv_h:.2f} mSv/h instantaneous | "
                f"{self.vitals.cumulative_radiation_msv:.1f} mSv cumulative"
            )

        self._touch()
        updated_state = self.get_state()
        sys_eval = updated_state.clinical_evaluation.systems[system_id]

        self.earth_sync.record_audit_event(
            event_type="ACTIVE_MEASUREMENT_TRIGGERED",
            astronaut_id=self.astronaut_id,
            summary=f"[{sys_eval.name}] {reading}",
            metadata={"system_id": system_id, "status": sys_eval.status},
        )

        return MeasurementResponse(
            system_id=system_id,
            system_name=sys_eval.name,
            device_used=sys_eval.checs_device,
            decontamination_required=updated_state.clinical_evaluation.decontamination_required,
            decontamination_checklist=updated_state.clinical_evaluation.decontamination_checklist,
            reading_summary=reading,
            status=sys_eval.status,
            guidance=sys_eval.recommended_action,
            state=updated_state,
        )

    def add_nutrition_entry(
        self,
        item_label: str,
        calories: float,
        water_ml: float,
        protein_g: float,
        carbs_g: float,
        fiber_g: float,
        sodium_mg: float,
        iron_mg: float,
    ) -> MissionState:
        self.nutrition.calories_kcal = round(self.nutrition.calories_kcal + calories, 1)
        self.nutrition.water_ml = round(self.nutrition.water_ml + water_ml, 1)
        self.nutrition.protein_g = round(self.nutrition.protein_g + protein_g, 1)
        self.nutrition.carbs_g = round(self.nutrition.carbs_g + carbs_g, 1)
        self.nutrition.fiber_g = round(self.nutrition.fiber_g + fiber_g, 1)
        self.nutrition.sodium_mg = round(self.nutrition.sodium_mg + sodium_mg, 1)
        self.nutrition.iron_mg = round(self.nutrition.iron_mg + iron_mg, 2)

        self.nutrition.logged_items.insert(
            0,
            LoggedFoodItem(
                timestamp=datetime.now(timezone.utc).strftime("%H:%M UTC"),
                item=item_label,
                calories_kcal=calories,
                water_ml=water_ml,
                protein_g=protein_g,
                carbs_g=carbs_g,
                fiber_g=fiber_g,
                sodium_mg=sodium_mg,
                iron_mg=iron_mg,
            ),
        )
        self.nutrition.logged_items = self.nutrition.logged_items[:12]

        if carbs_g > 0 and self.vitals.glucose_mg_dl < 85:
            self.vitals.glucose_mg_dl = round(min(104.0, self.vitals.glucose_mg_dl + carbs_g * 0.65), 1)
        if water_ml >= 300 and self.vitals.bp_systolic < 96 and self.scenario_id == "orthostatic_intolerance":
            self.vitals.bp_systolic = round(min(108.0, self.vitals.bp_systolic + 8.0), 1)
            self.vitals.bp_diastolic = round(min(70.0, self.vitals.bp_diastolic + 5.0), 1)
            self.vitals.heart_rate_bpm = round(max(82.0, self.vitals.heart_rate_bpm - 10.0), 1)

        if self.longitudinal_series:
            self.longitudinal_series[-1]["glucose"] = round(self.vitals.glucose_mg_dl, 1)
            self.longitudinal_series[-1]["hr"] = round(self.vitals.heart_rate_bpm, 1)

        self.earth_sync.record_audit_event(
            event_type="NUTRITION_HYDRATION_LOGGED",
            astronaut_id=self.astronaut_id,
            summary=f"Logged {item_label} (+{calories:.0f} kcal, +{water_ml:.0f} ml H2O).",
        )
        self._touch()
        return self.get_state()

    def update_sleep_mood(
        self,
        sleep_hours: float | None = None,
        mood_score: int | None = None,
        shoulder_pain_score: int | None = None,
        stress_index: float | None = None,
    ) -> MissionState:
        if sleep_hours is not None:
            self.vitals.sleep_hours = round(max(1.0, min(12.0, sleep_hours)), 1)
            if sleep_hours < 5.0:
                self.vitals.sleep_streak_low_days = max(self.vitals.sleep_streak_low_days + 1, 1)
                self.vitals.rem_sleep_pct = max(10.0, round(self.vitals.rem_sleep_pct - 4.0, 1))
                self.vitals.hrv_ms = max(18.0, round(self.vitals.hrv_ms - 8.0, 1))
            elif sleep_hours >= 7.0:
                self.vitals.sleep_streak_low_days = 0
                self.vitals.rem_sleep_pct = min(24.0, round(self.vitals.rem_sleep_pct + 3.0, 1))
                self.vitals.hrv_ms = min(65.0, round(self.vitals.hrv_ms + 8.0, 1))
        if mood_score is not None:
            self.vitals.mood_score = max(1, min(5, mood_score))
        if stress_index is not None:
            self.vitals.stress_index = round(max(5.0, min(99.0, stress_index)), 1)
        elif mood_score is not None:
            self.vitals.stress_index = round(max(15.0, min(92.0, (6 - mood_score) * 18.0)), 1)
        if shoulder_pain_score is not None:
            self.vitals.shoulder_pain_score = max(0, min(10, shoulder_pain_score))

        if self.longitudinal_series:
            self.longitudinal_series[-1]["sleep"] = self.vitals.sleep_hours
            self.longitudinal_series[-1]["rem"] = self.vitals.rem_sleep_pct
            self.longitudinal_series[-1]["mood"] = self.vitals.mood_score
            self.longitudinal_series[-1]["hrv"] = self.vitals.hrv_ms

        self.earth_sync.record_audit_event(
            event_type="SLEEP_MOOD_CHECKIN_UPDATED",
            astronaut_id=self.astronaut_id,
            summary=f"Sleep={self.vitals.sleep_hours:.1f}h, Mood={self.vitals.mood_score}/5, Shoulder VAS={self.vitals.shoulder_pain_score}/10.",
        )
        self._touch()
        return self.get_state()

    def record_followup_confirmation(
        self, case_id: str, req: RecordConfirmationRequest
    ) -> ClinicalFollowUpCase:
        # Update live vitals if metric exists on VitalSigns
        if hasattr(self.vitals, req.metric):
            setattr(self.vitals, req.metric, req.measured_value)
        self.measurement_quality.overall_quality_pct = max(
            self.measurement_quality.overall_quality_pct, req.signal_quality_pct
        )
        self.measurement_quality.motion_artifact_detected = False
        if req.metric in ("bp_systolic", "bp_diastolic"):
            self.measurement_quality.nibp_cuff_verified = True

        astro_profile = self.astronauts_by_id[self.astronaut_id]
        adaptive_base = self.baseline_engine.evaluate(
            astro_profile, self.vitals, self.mission_context, self.longitudinal_series, self.mission_day
        )
        case = self.followup_manager.record_confirmation(case_id, req, adaptive_base)
        self.earth_sync.record_audit_event(
            event_type="FOLLOWUP_CONFIRMATION_RECORDED",
            astronaut_id=self.astronaut_id,
            summary=(
                f"Case {case_id}: Recorded confirmation {req.metric}={req.measured_value} via {req.device_used} "
                f"(status -> {case.status})."
            ),
            metadata={"case_id": case_id, "confirms_anomaly": case.confirmations_recorded[-1].confirms_anomaly},
        )
        self._touch()
        return case

    def record_followup_action(self, case_id: str, req: RecordActionRequest) -> ClinicalFollowUpCase:
        case = self.followup_manager.record_action(case_id, req)
        self.earth_sync.record_audit_event(
            event_type="FOLLOWUP_ACTION_EXECUTED",
            astronaut_id=self.astronaut_id,
            summary=f"Case {case_id}: Executed '{req.action_description}' by {req.performed_by}; reassessment in T+{req.schedule_reassessment_in_minutes}m.",
            metadata={"case_id": case_id, "protocol": req.protocol_reference},
        )
        self._touch()
        return case

    def complete_followup_reassessment(
        self, case_id: str, req: CompleteReassessmentRequest
    ) -> ClinicalFollowUpCase:
        case = self.followup_manager.complete_reassessment(case_id, req)
        self.earth_sync.record_audit_event(
            event_type="FOLLOWUP_REASSESSMENT_COMPLETED",
            astronaut_id=self.astronaut_id,
            summary=f"Case {case_id}: Reassessment {req.reassessment_id} completed (status -> {case.status}).",
            metadata={"case_id": case_id, "resolved": req.resolve_case},
        )
        self._touch()
        return case

    def escalate_followup_case(self, case_id: str, req: EscalateCaseRequest) -> ClinicalFollowUpCase:
        case = self.followup_manager.escalate(case_id, req)
        self.earth_sync.record_audit_event(
            event_type="FOLLOWUP_ESCALATED_TO_EARTH",
            astronaut_id=self.astronaut_id,
            summary=f"Case {case_id} escalated to Earth Flight Surgeon by {req.requested_by}: {req.reason}",
            metadata={"case_id": case_id},
        )
        self._touch()
        return case

    def synchronize_with_earth(self) -> list[EarthSyncPackage]:
        """Flush queued packages only when the current link window allows it."""
        return self.earth_sync.synchronize_queued_packages(
            comms_available=self.horizons_link.comms_available
        )

    async def refresh_space_weather(self, force: bool = False) -> SpaceWeatherSummary:
        self.space_weather = await fetch_nasa_space_weather(simulated=self._scenario_donki(), force=force)
        self._touch()
        return self.space_weather

    def create_earth_sync_package(self) -> EarthSyncPackage:
        state = self.get_state()
        return self.earth_sync.build_and_queue_package(
            astronaut_id=self.astronaut_id,
            crew_member=state.crew_member,
            mission_day=state.mission_day,
            environment_id=state.environment_id,
            horizons_link=state.horizons_link or load_sample_horizons(state.environment_id),
            space_weather_alert=state.space_weather.alert_level if state.space_weather else "NOMINAL",
            adaptive_baseline=state.adaptive_baseline,
            contextual_report=state.contextual_intelligence,
            ml_prediction=state.ml_prediction,
            explainable_alerts=state.explainable_alerts,
            followup_cases=state.followup_cases,
            longitudinal_series=state.longitudinal_series,
            forecast_72h=state.ml_prediction.forecast_72h,
            auto_sync_if_low_latency=(state.one_way_latency_seconds <= 10),
        )

    def compile_dossier(self) -> TelemedicineDossier:
        pkg = self.create_earth_sync_package()
        state = self.get_state()
        env = self.environments_by_id[self.environment_id]
        latency = int(env.get("one_way_latency_seconds", 720))
        tx_mode = (
            "Asynchronous Store-and-Forward Telemetry + Audit Bundle (Deep Space Delay)"
            if latency > 30
            else "Real-Time Synchronous Telemetry + PMC Loop (ISS/Gateway)"
        )

        roles = [
            "Flight Surgeon (FS — Primary Aerospace Medical Authority)",
            "Crew Surgeon (CS — In-Flight Medical Operations)",
            "Biomedical Engineer (BME — CHeCS Hardware & Telemetry)",
        ]
        if state.clinical_evaluation.systems["nervous_sleep"].status != "NOMINAL":
            roles.append("Behavioral Health & Performance Specialist (BHP — OCHMO-MTB-009)")
        if state.clinical_evaluation.systems["radiation"].status != "NOMINAL":
            roles.append("Radiation Health Officer (RHO — ALARA & DONKI SPE)")

        top_drivers = ", ".join(
            f"{f.label}: {f.current_value} (personal z={f.individual_z_score:+.1f}σ, {f.importance:.0f}%)"
            for f in state.ml_prediction.feature_importances[:3]
        )
        sw_note = (
            state.space_weather.alara_instruction
            if state.space_weather
            else "NASA DONKI solar weather feed pending sync; personal BLE dosimeter active."
        )

        questions = [
            "Review closed-loop confirmation measurements and authorize next-stage CHeCS protocol adjustment.",
            "Confirm return-to-EVA / operational schedule vs. continued medical watch per OCHMO-TB-044 MORD.",
        ]
        if state.contextual_intelligence.plausible_non_pathological_confounders:
            questions.append(
                f"Evaluate contextual confounder hypothesis: {state.contextual_intelligence.plausible_non_pathological_confounders[0]}."
            )

        return TelemedicineDossier(
            dossier_id=f"ASTRA-MORD-{uuid4().hex[:6].upper()}",
            generated_at=datetime.now(timezone.utc).isoformat(),
            mission_day=state.mission_day,
            crew_member=state.crew_member,
            environment_id=state.environment_id,
            environment_name=state.environment_name,
            one_way_latency_seconds=latency,
            transmission_mode=tx_mode,
            urgency=state.clinical_evaluation.overall_status,
            recipient_roles=roles,
            executive_summary=(
                f"Status: {state.clinical_evaluation.overall_status} | "
                f"Assessment: {state.clinical_evaluation.primary_diagnosis}. "
                f"Personal Adaptive Drift: {state.adaptive_baseline.personal_drift_score:.1f}% "
                f"(Mahalanobis {state.adaptive_baseline.multivariate_mahalanobis_distance:.2f}) | "
                f"Context-Adjusted ML Anomaly Score: {state.ml_prediction.anomaly_score:.1f}% "
                f"({state.ml_prediction.predicted_syndrome_label}, {state.ml_prediction.confidence_pct:.1f}% ± "
                f"{state.ml_prediction.uncertainty.total_uncertainty_pct:.1f}% uncertainty). "
                f"Top Drivers: {top_drivers}. "
                f"Earth Sync Package: {pkg.package_id} (SHA-256: {pkg.sha256_integrity_hash[:12]}...)."
            ),
            clinical_evaluation=state.clinical_evaluation,
            ml_prediction=state.ml_prediction,
            adaptive_baseline=state.adaptive_baseline,
            contextual_intelligence=state.contextual_intelligence,
            active_followup_cases=state.followup_cases,
            earth_sync_package_id=pkg.package_id,
            vitals_snapshot=state.vitals,
            nutrition_snapshot=state.nutrition,
            space_weather_alert=sw_note,
            recommended_earth_questions=questions,
        )

    def trigger_psychological_biofeedback(
        self, reason: str = "Automated biometric threshold or crew wellness intervention"
    ) -> CentralPsychAlertRecord:
        """
        Pillar 6: Triggers the Personalized Psychophysiological Biofeedback Countermeasure:
          - Evaluates individual-baseline-weighted psychological scores & selects Personal Crew Vault media
          - Applies closed-loop vagal & affective normalization toward the astronaut's personal baseline
          - Logs the intervention in the Closed-Loop Follow-Up Case with a T+15 min reassessment
          - Dispatches a mandatory alert + SHA-256 EarthSyncPackage to Central (MCC-Houston BHP & Flight Surgeon)
        """
        state_before = self.get_state()
        psych_eval = state_before.psych_biofeedback
        if psych_eval is None:
            astro_profile = self.astronauts_by_id[self.astronaut_id]
            psych_eval = self.psych_engine.evaluate(
                astronaut_profile=astro_profile,
                vitals=self.vitals,
                nutrition=self.nutrition,
                context=self.mission_context,
                adaptive_baseline=state_before.adaptive_baseline,
                one_way_latency_seconds=state_before.one_way_latency_seconds,
            )

        active_case_id = state_before.followup_cases[0].case_id if state_before.followup_cases else None
        alert_rec = self.psych_engine.trigger_and_dispatch_to_central(
            evaluation=psych_eval,
            vitals=self.vitals,
            adaptive_baseline=state_before.adaptive_baseline,
            mission_day=self.mission_day,
            followup_case_id=active_case_id,
        )

        # Update longitudinal series today snapshot with post-biofeedback stabilization
        if self.longitudinal_series:
            self.longitudinal_series[-1]["hr"] = self.vitals.heart_rate_bpm
            self.longitudinal_series[-1]["hrv"] = self.vitals.hrv_ms
            self.longitudinal_series[-1]["bp_sys"] = self.vitals.bp_systolic
            self.longitudinal_series[-1]["bp_dia"] = self.vitals.bp_diastolic
            self.longitudinal_series[-1]["mood"] = self.vitals.mood_score
            self.longitudinal_series[-1]["stress"] = self.vitals.stress_index

        stim_titles = ", ".join(s.title for s in alert_rec.dispatched_stimuli)
        if active_case_id:
            self.followup_manager.record_action(
                active_case_id,
                RecordActionRequest(
                    performed_by=f"AstraCare Biofeedback Engine + {state_before.crew_member}",
                    protocol_reference="OCHMO-MTB-009 / BHP Psychophysiological Countermeasure",
                    action_description=(
                        f"Dispatched Personal Vault Stimulus ({stim_titles}) for {alert_rec.primary_psych_label} "
                        f"[Score {alert_rec.weighted_score_0_100:.1f}/100]. HR {alert_rec.pre_stimulus_vitals['heart_rate_bpm']:.0f}->"
                        f"{alert_rec.post_stimulus_vitals['heart_rate_bpm']:.0f} bpm, HRV {alert_rec.pre_stimulus_vitals['hrv_ms']:.0f}->"
                        f"{alert_rec.post_stimulus_vitals['hrv_ms']:.0f} ms."
                    ),
                    schedule_reassessment_in_minutes=15,
                    outcome_note=f"Central MCC-BHP alert {alert_rec.central_alert_id} transmitted; T+15m reassessment scheduled.",
                ),
            )

        self._touch()
        # Automatically compile & queue SHA-256 Store-and-Forward package to Central (MCC-Houston)
        sync_pkg = self.create_earth_sync_package()
        alert_rec.earth_sync_package_id = sync_pkg.package_id

        self.earth_sync.record_audit_event(
            event_type="CENTRAL_BHP_PSYCH_ALERT_DISPATCHED",
            astronaut_id=self.astronaut_id,
            summary=(
                f"Alert {alert_rec.central_alert_id} sent to Central MCC-Houston BHP & Flight Surgeon: "
                f"{alert_rec.primary_psych_label} ({alert_rec.weighted_score_0_100:.1f}/100) -> Dispatched [{stim_titles}] "
                f"| Sync Package: {sync_pkg.package_id}."
            ),
            metadata={
                "central_alert_id": alert_rec.central_alert_id,
                "reason": reason,
                "pre_vitals": alert_rec.pre_stimulus_vitals,
                "post_vitals": alert_rec.post_stimulus_vitals,
                "earth_sync_package_id": sync_pkg.package_id,
            },
        )
        return alert_rec

    def get_state(self) -> MissionState:
        astro_profile = self.astronauts_by_id[self.astronaut_id]
        sc = self.scenarios_by_id[self.scenario_id]
        env = self.environments_by_id[self.environment_id]
        latency_sec = int(env.get("one_way_latency_seconds", 720))

        # 1. Pillar 1: Adaptive Individual Baseline
        adaptive_base = self.baseline_engine.evaluate(
            astronaut_profile=astro_profile,
            vitals=self.vitals,
            context=self.mission_context,
            longitudinal_series=self.longitudinal_series,
            mission_day=self.mission_day,
        )

        # 2. Pillar 2: Contextual Mission Intelligence
        contextual_report = self.context_engine.evaluate(
            vitals=self.vitals,
            nutrition=self.nutrition,
            context=self.mission_context,
            adaptive_baseline=adaptive_base,
        )

        # 3. Pillar 4 (ML): Calibrated Real ML + Uncertainty + 72h Trajectory Forecast
        ml_pred = self.ml_predictor.predict(
            vitals=self.vitals,
            nutrition=self.nutrition,
            context=self.mission_context,
            quality=self.measurement_quality,
            adaptive_baseline=adaptive_base,
            contextual_report=contextual_report,
            longitudinal_series=self.longitudinal_series,
        )
        self.measurement_quality.reliability_grade = ml_pred.uncertainty.reliability_grade

        # 4. Pillar 6: Individual-Baseline-Weighted Psychophysiological Biofeedback Evaluation
        psych_eval = self.psych_engine.evaluate(
            astronaut_profile=astro_profile,
            vitals=self.vitals,
            nutrition=self.nutrition,
            context=self.mission_context,
            adaptive_baseline=adaptive_base,
            one_way_latency_seconds=latency_sec,
        )

        # 5. Pillar 4 (Explainable & Auditable Alerts) + NASA-STD-3001 / OCHMO Rules
        clin_eval = evaluate_clinical_and_explainable_rules(
            vitals=self.vitals,
            nutrition=self.nutrition,
            environment_id=self.environment_id,
            context=self.mission_context,
            quality=self.measurement_quality,
            adaptive_baseline=adaptive_base,
            contextual_report=contextual_report,
            ml_prediction=ml_pred,
            catalog=self.catalog,
        )

        # 5b. Cross diagnosis: physical vs. NASA DONKI space weather vs. psychological
        cross = evaluate_cross_diagnosis(
            vitals=self.vitals,
            context=self.mission_context,
            space_weather=self.space_weather,
            contextual_report=contextual_report,
            clinical=clin_eval,
        )

        # 6. Pillar 3: Sync Explainable Alerts into Closed-Loop Follow-Up Cases
        active_cases = self.followup_manager.sync_alerts(
            alerts=clin_eval.explainable_alerts,
            astronaut_id=self.astronaut_id,
            astronaut_name=astro_profile["name"],
            mission_day=self.mission_day,
            stabilization_checklist=clin_eval.stabilization_checklist,
        )

        last_pkg_id = self.earth_sync.packages[-1].package_id if self.earth_sync.packages else None

        return MissionState(
            mission_day=self.mission_day,
            astronaut_id=self.astronaut_id,
            crew_member=astro_profile["name"],
            scenario_id=self.scenario_id,
            scenario_name=sc["name"],
            scenario_description=sc["description"],
            environment_id=self.environment_id,
            environment_name=env["name"],
            one_way_latency_seconds=latency_sec,
            vitals=self.vitals,
            measurement_quality=self.measurement_quality,
            mission_context=self.mission_context,
            nutrition=self.nutrition,
            adaptive_baseline=adaptive_base,
            contextual_intelligence=contextual_report,
            clinical_evaluation=clin_eval,
            ml_prediction=ml_pred,
            psych_biofeedback=psych_eval,
            central_psych_alerts=list(reversed(self.psych_engine.central_alerts_history[-10:])),
            explainable_alerts=clin_eval.explainable_alerts,
            followup_cases=active_cases,
            space_weather=self.space_weather,
            cross_diagnosis=cross,
            horizons_link=self.horizons_link,
            earth_sync_queue_count=self.earth_sync.pending_count(),
            earth_sync_last_package_id=last_pkg_id,
            astronauts_catalog=[
                {
                    "astronaut_id": a["astronaut_id"],
                    "name": a["name"],
                    "role": a["role"],
                    "agency": a["agency"],
                }
                for a in self.catalog.get("astronaut_profiles", [])
            ],
            longitudinal_series=self.longitudinal_series,
            scenarios_catalog=[
                {
                    "id": s["id"],
                    "name": s["name"],
                    "short_label": s["short_label"],
                    "severity": s["severity"],
                    "description": s["description"],
                }
                for s in self.catalog.get("scenarios", [])
            ],
            environments_catalog=self.catalog.get("environments", []),
            indicators_guide=self.catalog.get("indicators_guide", []),
            systems_guide=self.catalog.get("systems_guide", {}),
            last_updated=self.last_updated,
        )
