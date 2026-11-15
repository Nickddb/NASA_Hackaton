from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.engine.clinical_rules import (
    build_personal_baseline_from_profile,
    evaluate_clinical_and_explainable_rules,
    evaluate_personal_baseline,
    load_scenarios_catalog,
    max_severity,
)
from app.engine.earth_sync import EarthSyncManager
from app.engine.followup_loop import FollowUpCaseManager
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
    ClinicalEvaluationResult,
    ClinicalFollowUpCase,
    CompleteReassessmentRequest,
    ContextUpdateRequest,
    CrewAlertRecord,
    CrewMemberSummary,
    CrewRosterResponse,
    DispatchAlertRequest,
    EarthSyncPackage,
    HorizonsLinkStatus,
    LoggedFoodItem,
    MeasurementQualityProfile,
    MeasurementResponse,
    MissionContext,
    MissionState,
    NutritionHydrationState,
    PersonalBaseline,
    PsychBiofeedbackEvaluation,
    RecordActionRequest,
    RecordConfirmationRequest,
    SeverityStatus,
    SpaceWeatherSummary,
    StabilizeRequest,
    TelemedicineDossier,
    VitalSigns,
)

DEFAULT_CREW_META: dict[str, dict[str, str]] = {
    "elena_vance": {
        "callsign": "EVA-1",
        "mission_group": "EVA",
        "location_module": "ISS Quest Airlock (EVA)",
        "environment_id": "orbital_station",
        "initial_scenario_id": "nominal",
        "suit_variant": "MERCURY_EVA_SILVER",
        "suit_accent": "#38BDF8",
    },
    "lucas_ferreira": {
        "callsign": "PYL-1",
        "mission_group": "ISS",
        "location_module": "ISS Columbus Bio-Lab",
        "environment_id": "orbital_station",
        "initial_scenario_id": "hypoglycemia",
        "suit_variant": "MERCURY_EVA_GOLD",
        "suit_accent": "#F59E0B",
    },
    "kenji_sato": {
        "callsign": "PLT-1",
        "mission_group": "DEEP_SPACE",
        "location_module": "Orion Flight Deck",
        "environment_id": "transit",
        "initial_scenario_id": "nominal",
        "suit_variant": "MERCURY_IVA_SLATE",
        "suit_accent": "#34D399",
    },
    "amara_okafor": {
        "callsign": "MED-2",
        "mission_group": "ISS",
        "location_module": "ISS Harmony Medical Bay",
        "environment_id": "orbital_station",
        "initial_scenario_id": "nominal",
        "suit_variant": "MERCURY_EVA_CYAN",
        "suit_accent": "#22D3EE",
    },
    "liam_soren": {
        "callsign": "ORB-4",
        "mission_group": "DEEP_SPACE",
        "location_module": "Orion Habitation Ring",
        "environment_id": "transit",
        "initial_scenario_id": "systemic_infection",
        "suit_variant": "MERCURY_TRANSIT_COBALT",
        "suit_accent": "#EF4444",
    },
}


