from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import numpy as np

from app.engine.clinical_rules import (
    build_personal_baseline_from_profile,
    evaluate_clinical_and_explainable_rules,
    evaluate_personal_baseline,
    load_scenarios_catalog,
    max_severity,
)
from app.engine.cross_diagnosis import SEVERE_PSYCH, evaluate_cross_diagnosis
from app.engine.earth_sync import FOLLOWUP_STORE_PATH, EarthSyncManager
from app.engine.followup_loop import FollowUpCaseManager
from app.engine.nasa_feeds import (
    fetch_nasa_space_weather,
    load_sample_donki,
    load_sample_horizons,
)
from app.engine.telemetry_generator import CRISIS_PROFILES, TelemetryGenerator
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
    EscalateCaseRequest,
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

DEFAULT_CREW_META: dict[str, dict[str, Any]] = {
    "elena_vance": {
        "callsign": "EVA-1",
        "role": "Mission Commander & Lead EVA Specialist",
        "mission_group": "EVA",
        "location_module": "ISS Quest Airlock (EVA)",
        "suit_variant": "MERCURY_EVA_SILVER",
        "environment_id": "transit",
        "initial_scenario_id": "nominal",
    },
    "lucas_ferreira": {
        "callsign": "MS-1",
        "role": "Mission Specialist & Biomedical Payload Officer",
        "mission_group": "INTERNAL",
        "location_module": "Columbus Bio-Lab",
        "suit_variant": "IVA_FLIGHT_BLUE",
        "environment_id": "orbital_station",
        "initial_scenario_id": "hypoglycemia",
    },
    "kenji_sato": {
        "callsign": "PLT-1",
        "role": "Spacecraft Pilot & Systems Engineer",
        "mission_group": "EVA",
        "location_module": "Orion Flight Deck",
        "suit_variant": "MERCURY_IVA_SLATE",
        "environment_id": "transit",
        "initial_scenario_id": "nominal",
    },
    "amara_okafor": {
        "callsign": "MED-2",
        "role": "Crew Medical Officer",
        "mission_group": "INTERNAL",
        "location_module": "ISS Harmony Medical Bay",
        "suit_variant": "MERCURY_EVA_CYAN",
        "environment_id": "orbital_station",
        "initial_scenario_id": "nominal",
    },
    "liam_soren": {
        "callsign": "MS-3",
        "role": "Propulsion & Habitat Environmental Specialist",
        "mission_group": "INTERNAL",
        "location_module": "Zvezda Habitation Core",
        "suit_variant": "IVA_OPS_AMBER",
        "environment_id": "transit",
        "initial_scenario_id": "systemic_infection",
    },
}

SYNDROME_TO_SYSTEM: dict[str, str] = {
    "nominal": "cardiovascular",
    "post_exercise_physiological": "cardiovascular",
    "orthostatic_intolerance": "cardiovascular",
    "decompression_sickness": "respiratory",
    "cabin_co2_pocket": "respiratory",
    "hypoglycemia": "metabolic",
    "systemic_infection": "respiratory",
    "behavioral_fatigue": "nervous_sleep",
    "solar_storm": "radiation",
    "external_medical_alert": "cardiovascular",
}


class CrewMemberRecord:
    """Isolated runtime state for a single astronaut on the mission roster."""

    def __init__(
        self,
        crew_id: str,
        profile: dict[str, Any],
        meta: dict[str, Any],
        scenario: dict[str, Any],
        mission_day: int,
    ) -> None:
        self.crew_id: str = crew_id
        self.profile: dict[str, Any] = profile
        self.name: str = profile.get("name", crew_id)
        self.callsign: str = profile.get("callsign", meta.get("callsign", crew_id.upper()))
        self.role: str = profile.get("role", meta.get("role", "Crew Specialist"))
        self.mission_group: str = meta.get("mission_group", profile.get("mission_group", "INTERNAL"))
        self.location_module: str = meta.get("location_module", profile.get("location_module", "Habitat Module"))
        self.suit_variant: str = meta.get("suit_variant", profile.get("suit_variant", "IVA_STANDARD"))
        self.environment_id: str = meta.get("environment_id", profile.get("environment_id", "transit"))

        self.scenario_id: str = scenario["id"]
        self.mission_day: int = int(scenario.get("mission_day", mission_day))
        self.mission_context: MissionContext = MissionContext(**scenario.get("mission_context", {}))
        self.measurement_quality: MeasurementQualityProfile = MeasurementQualityProfile(
            **scenario.get("measurement_quality", {})
        )
        self.nutrition: NutritionHydrationState = NutritionHydrationState(**scenario["nutrition"])

        gen = TelemetryGenerator(self.profile, self.mission_context.mission_phase)
        vitals_dict, series = gen.generate(scenario.get("crisis_profile", self.scenario_id), self.mission_day)
        vitals_dict["reported_symptoms"] = list(scenario.get("reported_symptoms", []))
        self.vitals: VitalSigns = VitalSigns(**vitals_dict)
        self.longitudinal_series: list[dict[str, Any]] = series

        self.personal_baseline: PersonalBaseline = build_personal_baseline_from_profile(profile)
        self.active_alert: CrewAlertRecord | None = None
        self.pending_verification_measurement: bool = False
        now_iso = datetime.now(timezone.utc).isoformat()
        self.last_measured_at: str = now_iso
        self.last_updated: str = now_iso
        self.horizons_link: HorizonsLinkStatus = load_sample_horizons(self.environment_id)


