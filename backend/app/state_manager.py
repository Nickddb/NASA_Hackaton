from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.engine.clinical_rules import evaluate_clinical_rules, load_scenarios_catalog
from app.engine.ml_predictor import AstraCareMLPredictor
from app.engine.nasa_donki import _load_sample_donki, fetch_nasa_space_weather
from app.models.schemas import (
    LoggedFoodItem,
    MeasurementResponse,
    MissionState,
    NutritionHydrationState,
    SpaceWeatherSummary,
    TelemedicineDossier,
    VitalSigns,
)


class MissionStateManager:
    """In-memory mission medical telemetry store with instant Layer 1 + Layer 2 re-evaluation."""

    def __init__(self) -> None:
        self.catalog: dict[str, Any] = load_scenarios_catalog()
        self.ml_predictor = AstraCareMLPredictor()
        self.scenarios_by_id: dict[str, dict[str, Any]] = {
            s["id"]: s for s in self.catalog.get("scenarios", [])
        }
        self.environments_by_id: dict[str, dict[str, Any]] = {
            e["id"]: e for e in self.catalog.get("environments", [])
        }

        self.scenario_id: str = "nominal"
        self.environment_id: str = "transit"
        self.mission_day: int = 142
        self.crew_member: str = "CDR Elena Vance (EVA-1)"
        self.vitals: VitalSigns = VitalSigns(**self.scenarios_by_id["nominal"]["vitals"])
        self.nutrition: NutritionHydrationState = NutritionHydrationState(
            **self.scenarios_by_id["nominal"]["nutrition"]
        )
        self.longitudinal_series: list[dict[str, Any]] = list(
            self.scenarios_by_id["nominal"].get("longitudinal_series", [])
        )
        self.space_weather: SpaceWeatherSummary | None = _load_sample_donki()
        self.last_updated: str = datetime.now(timezone.utc).isoformat()

    def _touch(self) -> None:
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def switch_scenario(self, scenario_id: str) -> MissionState:
        if scenario_id not in self.scenarios_by_id:
            raise KeyError(f"Unknown scenario_id: {scenario_id}")
        sc = self.scenarios_by_id[scenario_id]
        self.scenario_id = scenario_id
        self.mission_day = int(sc.get("mission_day", 142))
        self.vitals = VitalSigns(**sc["vitals"])
        self.nutrition = NutritionHydrationState(**sc["nutrition"])
        self.longitudinal_series = list(sc.get("longitudinal_series", []))
        self._touch()
        return self.get_state()

    def switch_environment(self, env_id: str) -> MissionState:
        if env_id not in self.environments_by_id:
            raise KeyError(f"Unknown environment_id: {env_id}")
        self.environment_id = env_id
        self._touch()
        return self.get_state()

    def trigger_measurement(self, system_id: str) -> MeasurementResponse:
        eval_res = evaluate_clinical_rules(self.vitals, self.nutrition, self.environment_id, self.catalog)
        if system_id not in eval_res.systems:
            raise KeyError(f"Unknown system_id: {system_id}")

        # Slight realistic sensor refresh micro-jitter while preserving clinical state
        if system_id == "cardiovascular":
            self.vitals.heart_rate_bpm = round(self.vitals.heart_rate_bpm + 1.0 if self.vitals.heart_rate_bpm < 110 else self.vitals.heart_rate_bpm - 1.0, 1)
            reading = f"PPG/NIBP Sync: {self.vitals.heart_rate_bpm:.0f} bpm, HRV {self.vitals.hrv_ms:.0f} ms, BP {self.vitals.bp_systolic:.0f}/{self.vitals.bp_diastolic:.0f} mmHg"
        elif system_id == "nervous_sleep":
            reading = f"EEG/Actigraphy + IOP: Sleep {self.vitals.sleep_hours:.1f}h (REM {self.vitals.rem_sleep_pct:.0f}%), Mood {self.vitals.mood_score}/5, IOP {self.vitals.intraocular_pressure_mmhg:.1f} mmHg"
        elif system_id == "respiratory":
            reading = f"Tempus Pro Capnography/IR: SpO2 {self.vitals.spo2_pct:.1f}%, RR {self.vitals.respiration_rpm:.0f} rpm, Temp {self.vitals.temperature_c:.1f} C"
        elif system_id == "metabolic":
            reading = f"i-STAT/CGM Check: Glucose {self.vitals.glucose_mg_dl:.0f} mg/dL | Intake {self.nutrition.calories_kcal:.0f}/{self.nutrition.goal_calories_kcal:.0f} kcal, {self.nutrition.water_ml:.0f} ml H2O"
        elif system_id == "musculoskeletal":
            reading = f"EVA Shoulder & Urolux Scan: Shoulder VAS {self.vitals.shoulder_pain_score}/10, Urinary Ca {self.vitals.urinary_calcium_mg_d:.0f} mg/day"
        else:
            reading = f"BLE Dosimeter Sync: {self.vitals.radiation_msv_h:.2f} mSv/h instantaneous | {self.vitals.cumulative_radiation_msv:.1f} mSv cumulative"

        self._touch()
        updated_state = self.get_state()
        sys_eval = updated_state.clinical_evaluation.systems[system_id]

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

        # Physiological glucose & hydration coupling
        if carbs_g > 0 and self.vitals.glucose_mg_dl < 85:
            self.vitals.glucose_mg_dl = round(min(104.0, self.vitals.glucose_mg_dl + carbs_g * 0.65), 1)
        if water_ml >= 300 and self.vitals.bp_systolic < 96 and self.scenario_id == "orthostatic_intolerance":
            self.vitals.bp_systolic = round(min(108.0, self.vitals.bp_systolic + 8.0), 1)
            self.vitals.bp_diastolic = round(min(70.0, self.vitals.bp_diastolic + 5.0), 1)
            self.vitals.heart_rate_bpm = round(max(82.0, self.vitals.heart_rate_bpm - 10.0), 1)

        if self.longitudinal_series:
            self.longitudinal_series[-1]["glucose"] = round(self.vitals.glucose_mg_dl, 1)
            self.longitudinal_series[-1]["hr"] = round(self.vitals.heart_rate_bpm, 1)

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

        self._touch()
        return self.get_state()

    async def refresh_space_weather(self) -> SpaceWeatherSummary:
        self.space_weather = await fetch_nasa_space_weather()
        self._touch()
        return self.space_weather

    def compile_dossier(self) -> TelemedicineDossier:
        state = self.get_state()
        env = self.environments_by_id[self.environment_id]
        latency = int(env.get("one_way_latency_seconds", 720))
        tx_mode = (
            "Asynchronous Store-and-Forward Video + Telemetry Bundle (Mars/Deep Space Delay)"
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
            f"{f.label}: {f.current_value} ({f.importance:.0f}%)"
            for f in state.ml_prediction.feature_importances[:3]
        )
        sw_note = (
            state.space_weather.alara_instruction
            if state.space_weather
            else "NASA DONKI solar weather feed pending sync; personal BLE dosimeter active."
        )

        questions = [
            "Confirm recommended CHeCS medical kit pharmacological dosage adjustment based on latest i-STAT electrolytes.",
            "Authorize return-to-EVA timeline vs. temporary mission task suspension per OCHMO-TB-044 MORD.",
        ]
        if state.clinical_evaluation.systems["musculoskeletal"].status != "NOMINAL":
            questions.append("Review portable musculoskeletal ultrasound clips for EVA HUT rotator-cuff impingement (OCHMO-MTB-006).")
        if state.vitals.pfo_decompression_risk != "LOW":
            questions.append("Confirm extended 4h O2 prebreathe or Campout 10.2 psia protocol prior to next EVA (OCHMO-MTB-011).")

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
                f"Primary Clinical Assessment: {state.clinical_evaluation.primary_diagnosis}. "
                f"ML IsolationForest Anomaly Score: {state.ml_prediction.anomaly_score:.1f}% "
                f"(RF Confidence {state.ml_prediction.confidence_pct:.1f}%). Top drivers: {top_drivers}."
            ),
            clinical_evaluation=state.clinical_evaluation,
            ml_prediction=state.ml_prediction,
            vitals_snapshot=state.vitals,
            nutrition_snapshot=state.nutrition,
            space_weather_alert=sw_note,
            recommended_earth_questions=questions,
        )

    def get_state(self) -> MissionState:
        sc = self.scenarios_by_id[self.scenario_id]
        env = self.environments_by_id[self.environment_id]
        clinical_eval = evaluate_clinical_rules(self.vitals, self.nutrition, self.environment_id, self.catalog)
        ml_pred = self.ml_predictor.predict(self.vitals, self.nutrition)

        scenarios_catalog = [
            {
                "id": s["id"],
                "name": s["name"],
                "short_label": s["short_label"],
                "severity": s["severity"],
                "description": s["description"],
            }
            for s in self.catalog.get("scenarios", [])
        ]
        environments_catalog = [
            {
                "id": e["id"],
                "name": e["name"],
                "short_label": e["short_label"],
                "gravity": e["gravity"],
                "one_way_latency_seconds": e["one_way_latency_seconds"],
                "latency_label": e["latency_label"],
                "protocol_focus": e["protocol_focus"],
                "decontamination_required": e["decontamination_required"],
            }
            for e in self.catalog.get("environments", [])
        ]

        return MissionState(
            mission_day=self.mission_day,
            crew_member=self.crew_member,
            scenario_id=self.scenario_id,
            scenario_name=sc["name"],
            scenario_description=sc["description"],
            environment_id=self.environment_id,
            environment_name=env["name"],
            one_way_latency_seconds=int(env["one_way_latency_seconds"]),
            vitals=self.vitals.model_copy(deep=True),
            nutrition=self.nutrition.model_copy(deep=True),
            clinical_evaluation=clinical_eval,
            ml_prediction=ml_pred,
            space_weather=self.space_weather,
            longitudinal_series=self.longitudinal_series,
            scenarios_catalog=scenarios_catalog,
            environments_catalog=environments_catalog,
            indicators_guide=self.catalog.get("indicators_guide", []),
            systems_guide=self.catalog.get("systems_guide", {}),
            last_updated=self.last_updated,
        )


def ensure_space_weather_sync(manager: MissionStateManager) -> SpaceWeatherSummary:
    if manager.space_weather is not None:
        return manager.space_weather
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            from app.engine.nasa_donki import _load_sample_donki
            manager.space_weather = _load_sample_donki()
            return manager.space_weather
    except RuntimeError:
        pass
    manager.space_weather = asyncio.run(fetch_nasa_space_weather())
    return manager.space_weather