@dataclass
class CrewMemberRecord:
    crew_id: str
    name: str
    callsign: str
    role: str
    agency: str
    mission_group: str
    location_module: str
    suit_variant: str
    suit_accent: str
    environment_id: str
    scenario_id: str
    mission_day: int
    vitals: VitalSigns
    mission_context: MissionContext
    measurement_quality: MeasurementQualityProfile
    nutrition: NutritionHydrationState
    longitudinal_series: list[dict[str, Any]]
    personal_baseline: PersonalBaseline
    horizons_link: HorizonsLinkStatus
    last_measured_at: str
    active_alert: CrewAlertRecord | None = None
    pending_verification_measurement: bool = False


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
        self.followup_manager = FollowUpCaseManager()
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

        self.space_weather: SpaceWeatherSummary = load_sample_donki()
        self.last_updated: str = datetime.now(timezone.utc).isoformat()

        self.crew_records: dict[str, CrewMemberRecord] = {}
        for astro_profile in self.catalog.get("astronaut_profiles", []):
            cid = astro_profile["astronaut_id"]
            self.crew_records[cid] = self._build_initial_crew_record(astro_profile)

        self._active_crew_id: str = (
            "elena_vance" if "elena_vance" in self.crew_records else next(iter(self.crew_records))
        )

        # Evaluate every crew member once on boot to establish initial telemetry alerts accurately
        for record in self.crew_records.values():
            self._evaluate_record(record)

    # --- Backward-compatible properties delegating to active crew member ---
    def _member(self, crew_id: str | None = None) -> CrewMemberRecord:
        target = crew_id or self._active_crew_id
        if target not in self.crew_records:
            raise KeyError(f"Unknown astronaut_id / crew_id: {target}")
        return self.crew_records[target]

    @property
    def astronaut_id(self) -> str:
        return self._active_crew_id

    @astronaut_id.setter
    def astronaut_id(self, value: str) -> None:
        if value not in self.crew_records:
            raise KeyError(f"Unknown astronaut_id: {value}")
        self._active_crew_id = value

    @property
    def scenario_id(self) -> str:
        return self._member().scenario_id

    @scenario_id.setter
    def scenario_id(self, value: str) -> None:
        self._member().scenario_id = value

    @property
    def environment_id(self) -> str:
        return self._member().environment_id

    @environment_id.setter
    def environment_id(self, value: str) -> None:
        self._member().environment_id = value

    @property
    def mission_day(self) -> int:
        return self._member().mission_day

    @mission_day.setter
    def mission_day(self, value: int) -> None:
        self._member().mission_day = value

    @property
    def vitals(self) -> VitalSigns:
        return self._member().vitals

    @vitals.setter
    def vitals(self, value: VitalSigns) -> None:
        self._member().vitals = value

    @property
    def mission_context(self) -> MissionContext:
        return self._member().mission_context

    @mission_context.setter
    def mission_context(self, value: MissionContext) -> None:
        self._member().mission_context = value

    @property
    def measurement_quality(self) -> MeasurementQualityProfile:
        return self._member().measurement_quality

    @measurement_quality.setter
    def measurement_quality(self, value: MeasurementQualityProfile) -> None:
        self._member().measurement_quality = value

    @property
    def nutrition(self) -> NutritionHydrationState:
        return self._member().nutrition

    @nutrition.setter
    def nutrition(self, value: NutritionHydrationState) -> None:
        self._member().nutrition = value

    @property
    def longitudinal_series(self) -> list[dict[str, Any]]:
        return self._member().longitudinal_series

    @longitudinal_series.setter
    def longitudinal_series(self, value: list[dict[str, Any]]) -> None:
        self._member().longitudinal_series = value

    @property
    def horizons_link(self) -> HorizonsLinkStatus:
        return self._member().horizons_link

    @horizons_link.setter
    def horizons_link(self, value: HorizonsLinkStatus) -> None:
        self._member().horizons_link = value

    def _build_initial_crew_record(self, astro_profile: dict[str, Any]) -> CrewMemberRecord:
        cid = astro_profile["astronaut_id"]
        meta = DEFAULT_CREW_META.get(cid, {})
        env_id = astro_profile.get("environment_id", meta.get("environment_id", "transit"))
        sc_id = astro_profile.get("initial_scenario_id", meta.get("initial_scenario_id", "nominal"))
        if sc_id not in self.scenarios_by_id:
            sc_id = "nominal"
        if env_id not in self.environments_by_id:
            env_id = "transit"

        sc = self.scenarios_by_id[sc_id]
        env_info = self.environments_by_id[env_id]
        personal_baseline = build_personal_baseline_from_profile(astro_profile)
        vitals = VitalSigns(**sc["vitals"])
        if sc_id == "nominal":
            vitals = self._calibrate_vitals_to_personal_resting(vitals, personal_baseline)

        ctx = MissionContext(**sc.get("mission_context", {}))
        ctx.gravitational_g = float(env_info.get("gravitational_g", ctx.gravitational_g))
        if "mission_phase" in env_info:
            ctx.mission_phase = env_info["mission_phase"]

        series = [dict(row) for row in sc.get("longitudinal_series", [])]
        if sc_id == "nominal" and series:
            series[-1]["hr"] = vitals.heart_rate_bpm
            series[-1]["hrv"] = vitals.hrv_ms
            series[-1]["bp_sys"] = vitals.bp_systolic
            series[-1]["bp_dia"] = vitals.bp_diastolic
            series[-1]["glucose"] = vitals.glucose_mg_dl

        now_iso = datetime.now(timezone.utc).isoformat()
        return CrewMemberRecord(
            crew_id=cid,
            name=astro_profile["name"],
            callsign=astro_profile.get("callsign", meta.get("callsign", cid[:4].upper())),
            role=astro_profile["role"],
            agency=astro_profile.get("agency", "NASA"),
            mission_group=astro_profile.get("mission_group", meta.get("mission_group", "DEEP_SPACE")),
            location_module=astro_profile.get("location_module", meta.get("location_module", env_info["name"])),
            suit_variant=astro_profile.get("suit_variant", meta.get("suit_variant", "MERCURY_EVA_SILVER")),
            suit_accent=astro_profile.get("suit_accent", meta.get("suit_accent", "#38BDF8")),
            environment_id=env_id,
            scenario_id=sc_id,
            mission_day=int(sc.get("mission_day", 142)),
            vitals=vitals,
            mission_context=ctx,
            measurement_quality=MeasurementQualityProfile(**sc.get("measurement_quality", {})),
            nutrition=NutritionHydrationState(**sc["nutrition"]),
            longitudinal_series=series,
            personal_baseline=personal_baseline,
            horizons_link=load_sample_horizons(env_id),
            last_measured_at=now_iso,
        )

    @staticmethod
    def _calibrate_vitals_to_personal_resting(vitals: VitalSigns, baseline: PersonalBaseline) -> VitalSigns:
        return vitals.model_copy(
            update={
                "heart_rate_bpm": round(baseline.resting_hr_bpm, 1),
                "hrv_ms": round(baseline.resting_hrv_ms, 1),
                "bp_systolic": round(baseline.resting_bp_systolic, 1),
                "bp_diastolic": round(baseline.resting_bp_diastolic, 1),
                "glucose_mg_dl": round(baseline.resting_glucose_mg_dl, 1),
                "temperature_c": round(baseline.resting_temp_c, 2),
                "spo2_pct": round(baseline.resting_spo2_pct, 1),
                "sleep_hours": round(baseline.resting_sleep_hours, 1),
                "sleep_streak_low_days": 0,
                "mood_score": 5,
                "stress_index": 20.0,
                "shoulder_pain_score": 0,
                "pfo_decompression_risk": "LOW",
                "radiation_msv_h": 0.04,
            }
        )

    def _touch(self) -> None:
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def select_crew_member(self, crew_id: str) -> MissionState:
        member = self._member(crew_id)
        self._active_crew_id = crew_id
        self.earth_sync.record_audit_event(
            event_type="CREW_FOCUS_SELECTED",
            astronaut_id=crew_id,
            summary=f"Focused telemetry view on {member.name} ({member.callsign} · {member.location_module}).",
            metadata={"mission_group": member.mission_group},
        )
        self._touch()
        return self.get_state(crew_id)

    def switch_astronaut(self, astronaut_id: str) -> MissionState:
        return self.select_crew_member(astronaut_id)

    def switch_scenario(self, scenario_id: str, crew_id: str | None = None) -> MissionState:
        if scenario_id not in self.scenarios_by_id:
            raise KeyError(f"Unknown scenario_id: {scenario_id}")
        member = self._member(crew_id)
        sc = self.scenarios_by_id[scenario_id]
        member.scenario_id = scenario_id
        member.mission_day = int(sc.get("mission_day", 142))
        vitals = VitalSigns(**sc["vitals"])
        if scenario_id == "nominal":
            vitals = self._calibrate_vitals_to_personal_resting(vitals, member.personal_baseline)
            member.active_alert = None
            member.pending_verification_measurement = False
        member.vitals = vitals

        ctx = MissionContext(**sc.get("mission_context", {}))
        env_info = self.environments_by_id.get(member.environment_id, {})
        ctx.gravitational_g = float(env_info.get("gravitational_g", ctx.gravitational_g))
        if "mission_phase" in env_info:
            ctx.mission_phase = env_info["mission_phase"]
        member.mission_context = ctx
        member.measurement_quality = MeasurementQualityProfile(**sc.get("measurement_quality", {}))
        member.nutrition = NutritionHydrationState(**sc["nutrition"])
        member.longitudinal_series = [dict(row) for row in sc.get("longitudinal_series", [])]
        if scenario_id == "nominal" and member.longitudinal_series:
            member.longitudinal_series[-1]["hr"] = vitals.heart_rate_bpm
            member.longitudinal_series[-1]["hrv"] = vitals.hrv_ms
            member.longitudinal_series[-1]["bp_sys"] = vitals.bp_systolic
            member.longitudinal_series[-1]["bp_dia"] = vitals.bp_diastolic
            member.longitudinal_series[-1]["glucose"] = vitals.glucose_mg_dl
        member.last_measured_at = datetime.now(timezone.utc).isoformat()

        self.earth_sync.record_audit_event(
            event_type="SCENARIO_LOADED",
            astronaut_id=member.crew_id,
            summary=f"Loaded scenario '{sc['name']}' (Day {member.mission_day}) for {member.name}.",
            metadata={"scenario_id": scenario_id},
        )
        self._touch()
        return self.get_state(member.crew_id)

    def switch_environment(self, env_id: str, crew_id: str | None = None) -> MissionState:
        if env_id not in self.environments_by_id:
            raise KeyError(f"Unknown environment_id: {env_id}")
        member = self._member(crew_id)
        member.environment_id = env_id
        env_info = self.environments_by_id[env_id]
        member.mission_context.gravitational_g = float(env_info.get("gravitational_g", 0.0))
        if "mission_phase" in env_info:
            member.mission_context.mission_phase = env_info["mission_phase"]
        member.horizons_link = load_sample_horizons(env_id)
        self.earth_sync.record_audit_event(
            event_type="ENVIRONMENT_CALIBRATION_CHANGED",
            astronaut_id=member.crew_id,
            summary=f"Updated mission environment to {env_info['name']} ({member.mission_context.gravitational_g:.2f}g).",
            metadata={"environment_id": env_id},
        )
        self._touch()
        return self.get_state(member.crew_id)

    def update_context(self, req: ContextUpdateRequest, crew_id: str | None = None) -> MissionState:
        member = self._member(crew_id)
        if req.exercise_minutes_24h is not None:
            member.mission_context.exercise_minutes_24h = req.exercise_minutes_24h
        if req.exercise_modality is not None:
            member.mission_context.exercise_modality = req.exercise_modality
        if req.minutes_since_last_exercise is not None:
            member.mission_context.minutes_since_last_exercise = req.minutes_since_last_exercise
        if req.eva_status is not None:
            member.mission_context.eva_status = req.eva_status
        if req.hours_since_last_eva is not None:
            member.mission_context.hours_since_last_eva = req.hours_since_last_eva
        if req.cabin_co2_mmhg is not None:
            member.mission_context.cabin_co2_mmhg = req.cabin_co2_mmhg
        if req.cabin_o2_pct is not None:
            member.mission_context.cabin_o2_pct = req.cabin_o2_pct
        if req.cabin_temp_c is not None:
            member.mission_context.cabin_temp_c = req.cabin_temp_c
        if req.signal_quality_pct is not None:
            member.measurement_quality.overall_quality_pct = req.signal_quality_pct
            member.measurement_quality.wearable_ppg_quality_pct = req.signal_quality_pct
        if req.motion_artifact_detected is not None:
            member.measurement_quality.motion_artifact_detected = req.motion_artifact_detected
        if req.nibp_cuff_verified is not None:
            member.measurement_quality.nibp_cuff_verified = req.nibp_cuff_verified

        self.earth_sync.record_audit_event(
            event_type="CONTEXT_COVARIATES_UPDATED",
            astronaut_id=member.crew_id,
            summary="Updated operational/environmental context covariates.",
            metadata=req.model_dump(exclude_none=True),
        )
        self._touch()
        return self.get_state(member.crew_id)

    def dispatch_alert(self, crew_id: str, req: DispatchAlertRequest) -> CrewRosterResponse:
        """Mission Control dispatches a formal WARNING or CRITICAL alert to an astronaut."""
        member = self._member(crew_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        alert = CrewAlertRecord(
            alert_id=f"ALT-{member.callsign}-{uuid4().hex[:5].upper()}",
            severity=req.severity,
            message=req.message,
            issued_by=req.issued_by,
            issued_at=now_iso,
            acknowledged_by_crew=False,
            stabilization_applied=False,
            requires_confirmatory_measurement=True,
            origin_type="MISSION_CONTROL_DISPATCH",
        )
        member.active_alert = alert
        member.pending_verification_measurement = False

        if req.simulate_vitals_drift:
            base = member.personal_baseline
            if req.severity == "CRITICAL":
                member.vitals.heart_rate_bpm = round(max(member.vitals.heart_rate_bpm, base.hr_max + 26.0), 1)
                member.vitals.spo2_pct = round(min(member.vitals.spo2_pct, 92.2), 1)
                member.vitals.temperature_c = round(max(member.vitals.temperature_c, 38.4), 1)
                member.vitals.bp_systolic = round(min(member.vitals.bp_systolic, max(82.0, base.bp_sys_min - 14.0)), 1)
                member.vitals.stress_index = max(member.vitals.stress_index, 84.0)
                member.vitals.hrv_ms = min(member.vitals.hrv_ms, 23.0)
            else:
                member.vitals.heart_rate_bpm = round(max(member.vitals.heart_rate_bpm, base.hr_max + 10.0), 1)
                member.vitals.spo2_pct = round(min(member.vitals.spo2_pct, 94.6), 1)
                member.vitals.stress_index = max(member.vitals.stress_index, 62.0)

            if member.longitudinal_series:
                member.longitudinal_series[-1]["hr"] = member.vitals.heart_rate_bpm
                member.longitudinal_series[-1]["hrv"] = member.vitals.hrv_ms
                member.longitudinal_series[-1]["bp_sys"] = member.vitals.bp_systolic

        self.earth_sync.record_audit_event(
            event_type="MISSION_CONTROL_ALERT_DISPATCHED",
            astronaut_id=member.crew_id,
            summary=f"[{req.severity}] {req.message} (Issued by {req.issued_by}).",
            metadata={"alert_id": alert.alert_id, "simulate_vitals_drift": req.simulate_vitals_drift},
        )
        self._touch()
        return self.get_crew_roster()

    def acknowledge_alert(self, crew_id: str) -> CrewRosterResponse:
        """Crew onboard acknowledges alert receipt. NEVER silences, lowers, or clears an alert."""
        member = self._member(crew_id)
        if member.active_alert is not None:
            now_iso = datetime.now(timezone.utc).isoformat()
            member.active_alert.acknowledged_by_crew = True
            member.active_alert.acknowledged_at = now_iso
            self.earth_sync.record_audit_event(
                event_type="CREW_ALERT_ACKNOWLEDGED",
                astronaut_id=member.crew_id,
                summary=(
                    f"{member.name} acknowledged alert {member.active_alert.alert_id}. "
                    f"Alert remains active until stabilization + confirmatory scan."
                ),
                metadata={"alert_id": member.active_alert.alert_id},
            )
            self._touch()
        return self.get_crew_roster()

    def stabilize_crew_member(self, crew_id: str, req: StabilizeRequest | None = None) -> MissionState:
        """
        Applies clinical stabilization countermeasures bringing vitals toward the astronaut's
        personal resting baseline. Alert remains ACTIVE until a subsequent confirmatory measurement
        verifies biomarkers are truly within that astronaut's PersonalBaseline.
        """
        member = self._member(crew_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        note = req.note if req is not None else "Standard stabilization countermeasures administered by crew / CMO."

        member.vitals = self._calibrate_vitals_to_personal_resting(member.vitals, member.personal_baseline)
        sc_nom = self.scenarios_by_id["nominal"]
        env_info = self.environments_by_id.get(member.environment_id, {})
        ctx = MissionContext(**sc_nom.get("mission_context", {}))
        ctx.gravitational_g = float(env_info.get("gravitational_g", ctx.gravitational_g))
        if "mission_phase" in env_info:
            ctx.mission_phase = env_info["mission_phase"]
        member.mission_context = ctx
        member.nutrition = NutritionHydrationState(**sc_nom["nutrition"])
        member.scenario_id = "nominal"

        if member.longitudinal_series:
            member.longitudinal_series[-1]["hr"] = member.vitals.heart_rate_bpm
            member.longitudinal_series[-1]["hrv"] = member.vitals.hrv_ms
            member.longitudinal_series[-1]["bp_sys"] = member.vitals.bp_systolic
            member.longitudinal_series[-1]["bp_dia"] = member.vitals.bp_diastolic
            member.longitudinal_series[-1]["glucose"] = member.vitals.glucose_mg_dl
            member.longitudinal_series[-1]["sleep"] = member.vitals.sleep_hours
            member.longitudinal_series[-1]["mood"] = member.vitals.mood_score

        if member.active_alert is not None:
            member.active_alert.stabilization_applied = True
            member.active_alert.stabilization_note = note
            member.active_alert.stabilized_at = now_iso
            member.active_alert.requires_confirmatory_measurement = True
            member.pending_verification_measurement = True

        # Record executed stabilization actions on any open follow-up case for this astronaut
        for case in self.followup_manager.cases.values():
            if case.astronaut_id == member.crew_id and case.status != "RESOLVED":
                self.followup_manager.record_action(
                    case.case_id,
                    RecordActionRequest(
                        performed_by=f"Crew / CMO Stabilization Protocol ({member.callsign})",
                        protocol_reference="NASA-STD-3001 / OCHMO-TB-044 Stabilization",
                        action_description=note,
                        schedule_reassessment_in_minutes=15,
                        outcome_note="Awaiting confirmatory CHeCS scan before returning to NOMINAL.",
                    ),
                )

        self.earth_sync.record_audit_event(
            event_type="STABILIZATION_PROTOCOL_APPLIED",
            astronaut_id=member.crew_id,
            summary=f"Stabilization applied for {member.name}: '{note}'. Pending confirmatory measurement.",
        )
        self._touch()
        return self.get_state(member.crew_id)

    def trigger_measurement(self, system_id: str, crew_id: str | None = None) -> MeasurementResponse:
        member = self._member(crew_id)
        eval_before = self._evaluate_record(member)
        clin_before: ClinicalEvaluationResult = eval_before["clin_eval"]
        is_full_body = system_id == "full_body"
        if not is_full_body and system_id not in clin_before.systems:
            raise KeyError(f"Unknown system_id: {system_id}")

        # Active confirmation measurement improves sensor quality & instrument verification
        member.measurement_quality.overall_quality_pct = min(
            99.0, max(95.0, member.measurement_quality.overall_quality_pct + 4.0)
        )
        member.measurement_quality.motion_artifact_detected = False
        now_iso = datetime.now(timezone.utc).isoformat()
        member.last_measured_at = now_iso

        if is_full_body:
            member.measurement_quality.nibp_cuff_verified = True
            member.measurement_quality.ambient_temp_compensated = True
            member.measurement_quality.cgm_calibration_age_hours = 0.5
            reading = (
                f"Full-Body Confirmatory Scan: HR {member.vitals.heart_rate_bpm:.0f} bpm, "
                f"BP {member.vitals.bp_systolic:.0f}/{member.vitals.bp_diastolic:.0f} mmHg, "
                f"SpO2 {member.vitals.spo2_pct:.1f}%, Temp {member.vitals.temperature_c:.1f} C, "
                f"Glucose {member.vitals.glucose_mg_dl:.0f} mg/dL, Rad {member.vitals.radiation_msv_h:.2f} mSv/h"
            )
            rep_sys_id = "cardiovascular"
        elif system_id == "cardiovascular":
            member.measurement_quality.nibp_cuff_verified = True
            reading = (
                f"Anchored NIBP + Astroskin ECG Sync: {member.vitals.heart_rate_bpm:.0f} bpm, "
                f"HRV {member.vitals.hrv_ms:.0f} ms, BP {member.vitals.bp_systolic:.0f}/{member.vitals.bp_diastolic:.0f} mmHg "
                f"(SNR {member.measurement_quality.overall_quality_pct:.0f}%)"
            )
            rep_sys_id = "cardiovascular"
        elif system_id == "nervous_sleep":
            reading = (
                f"EEG/Actigraphy + Tonometry: Sleep {member.vitals.sleep_hours:.1f}h (REM {member.vitals.rem_sleep_pct:.0f}%), "
                f"Mood {member.vitals.mood_score}/5, IOP {member.vitals.intraocular_pressure_mmhg:.1f} mmHg"
            )
            rep_sys_id = "nervous_sleep"
        elif system_id == "respiratory":
            member.measurement_quality.ambient_temp_compensated = True
            reading = (
                f"Tempus Pro Capnography/IR: SpO2 {member.vitals.spo2_pct:.1f}%, RR {member.vitals.respiration_rpm:.0f} rpm, "
                f"Core Temp {member.vitals.temperature_c:.1f} C, Cabin CO2 {member.mission_context.cabin_co2_mmhg:.1f} mmHg"
            )
            rep_sys_id = "respiratory"
        elif system_id == "metabolic":
            member.measurement_quality.cgm_calibration_age_hours = 0.5
            reading = (
                f"i-STAT / Shielded Capillary Check: Glucose {member.vitals.glucose_mg_dl:.0f} mg/dL | "
                f"Intake {member.nutrition.calories_kcal:.0f}/{member.nutrition.goal_calories_kcal:.0f} kcal, {member.nutrition.water_ml:.0f} ml H2O"
            )
            rep_sys_id = "metabolic"
        elif system_id == "musculoskeletal":
            reading = (
                f"Ultrasound 2 & Urolux Scan: Shoulder VAS {member.vitals.shoulder_pain_score}/10, "
                f"Urinary Ca {member.vitals.urinary_calcium_mg_d:.0f} mg/day"
            )
            rep_sys_id = "musculoskeletal"
        else:
            reading = (
                f"BLE Dosimeter Sync: {member.vitals.radiation_msv_h:.2f} mSv/h instantaneous | "
                f"{member.vitals.cumulative_radiation_msv:.1f} mSv cumulative"
            )
            rep_sys_id = "radiation"

        # Strict Normalization Rule:
        # Alert clears ONLY if stabilization was already applied AND a confirmatory measurement
        # verifies BOTH clinical rules == NOMINAL and vitals within THAT astronaut's PersonalBaseline.
        eval_mid = self._evaluate_record(member, sync_alerts=False)
        clin_mid: ClinicalEvaluationResult = eval_mid["clin_eval"]
        within_personal = bool(eval_mid["within_personal_baseline"])
        raw_status: SeverityStatus = eval_mid["raw_clinical_status"]

        if member.active_alert is not None:
            if (
                member.active_alert.stabilization_applied
                and within_personal
                and raw_status == "NOMINAL"
            ):
                member.active_alert.confirmatory_measurement_at = now_iso
                cleared_id = member.active_alert.alert_id
                member.active_alert = None
                member.pending_verification_measurement = False
                for case in self.followup_manager.cases.values():
                    if case.astronaut_id == member.crew_id and case.status != "RESOLVED":
                        case.status = "RESOLVED"
                        case.updated_at = now_iso
                reading += f" | VERIFIED PERSONAL BASELINE RESTORED — Alert {cleared_id} cleared."
                self.earth_sync.record_audit_event(
                    event_type="ALERT_VERIFIED_NORMALIZED",
                    astronaut_id=member.crew_id,
                    summary=f"Confirmatory scan verified personal baseline for {member.name}; alert {cleared_id} resolved.",
                )
            else:
                deviations = eval_mid["baseline_deviations"]
                reason = (
                    f"Biomarkers outside personal baseline ({', '.join(deviations[:2])})"
                    if deviations
                    else "Stabilization protocol not yet applied prior to confirmatory scan"
                )
                reading += f" | ALERT REMAINS ACTIVE ({member.active_alert.severity}): {reason}."

        self._touch()
        updated_state = self.get_state(member.crew_id)
        sys_eval = updated_state.clinical_evaluation.systems[rep_sys_id]

        self.earth_sync.record_audit_event(
            event_type="ACTIVE_MEASUREMENT_TRIGGERED",
            astronaut_id=member.crew_id,
            summary=f"[{sys_eval.name}] {reading}",
            metadata={"system_id": system_id, "status": updated_state.clinical_evaluation.overall_status},
        )

        return MeasurementResponse(
            system_id=system_id,
            system_name="Full-Body Confirmatory Scan (All CHeCS)" if is_full_body else sys_eval.name,
            device_used="Integrated CHeCS Suite (Astroskin + NIBP + Tempus + i-STAT)" if is_full_body else sys_eval.checs_device,
            decontamination_required=updated_state.clinical_evaluation.decontamination_required,
            decontamination_checklist=updated_state.clinical_evaluation.decontamination_checklist,
            reading_summary=reading,
            status=updated_state.clinical_evaluation.overall_status if is_full_body else sys_eval.status,
            guidance=(
                updated_state.clinical_evaluation.primary_diagnosis
                if is_full_body
                else sys_eval.recommended_action
            ),
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

    async def refresh_space_weather(self) -> SpaceWeatherSummary:
        self.space_weather = await fetch_nasa_space_weather()
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

    def compile_dossier(self, crew_id: str | None = None) -> TelemedicineDossier:
        if crew_id is not None:
            self.select_crew_member(crew_id)
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

    @staticmethod
    def _sync_alert_for_member(
        member: CrewMemberRecord,
        raw_clinical_status: SeverityStatus,
        primary_diagnosis: str,
        baseline_deviations: list[str],
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        if raw_clinical_status != "NOMINAL":
            sev: SeverityStatus = "CRITICAL" if raw_clinical_status == "CRITICAL" else "WARNING"
            reason = (
                f"{primary_diagnosis}: {'; '.join(baseline_deviations[:3])}"
                if baseline_deviations
                else primary_diagnosis
            )
            if member.active_alert is None:
                member.active_alert = CrewAlertRecord(
                    alert_id=f"ALT-{member.callsign}-{uuid4().hex[:5].upper()}",
                    severity=sev,
                    message=reason,
                    issued_by="AstraCare Edge Telemetry & Clinical Rules",
                    issued_at=now_iso,
                    acknowledged_by_crew=False,
                    stabilization_applied=False,
                    requires_confirmatory_measurement=True,
                    origin_type="CLINICAL_TELEMETRY",
                )
            else:
                member.active_alert.severity = max_severity(member.active_alert.severity, sev)
                if not member.active_alert.stabilization_applied and baseline_deviations:
                    member.active_alert.message = reason
                member.active_alert.requires_confirmatory_measurement = True
        elif member.active_alert is not None:
            member.active_alert.requires_confirmatory_measurement = True

    def _evaluate_record(self, member: CrewMemberRecord, sync_alerts: bool = True) -> dict[str, Any]:
        astro_profile = self.astronauts_by_id[member.crew_id]
        sc = self.scenarios_by_id[member.scenario_id]
        env = self.environments_by_id[member.environment_id]
        latency_sec = int(env.get("one_way_latency_seconds", 720))

        # 1. Pillar 1: Adaptive Individual Baseline
        adaptive_base = self.baseline_engine.evaluate(
            astronaut_profile=astro_profile,
            vitals=member.vitals,
            context=member.mission_context,
            longitudinal_series=member.longitudinal_series,
            mission_day=member.mission_day,
        )

        # 2. Pillar 2: Contextual Mission Intelligence
        contextual_report = self.context_engine.evaluate(
            vitals=member.vitals,
            nutrition=member.nutrition,
            context=member.mission_context,
            adaptive_baseline=adaptive_base,
        )

        # 3. Pillar 4 (ML): Calibrated Real ML + Uncertainty + 72h Trajectory Forecast
        ml_pred = self.ml_predictor.predict(
            vitals=member.vitals,
            nutrition=member.nutrition,
            context=member.mission_context,
            quality=member.measurement_quality,
            adaptive_baseline=adaptive_base,
            contextual_report=contextual_report,
            longitudinal_series=member.longitudinal_series,
        )
        member.measurement_quality.reliability_grade = ml_pred.uncertainty.reliability_grade

        # 4. Pillar 6: Individual-Baseline-Weighted Psychophysiological Biofeedback Evaluation
        psych_eval = self.psych_engine.evaluate(
            astronaut_profile=astro_profile,
            vitals=member.vitals,
            nutrition=member.nutrition,
            context=member.mission_context,
            adaptive_baseline=adaptive_base,
            one_way_latency_seconds=latency_sec,
        )

        # 5. Pillar 4 (Explainable & Auditable Alerts) + NASA-STD-3001 / OCHMO Rules
        clin_eval = evaluate_clinical_and_explainable_rules(
            vitals=member.vitals,
            nutrition=member.nutrition,
            environment_id=member.environment_id,
            context=member.mission_context,
            quality=member.measurement_quality,
            adaptive_baseline=adaptive_base,
            contextual_report=contextual_report,
            ml_prediction=ml_pred,
            catalog=self.catalog,
        )

        within_personal, baseline_deviations, baseline_sev = evaluate_personal_baseline(
            member.vitals, member.personal_baseline
        )
        raw_clinical_status = max_severity(clin_eval.overall_status, baseline_sev)

        if sync_alerts:
            self._sync_alert_for_member(
                member,
                raw_clinical_status=raw_clinical_status,
                primary_diagnosis=clin_eval.primary_diagnosis,
                baseline_deviations=baseline_deviations,
            )

        effective_status = (
            max_severity(raw_clinical_status, member.active_alert.severity)
            if member.active_alert is not None
            else raw_clinical_status
        )
        clin_eval.overall_status = effective_status

        pending_verif = bool(
            member.active_alert is not None
            and (
                member.pending_verification_measurement
                or member.active_alert.stabilization_applied
                or (raw_clinical_status == "NOMINAL" and within_personal)
            )
        )
        member.pending_verification_measurement = pending_verif

        # 6. Pillar 3: Sync Explainable Alerts into Closed-Loop Follow-Up Cases
        active_cases = self.followup_manager.sync_alerts(
            alerts=clin_eval.explainable_alerts,
            astronaut_id=member.crew_id,
            astronaut_name=astro_profile["name"],
            mission_day=member.mission_day,
            stabilization_checklist=clin_eval.stabilization_checklist,
        )

        return {
            "astro_profile": astro_profile,
            "sc": sc,
            "env": env,
            "latency_sec": latency_sec,
            "adaptive_base": adaptive_base,
            "contextual_report": contextual_report,
            "ml_pred": ml_pred,
            "psych_eval": psych_eval,
            "clin_eval": clin_eval,
            "within_personal_baseline": within_personal,
            "baseline_deviations": baseline_deviations,
            "raw_clinical_status": raw_clinical_status,
            "effective_status": effective_status,
            "pending_verification_measurement": pending_verif,
            "active_cases": active_cases,
        }

    def get_crew_roster(self) -> CrewRosterResponse:
        summaries: list[CrewMemberSummary] = []
        counts: dict[str, int] = {
            "total": 0,
            "nominal": 0,
            "warning": 0,
            "critical": 0,
            "iss": 0,
            "deep_space": 0,
            "eva": 0,
        }
        for member in self.crew_records.values():
            ev = self._evaluate_record(member)
            eff_status: SeverityStatus = ev["effective_status"]
            clin_eval: ClinicalEvaluationResult = ev["clin_eval"]
            ml_pred = ev["ml_pred"]
            counts["total"] += 1
            counts[eff_status.lower()] += 1
            counts[member.mission_group.lower()] += 1

            summaries.append(
                CrewMemberSummary(
                    crew_id=member.crew_id,
                    name=member.name,
                    callsign=member.callsign,
                    role=member.role,
                    mission_group=member.mission_group,  # type: ignore[arg-type]
                    location_module=member.location_module,
                    environment_id=member.environment_id,
                    scenario_id=member.scenario_id,
                    suit_variant=member.suit_variant,
                    suit_accent=member.suit_accent,
                    status=eff_status,
                    clinical_status=ev["raw_clinical_status"],
                    within_personal_baseline=ev["within_personal_baseline"],
                    baseline_deviations=ev["baseline_deviations"],
                    active_alert=member.active_alert,
                    pending_verification_measurement=ev["pending_verification_measurement"],
                    vitals=member.vitals,
                    mission_context=member.mission_context,
                    personal_baseline=member.personal_baseline,
                    primary_diagnosis=clin_eval.primary_diagnosis,
                    anomaly_score=ml_pred.anomaly_score,
                    last_measured_at=member.last_measured_at,
                )
            )

        active_member = self._member()
        return CrewRosterResponse(
            mission_day=active_member.mission_day,
            active_crew_id=self._active_crew_id,
            summary_counts=counts,
            space_weather=self.space_weather,
            crew=summaries,
            last_updated=self.last_updated,
        )

    def get_state(self, crew_id: str | None = None) -> MissionState:
        member = self._member(crew_id)
        ev = self._evaluate_record(member)
        astro_profile = ev["astro_profile"]
        sc = ev["sc"]
        env = ev["env"]
        latency_sec = ev["latency_sec"]
        clin_eval: ClinicalEvaluationResult = ev["clin_eval"]
        last_pkg_id = self.earth_sync.packages[-1].package_id if self.earth_sync.packages else None

        return MissionState(
            mission_day=member.mission_day,
            astronaut_id=member.crew_id,
            crew_id=member.crew_id,
            crew_member=astro_profile["name"],
            crew_role=member.role,
            mission_group=member.mission_group,
            location_module=member.location_module,
            suit_variant=member.suit_variant,
            scenario_id=member.scenario_id,
            scenario_name=sc["name"],
            scenario_description=sc["description"],
            environment_id=member.environment_id,
            environment_name=env["name"],
            one_way_latency_seconds=latency_sec,
            vitals=member.vitals,
            measurement_quality=member.measurement_quality,
            mission_context=member.mission_context,
            nutrition=member.nutrition,
            personal_baseline=member.personal_baseline,
            within_personal_baseline=ev["within_personal_baseline"],
            baseline_deviations=ev["baseline_deviations"],
            active_alert=member.active_alert,
            pending_verification_measurement=ev["pending_verification_measurement"],
            last_measured_at=member.last_measured_at,
            adaptive_baseline=ev["adaptive_base"],
            contextual_intelligence=ev["contextual_report"],
            clinical_evaluation=clin_eval,
            ml_prediction=ev["ml_pred"],
            psych_biofeedback=ev["psych_eval"],
            central_psych_alerts=list(reversed(self.psych_engine.central_alerts_history[-10:])),
            explainable_alerts=clin_eval.explainable_alerts,
            followup_cases=ev["active_cases"],
            space_weather=self.space_weather,
            horizons_link=member.horizons_link,
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
            longitudinal_series=member.longitudinal_series,
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