class MissionStateManager:
    """
    Central orchestrator for AstraCare AI's 6 ML, Psychophysiological & Clinical Continuity Pillars:
      1. Adaptive Individual Baseline (EWMA + MAD + Ledoit-Wolf Mahalanobis + OSDR Phase Priors)
      2. Contextual Mission Intelligence (Sleep, Exercise, EVA, Gravity Phase, Cabin CO2/O2)
      3. Closed-Loop Follow-Up Cycle (Confirmation Measurements -> Actions -> Scheduled Reassessments)
      4. Explainable & Auditable Real ML (Calibrated HGB+RF Ensemble, Epistemic/Aleatoric Uncertainty, 72h Forecast)
      5. Spacecraft-Earth Store-and-Forward Continuity (SHA-256 Offline Ledger & MCC Sync Bundles)
      6. Individual-Weighted Psychophysiological Biofeedback Countermeasure & Central BHP Alert Dispatch
      + Multi-Crew Roster & Alert/Stabilization/Confirmatory Measurement Hub
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

        self.telemetry_rng = np.random.default_rng()
        self.active_crew_id: str = "elena_vance"
        self.crew_records: dict[str, CrewMemberRecord] = {}
        self.space_weather: SpaceWeatherSummary = load_sample_donki(simulated={})
        self._bootstrap_crew_records()
        self.space_weather = load_sample_donki(simulated=self._scenario_donki())

    def _bootstrap_crew_records(self) -> None:
        default_sc = self.scenarios_by_id["nominal"]
        for astro_id, profile in self.astronauts_by_id.items():
            meta = DEFAULT_CREW_META.get(astro_id, {})
            sc_id = meta.get("initial_scenario_id", profile.get("initial_scenario_id", "nominal"))
            sc = self.scenarios_by_id.get(sc_id, default_sc)
            record = CrewMemberRecord(
                crew_id=astro_id,
                profile=profile,
                meta=meta,
                scenario=sc,
                mission_day=int(sc.get("mission_day", 142)),
            )
            self.crew_records[astro_id] = record
            if sc_id != "nominal":
                self._evaluate_record(record, sync_followup=False)

    def _member(self, crew_id: str | None = None) -> CrewMemberRecord:
        target_id = crew_id or self.active_crew_id
        if target_id not in self.crew_records:
            target_id = self.active_crew_id
        return self.crew_records[target_id]

    # --- Backward-compatible properties delegating to the active crew member ---
    @property
    def astronaut_id(self) -> str:
        return self.active_crew_id

    @astronaut_id.setter
    def astronaut_id(self, value: str) -> None:
        if value in self.crew_records:
            self.active_crew_id = value

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
    def vitals(self) -> VitalSigns:
        return self._member().vitals

    @vitals.setter
    def vitals(self, value: VitalSigns) -> None:
        self._member().vitals = value

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

    @property
    def last_updated(self) -> str:
        return self._member().last_updated

    @last_updated.setter
    def last_updated(self, value: str) -> None:
        self._member().last_updated = value

    # ---------- Stochastic telemetry (replaces static scenario vitals) ----------
    def record_reported_symptom(self, text: str, crew_id: str | None = None) -> None:
        """Keep crew-reported symptoms (from chat) so the cross-diagnosis tree and the dashboard see them."""
        member = self._member(crew_id)
        text = text.strip()
        if text and text not in member.vitals.reported_symptoms:
            member.vitals.reported_symptoms = (member.vitals.reported_symptoms + [text])[-8:]
            self.earth_sync.record_audit_event(
                event_type="CREW_SYMPTOM_REPORTED",
                astronaut_id=member.crew_id,
                summary=f"Crew report: {text[:160]}",
            )
            self._touch(member)

    def escalate_psych_priority(self, reason: str, crew_id: str | None = None) -> EarthSyncPackage:
        """Immediate Earth alert for severe psychological risk: audit entry + a store-and-forward package
        that goes first in the next communication window."""
        member = self._member(crew_id)
        self.earth_sync.record_audit_event(
            event_type="PSYCH_CRITICAL_ESCALATION",
            astronaut_id=member.crew_id,
            summary=f"IMMEDIATE behavioral-health alert to Earth Flight Surgeon: {reason}",
            metadata={"priority": "IMMEDIATE"},
        )
        pkg = self.create_earth_sync_package()
        if member.horizons_link.comms_available:
            self.earth_sync.synchronize_queued_packages(comms_available=True)
        return pkg

    def _scenario_donki(self, scenario_id: str | None = None) -> dict[str, list[dict[str, Any]]]:
        """Scenario-only DONKI events (e.g. the solar-storm drill), stamped relative to now so they are active.
        Kept separate from real NASA data and labelled origin='scenario_simulation' downstream."""
        sc_id = scenario_id or self.scenario_id
        sim = self.scenarios_by_id.get(sc_id, {}).get("donki_simulation") or {}
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

    def _generator(self, member: CrewMemberRecord | None = None) -> TelemetryGenerator:
        m = member or self._member()
        return TelemetryGenerator(self.astronauts_by_id[m.crew_id], m.mission_context.mission_phase)

    def _generate_telemetry(self, member: CrewMemberRecord | None = None) -> None:
        m = member or self._member()
        sc = self.scenarios_by_id[m.scenario_id]
        vitals, series = self._generator(m).generate(sc.get("crisis_profile", m.scenario_id), m.mission_day)
        vitals["reported_symptoms"] = list(sc.get("reported_symptoms", []))
        m.vitals = VitalSigns(**vitals)
        m.longitudinal_series = series

    def next_telemetry_reading(
        self, crisis_probability: float = 0.0, crew_id: str | None = None
    ) -> MissionState:
        """New noisy reading from the generator. With crisis_probability > 0 a nominal mission can
        stochastically enter one of the crisis profiles (demo of unplanned events)."""
        member = self._member(crew_id)
        if (
            member.scenario_id == "nominal"
            and crisis_probability > 0
            and self.telemetry_rng.random() < crisis_probability
        ):
            crises = [k for k in CRISIS_PROFILES if k != "nominal" and k in self.scenarios_by_id]
            return self.switch_scenario(str(self.telemetry_rng.choice(crises)), crew_id=member.crew_id)

        sc = self.scenarios_by_id[member.scenario_id]
        reading = self._generator(member).next_reading(
            sc.get("crisis_profile", member.scenario_id), member.vitals.model_dump(), self.telemetry_rng
        )
        member.vitals = VitalSigns(**reading)
        today = member.longitudinal_series[-1] if member.longitudinal_series else None
        if today is not None:
            for metric, key in (
                ("heart_rate_bpm", "hr"),
                ("hrv_ms", "hrv"),
                ("temperature_c", "temp"),
                ("bp_systolic", "bp_sys"),
                ("bp_diastolic", "bp_dia"),
                ("radiation_msv_h", "radiation"),
                ("glucose_mg_dl", "glucose"),
                ("spo2_pct", "spo2"),
                ("respiration_rpm", "rr"),
            ):
                today[key] = reading[metric]
        self._touch(member)
        return self.get_state(crew_id=member.crew_id)

    def _touch(self, member: CrewMemberRecord | None = None) -> None:
        m = member or self._member()
        m.last_updated = datetime.now(timezone.utc).isoformat()

    def select_crew_member(self, crew_id: str) -> MissionState:
        if crew_id not in self.crew_records:
            raise KeyError(f"Unknown crew_id: {crew_id}")
        self.active_crew_id = crew_id
        return self.get_state(crew_id=crew_id)

    def switch_astronaut(self, astronaut_id: str) -> MissionState:
        if astronaut_id not in self.astronauts_by_id:
            raise KeyError(f"Unknown astronaut_id: {astronaut_id}")
        current_sc = self.scenario_id
        self.active_crew_id = astronaut_id
        member = self._member(astronaut_id)
        member.scenario_id = current_sc
        member.active_alert = None
        member.pending_verification_measurement = False
        self._generate_telemetry(member)  # vitals are drawn around this astronaut's own baseline
        self.earth_sync.record_audit_event(
            event_type="ASTRONAUT_PROFILE_SWITCHED",
            astronaut_id=astronaut_id,
            summary=f"Switched active personal baseline profile to {self.astronauts_by_id[astronaut_id]['name']}.",
        )
        self._touch(member)
        return self.get_state(crew_id=astronaut_id)

    def switch_scenario(self, scenario_id: str, crew_id: str | None = None) -> MissionState:
        if scenario_id not in self.scenarios_by_id:
            raise KeyError(f"Unknown scenario_id: {scenario_id}")
        member = self._member(crew_id)
        sc = self.scenarios_by_id[scenario_id]
        member.scenario_id = scenario_id
        member.mission_day = int(sc.get("mission_day", 142))
        member.mission_context = MissionContext(**sc.get("mission_context", {}))
        member.measurement_quality = MeasurementQualityProfile(**sc.get("measurement_quality", {}))
        member.nutrition = NutritionHydrationState(**sc["nutrition"])
        member.active_alert = None
        member.pending_verification_measurement = False
        self._generate_telemetry(member)
        if member.crew_id == self.active_crew_id:
            self.space_weather = load_sample_donki(simulated=self._scenario_donki(scenario_id))
        self.earth_sync.record_audit_event(
            event_type="SCENARIO_LOADED",
            astronaut_id=member.crew_id,
            summary=f"Loaded scenario '{sc['name']}' (Day {member.mission_day}).",
            metadata={"scenario_id": scenario_id},
        )
        self._touch(member)
        return self.get_state(crew_id=member.crew_id)

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
        self._generate_telemetry(member)  # gravity phase shifts the nominal centre
        self.earth_sync.record_audit_event(
            event_type="ENVIRONMENT_CALIBRATION_CHANGED",
            astronaut_id=member.crew_id,
            summary=f"Updated mission environment to {env_info['name']} ({member.mission_context.gravitational_g:.2f}g).",
            metadata={"environment_id": env_id},
        )
        self._touch(member)
        return self.get_state(crew_id=member.crew_id)

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
        self._touch(member)
        return self.get_state(crew_id=member.crew_id)

    # --- Multi-Crew Alert & Stabilization Workflow ---
    def dispatch_alert(self, crew_id: str, payload: DispatchAlertRequest) -> MissionState:
        if crew_id not in self.crew_records:
            raise KeyError(f"Unknown crew_id: {crew_id}")
        member = self._member(crew_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        if payload.simulate_vitals_drift:
            v = member.vitals.model_dump()
            pb = member.personal_baseline
            sys_id = payload.target_system_id
            if sys_id == "cardiovascular":
                v["heart_rate_bpm"] = round(pb.hr_max + (24.0 if payload.severity == "CRITICAL" else 14.0), 1)
                v["bp_systolic"] = round(pb.bp_sys_max + (18.0 if payload.severity == "CRITICAL" else 10.0), 1)
                v["hrv_ms"] = round(max(18.0, pb.hrv_min - 12.0), 1)
            elif sys_id in ("respiratory_atmospheric", "respiratory"):
                v["spo2_pct"] = round(pb.spo2_min - (4.0 if payload.severity == "CRITICAL" else 2.0), 1)
                v["respiration_rpm"] = round(pb.resp_max + 4.5, 1)
                member.mission_context.cabin_co2_mmhg = 6.2 if payload.severity == "CRITICAL" else 4.9
                if payload.syndrome_code == "decompression_sickness":
                    member.mission_context.suit_pressure_psi = 4.1
                    member.mission_context.eva_status = "active_eva"
            elif sys_id in ("metabolic_endocrine", "metabolic"):
                v["glucose_mg_dl"] = round(pb.glucose_min - (18.0 if payload.severity == "CRITICAL" else 11.0), 1)
                v["heart_rate_bpm"] = round(pb.hr_max + 9.0, 1)
            elif sys_id in ("thermal_immunological", "thermal"):
                v["temperature_c"] = round(pb.temp_max + (1.2 if payload.severity == "CRITICAL" else 0.7), 1)
                v["heart_rate_bpm"] = round(pb.hr_max + 15.0, 1)
                v["hrv_ms"] = round(max(19.0, pb.hrv_min - 11.0), 1)
            elif sys_id in ("neuro_behavioral_sleep", "nervous_sleep"):
                v["sleep_hours"] = round(max(3.5, pb.sleep_min - 2.1), 1)
                v["stress_index"] = round(min(92.0, pb.stress_max + 32.0), 1)
                v["mood_score"] = 2 if payload.severity == "CRITICAL" else 3
            elif sys_id in ("radiation_space_weather", "radiation"):
                v["radiation_msv_h"] = 0.85 if payload.severity == "CRITICAL" else 0.25
                v["stress_index"] = round(min(85.0, pb.stress_max + 20.0), 1)
            member.vitals = VitalSigns(**v)

        _, deviations, _ = evaluate_personal_baseline(member.vitals, member.personal_baseline)
        default_actions = payload.recommended_actions or [
            "Realizar aferição confirmatória em repouso com dispositivo de bordo.",
            "Aplicar protocolo de estabilização clínica sob supervisão do CMO.",
            "Repetir aferição completa após estabilização para autorizar retorno ao status NORMAL.",
        ]

        member.active_alert = CrewAlertRecord(
            alert_id=f"CREW-ALT-{member.crew_id[:5].upper()}-{uuid4().hex[:6].upper()}",
            crew_id=member.crew_id,
            severity=payload.severity,
            syndrome_code=payload.syndrome_code,
            title=payload.title,
            summary=payload.summary,
            deviations=deviations or [payload.summary],
            recommended_actions=default_actions,
            target_system_id=payload.target_system_id,
            status="OPEN",
            stabilization_applied=False,
            verification_measurement_completed=False,
            created_at=now_iso,
            updated_at=now_iso,
            origin="EXTERNAL_ALERT",
        )
        member.pending_verification_measurement = True
        member.last_updated = now_iso
        return self._evaluate_record(member)

    def acknowledge_alert(self, crew_id: str) -> MissionState:
        if crew_id not in self.crew_records:
            raise KeyError(f"Unknown crew_id: {crew_id}")
        member = self._member(crew_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        if member.active_alert and member.active_alert.status == "OPEN":
            member.active_alert.status = "ACKNOWLEDGED"
            member.active_alert.updated_at = now_iso
        member.last_updated = now_iso
        return self._evaluate_record(member)

    def stabilize_crew_member(self, crew_id: str, payload: StabilizeRequest) -> MissionState:
        """Apply clinical stabilization and restore vitals toward the astronaut's personal nominal range.
        IMPORTANT: The astronaut does NOT return to NOMINAL status until a confirmatory measurement is performed."""
        if crew_id not in self.crew_records:
            raise KeyError(f"Unknown crew_id: {crew_id}")
        member = self._member(crew_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        nominal_sc = self.scenarios_by_id["nominal"]
        member.scenario_id = "nominal"
        member.mission_context = MissionContext(**nominal_sc.get("mission_context", {}))
        if member.environment_id == "lunar_eva":
            member.mission_context.eva_status = "post_eva_recovery"
            member.mission_context.suit_pressure_psi = 14.7

        self._generate_telemetry(member)
        member.measurement_quality = MeasurementQualityProfile(
            overall_quality_pct=98.0,
            wearable_ppg_quality_pct=98.0,
            nibp_cuff_verified=True,
            cgm_calibration_age_hours=1.0,
            motion_artifact_detected=False,
            ambient_temp_compensated=True,
            reliability_grade="HIGH",
            sensor_notes="Post-stabilization telemetry calibrated; awaiting confirmatory measurement.",
        )

        if member.active_alert is None:
            member.active_alert = CrewAlertRecord(
                alert_id=f"CREW-ALT-{member.crew_id[:5].upper()}-{uuid4().hex[:6].upper()}",
                crew_id=member.crew_id,
                severity="ATTENTION",
                syndrome_code="post_stabilization_verification",
                title="Estabilização Aplicada — Aguardando Aferição Confirmatória",
                summary=payload.intervention_note,
                deviations=[],
                recommended_actions=["Executar aferição confirmatória para liberar retorno ao status NORMAL."],
                target_system_id=payload.target_system_id or "cardiovascular",
                status="STABILIZING",
                stabilization_applied=True,
                stabilization_note=payload.intervention_note,
                verification_measurement_completed=False,
                created_at=now_iso,
                updated_at=now_iso,
                origin="STABILIZATION_FLOW",
            )
        else:
            if member.active_alert.severity == "CRITICAL":
                member.active_alert.severity = "WARNING"
            elif member.active_alert.severity == "WARNING":
                member.active_alert.severity = "ATTENTION"
            member.active_alert.status = "STABILIZING"
            member.active_alert.stabilization_applied = True
            member.active_alert.stabilization_note = payload.intervention_note
            member.active_alert.verification_measurement_completed = False
            member.active_alert.updated_at = now_iso

        member.pending_verification_measurement = True
        member.last_updated = now_iso
        return self._evaluate_record(member)

    def trigger_measurement(self, system_id: str, crew_id: str | None = None) -> MeasurementResponse:
        member = self._member(crew_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        state_before = self.get_state(crew_id=member.crew_id)

        # Map legacy / CrewHub system IDs smoothly
        alias_map = {
            "respiratory_atmospheric": "respiratory",
            "metabolic_endocrine": "metabolic",
            "thermal_immunological": "respiratory",
            "neuro_behavioral_sleep": "nervous_sleep",
            "radiation_space_weather": "radiation",
        }
        canonical_sys_id = alias_map.get(system_id, system_id)

        if canonical_sys_id != "full_body" and canonical_sys_id not in state_before.clinical_evaluation.systems:
            raise KeyError(f"Unknown system_id: {system_id}")

        # Active confirmation measurement improves sensor quality & NIBP verification
        member.measurement_quality.overall_quality_pct = min(
            99.0, max(94.0, member.measurement_quality.overall_quality_pct + 4.0)
        )
        member.measurement_quality.motion_artifact_detected = False
        member.last_measured_at = now_iso

        if canonical_sys_id == "full_body":
            member.measurement_quality.nibp_cuff_verified = True
            member.measurement_quality.ambient_temp_compensated = True
            reading = (
                f"Varredura Completa CHeCS: FC {member.vitals.heart_rate_bpm:.0f} bpm, "
                f"PA {member.vitals.bp_systolic:.0f}/{member.vitals.bp_diastolic:.0f} mmHg, "
                f"SpO2 {member.vitals.spo2_pct:.1f}%, Temp {member.vitals.temperature_c:.1f} C, "
                f"Glicose {member.vitals.glucose_mg_dl:.0f} mg/dL (SNR {member.measurement_quality.overall_quality_pct:.0f}%)"
            )
        elif canonical_sys_id == "cardiovascular":
            member.measurement_quality.nibp_cuff_verified = True
            reading = (
                f"Anchored NIBP + Astroskin ECG Sync: {member.vitals.heart_rate_bpm:.0f} bpm, "
                f"HRV {member.vitals.hrv_ms:.0f} ms, BP {member.vitals.bp_systolic:.0f}/{member.vitals.bp_diastolic:.0f} mmHg "
                f"(SNR {member.measurement_quality.overall_quality_pct:.0f}%)"
            )
        elif canonical_sys_id == "nervous_sleep":
            reading = (
                f"EEG/Actigraphy + Tonometry: Sleep {member.vitals.sleep_hours:.1f}h (REM {member.vitals.rem_sleep_pct:.0f}%), "
                f"Mood {member.vitals.mood_score}/5, IOP {member.vitals.intraocular_pressure_mmhg:.1f} mmHg"
            )
        elif canonical_sys_id == "respiratory":
            member.measurement_quality.ambient_temp_compensated = True
            reading = (
                f"Tempus Pro Capnography/IR: SpO2 {member.vitals.spo2_pct:.1f}%, RR {member.vitals.respiration_rpm:.0f} rpm, "
                f"Core Temp {member.vitals.temperature_c:.1f} C, Cabin CO2 {member.mission_context.cabin_co2_mmhg:.1f} mmHg"
            )
        elif canonical_sys_id == "metabolic":
            member.measurement_quality.cgm_calibration_age_hours = 0.5
            reading = (
                f"i-STAT / Shielded Capillary Check: Glucose {member.vitals.glucose_mg_dl:.0f} mg/dL | "
                f"Intake {member.nutrition.calories_kcal:.0f}/{member.nutrition.goal_calories_kcal:.0f} kcal, {member.nutrition.water_ml:.0f} ml H2O"
            )
        elif canonical_sys_id == "musculoskeletal":
            reading = (
                f"Ultrasound 2 & Urolux Scan: Shoulder VAS {member.vitals.shoulder_pain_score}/10, "
                f"Urinary Ca {member.vitals.urinary_calcium_mg_d:.0f} mg/day"
            )
        else:
            reading = (
                f"BLE Dosimeter Sync: {member.vitals.radiation_msv_h:.2f} mSv/h instantaneous | "
                f"{member.vitals.cumulative_radiation_msv:.1f} mSv cumulative"
            )

        within_baseline, _, _ = evaluate_personal_baseline(member.vitals, member.personal_baseline)
        if member.active_alert and member.active_alert.stabilization_applied and within_baseline and member.scenario_id == "nominal":
            member.active_alert.status = "RESOLVED"
            member.active_alert.verification_measurement_completed = True
            member.active_alert.updated_at = now_iso
            member.active_alert = None
            member.pending_verification_measurement = False
        elif within_baseline and member.scenario_id == "nominal":
            member.active_alert = None
            member.pending_verification_measurement = False

        self._touch(member)
        updated_state = self.get_state(crew_id=member.crew_id)

        if canonical_sys_id == "full_body":
            status = updated_state.clinical_evaluation.overall_status
            sys_name = "Varredura Biomédica Completa (Full-Body Scan)"
            device_used = "Tempus Pro + Astroskin Bio-Monitor + i-STAT"
            guidance = (
                "Sinais vitais confirmados dentro da linha de base individual. Status normalizado com segurança."
                if status == "NOMINAL"
                else "Alterações persistem fora do basal individual; manter protocolo de estabilização e vigilância."
            )
        else:
            sys_eval = updated_state.clinical_evaluation.systems[canonical_sys_id]
            status = sys_eval.status
            sys_name = sys_eval.name
            device_used = sys_eval.checs_device
            guidance = sys_eval.recommended_action

        self.earth_sync.record_audit_event(
            event_type="ACTIVE_MEASUREMENT_TRIGGERED",
            astronaut_id=member.crew_id,
            summary=f"[{sys_name}] {reading}",
            metadata={"system_id": system_id, "status": status},
        )

        return MeasurementResponse(
            system_id=system_id,
            system_name=sys_name,
            device_used=device_used,
            decontamination_required=updated_state.clinical_evaluation.decontamination_required,
            decontamination_checklist=updated_state.clinical_evaluation.decontamination_checklist,
            reading_summary=reading,
            status=status,
            guidance=guidance,
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

    def create_earth_sync_package(self, crew_id: str | None = None) -> EarthSyncPackage:
        state = self.get_state(crew_id=crew_id)
        return self.earth_sync.build_and_queue_package(
            astronaut_id=state.astronaut_id,
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
        pkg = self.create_earth_sync_package(crew_id=crew_id)
        state = self.get_state(crew_id=crew_id)
        env = self.environments_by_id[state.environment_id]
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
        Pillar 6: Triggers the Personalized Psychophysiological Biofeedback Countermeasure.
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

    def _sync_alert_for_member(
        self,
        member: CrewMemberRecord,
        clinical_eval: ClinicalEvaluationResult,
        within_baseline: bool,
        deviations: list[str],
        baseline_severity: SeverityStatus,
    ) -> None:
        effective_severity = max_severity(clinical_eval.overall_status, baseline_severity)
        if effective_severity == "NOMINAL" and within_baseline:
            if (
                member.active_alert
                and member.active_alert.stabilization_applied
                and not member.pending_verification_measurement
            ):
                member.active_alert = None
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        syndrome_code = (
            clinical_eval.syndrome_code
            if clinical_eval.syndrome_code != "nominal"
            else "personal_baseline_deviation"
        )
        target_sys = SYNDROME_TO_SYSTEM.get(syndrome_code, "cardiovascular")
        title = (
            clinical_eval.primary_diagnosis
            if clinical_eval.syndrome_code != "nominal"
            else "Desvio da Linha de Base Individual"
        )
        summary = (
            deviations[0]
            if deviations
            else f"Alteração fisiológica detectada ({clinical_eval.primary_diagnosis})."
        )
        actions = clinical_eval.stabilization_checklist[:4] or [
            "Realizar aferição confirmatória em repouso com dispositivo de bordo.",
            "Aplicar protocolo de estabilização clínica sob supervisão do CMO.",
        ]

        if member.active_alert is None or member.active_alert.status == "RESOLVED":
            member.active_alert = CrewAlertRecord(
                alert_id=f"CREW-ALT-{member.crew_id[:5].upper()}-D{member.mission_day}-{syndrome_code[:5].upper()}",
                crew_id=member.crew_id,
                severity=effective_severity,
                syndrome_code=syndrome_code,
                title=title,
                summary=summary,
                deviations=deviations,
                recommended_actions=actions,
                target_system_id=target_sys,
                status="OPEN",
                stabilization_applied=False,
                verification_measurement_completed=False,
                created_at=now_iso,
                updated_at=now_iso,
                origin="SCENARIO_AUTO",
            )
            member.pending_verification_measurement = True
        elif not member.active_alert.stabilization_applied:
            member.active_alert.severity = effective_severity
            member.active_alert.syndrome_code = syndrome_code
            member.active_alert.title = title
            member.active_alert.summary = summary
            member.active_alert.deviations = deviations
            member.active_alert.recommended_actions = actions
            member.active_alert.target_system_id = target_sys
            member.active_alert.updated_at = now_iso

    def _evaluate_record(
        self, member: CrewMemberRecord, sync_followup: bool = True
    ) -> MissionState:
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

        # Personal Baseline Envelope Evaluation
        within_baseline, baseline_deviations, baseline_severity = evaluate_personal_baseline(
            member.vitals, member.personal_baseline
        )
        self._sync_alert_for_member(
            member, clin_eval, within_baseline, baseline_deviations, baseline_severity
        )

        # Strict normalization rule:
        # Astronaut status only returns to NORMAL after stabilization AND a confirmatory measurement.
        if (
            member.active_alert is not None
            and member.active_alert.status != "RESOLVED"
            and (
                member.pending_verification_measurement
                or member.active_alert.origin in ("EXTERNAL_ALERT", "STABILIZATION_FLOW")
                or member.scenario_id != "nominal"
            )
            and clin_eval.overall_status == "NOMINAL"
        ):
            clin_eval = clin_eval.model_copy(
                update={
                    "overall_status": member.active_alert.severity,
                    "syndrome_code": member.active_alert.syndrome_code,
                    "primary_diagnosis": (
                        f"{member.active_alert.title} (Aguardando Aferição Confirmatória)"
                        if member.active_alert.stabilization_applied
                        else member.active_alert.title
                    ),
                    "stabilization_checklist": member.active_alert.recommended_actions,
                    "notify_crew_onboard": True,
                }
            )

        # 5b. Cross diagnosis: physical vs. NASA DONKI space weather vs. psychological
        sw_for_member = (
            self.space_weather
            if member.crew_id == self.active_crew_id
            else load_sample_donki(simulated=self._scenario_donki(member.scenario_id))
        )
        cross = evaluate_cross_diagnosis(
            vitals=member.vitals,
            context=member.mission_context,
            space_weather=sw_for_member,
            contextual_report=contextual_report,
            clinical=clin_eval,
        )

        # 6. Pillar 3: Sync Explainable Alerts into Closed-Loop Follow-Up Cases
        if sync_followup:
            active_cases = self.followup_manager.sync_alerts(
                alerts=clin_eval.explainable_alerts,
                astronaut_id=member.crew_id,
                astronaut_name=astro_profile["name"],
                mission_day=member.mission_day,
                stabilization_checklist=clin_eval.stabilization_checklist,
            )
        else:
            active_cases = self.followup_manager.list_cases_for_astronaut(member.crew_id)

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
            personal_baseline=member.personal_baseline,
            within_personal_baseline=within_baseline,
            baseline_deviations=baseline_deviations,
            active_alert=member.active_alert,
            pending_verification_measurement=member.pending_verification_measurement,
            last_measured_at=member.last_measured_at,
            measurement_quality=member.measurement_quality,
            mission_context=member.mission_context,
            nutrition=member.nutrition,
            adaptive_baseline=adaptive_base,
            contextual_intelligence=contextual_report,
            clinical_evaluation=clin_eval,
            ml_prediction=ml_pred,
            psych_biofeedback=psych_eval,
            central_psych_alerts=list(reversed(self.psych_engine.central_alerts_history[-10:])),
            explainable_alerts=clin_eval.explainable_alerts,
            followup_cases=active_cases,
            space_weather=sw_for_member,
            cross_diagnosis=cross,
            horizons_link=member.horizons_link,
            earth_sync_queue_count=self.earth_sync.pending_count(),
            earth_sync_last_package_id=last_pkg_id,
            astronauts_catalog=[
                {
                    "astronaut_id": a["astronaut_id"],
                    "name": a["name"],
                    "callsign": a.get(
                        "callsign",
                        DEFAULT_CREW_META.get(a["astronaut_id"], {}).get("callsign", a["astronaut_id"].upper()),
                    ),
                    "role": a["role"],
                    "agency": a["agency"],
                    "mission_group": DEFAULT_CREW_META.get(a["astronaut_id"], {}).get(
                        "mission_group", a.get("mission_group", "INTERNAL")
                    ),
                    "location_module": DEFAULT_CREW_META.get(a["astronaut_id"], {}).get(
                        "location_module", a.get("location_module", "Habitat")
                    ),
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
            last_updated=member.last_updated,
        )

    def get_state(self, crew_id: str | None = None) -> MissionState:
        member = self._member(crew_id)
        return self._evaluate_record(member)

    def get_crew_roster(self) -> CrewRosterResponse:
        summaries: list[CrewMemberSummary] = []
        counts: dict[SeverityStatus, int] = {
            "NOMINAL": 0,
            "ATTENTION": 0,
            "WARNING": 0,
            "CRITICAL": 0,
        }

        for crew_id, member in self.crew_records.items():
            state = self._evaluate_record(member, sync_followup=False)
            status = state.clinical_evaluation.overall_status
            counts[status] = counts.get(status, 0) + 1
            summaries.append(
                CrewMemberSummary(
                    crew_id=crew_id,
                    name=member.name,
                    callsign=member.callsign,
                    role=member.role,
                    mission_group=member.mission_group,
                    location_module=member.location_module,
                    suit_variant=member.suit_variant,
                    environment_id=member.environment_id,
                    environment_name=state.environment_name,
                    scenario_id=member.scenario_id,
                    scenario_name=state.scenario_name,
                    overall_status=status,
                    syndrome_code=state.clinical_evaluation.syndrome_code,
                    within_personal_baseline=state.within_personal_baseline,
                    baseline_deviations=state.baseline_deviations,
                    risk_score=state.ml_prediction.anomaly_score,
                    confidence_pct=state.ml_prediction.confidence_pct,
                    vitals=member.vitals,
                    personal_baseline=member.personal_baseline,
                    active_alert=member.active_alert,
                    pending_verification_measurement=member.pending_verification_measurement,
                    last_measured_at=member.last_measured_at,
                    last_updated=member.last_updated,
                )
            )

        return CrewRosterResponse(
            mission_day=self.mission_day,
            active_crew_id=self.active_crew_id,
            total_crew=len(summaries),
            nominal_count=counts["NOMINAL"],
            attention_count=counts["ATTENTION"],
            warning_count=counts["WARNING"],
            critical_count=counts["CRITICAL"],
            crew=summaries,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
