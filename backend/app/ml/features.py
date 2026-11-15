"""
Feature set and training cohort for the calibrated ML ensemble.

The cohort is drawn from the same NASA-calibrated stochastic generator that produces the live telemetry
(app/engine/telemetry_generator.py), for every astronaut on the roster and every crisis profile, so the
classifier learns the numbers the system actually emits instead of hand-written means.

Features added on top of the vital signs:
  ctb_reaction_time_ms         Cognition Test Battery reaction time (neurocognitive load)
  sleep_low_nights             consecutive nights < 4.5 h (NASA critical trigger at 2)
  personal_envelope_deviations number of vitals outside the astronaut's personal normal envelope (Crew Hub)
  donki_activity               0 nominal / 1 warning / 2 critical external space weather (NASA DONKI)
  radiation_symptom_flag       crew report compatible with radiation (nausea, light flashes)
  behavioural_symptom_flag     crew report of unusual smell, irritability, insomnia...
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.engine.clinical_rules import build_personal_baseline_from_profile, evaluate_personal_baseline
from app.engine.cross_diagnosis import RADIATION_SYMPTOMS, SENSORY_BEHAVIOURAL, _norm
from app.engine.telemetry_generator import CRISIS_PROFILES, TelemetryGenerator
from app.models.schemas import (
    AdaptiveBaselineProfile,
    MissionContext,
    NutritionHydrationState,
    PersonalBaseline,
    SpaceWeatherSummary,
    VitalSigns,
)

# (key, label, population/in-flight reference mean, reference SD)
FEATURE_SPECS: list[tuple[str, str, float, float]] = [
    ("heart_rate_bpm", "Heart Rate (bpm)", 68.0, 8.0),
    ("hrv_ms", "HRV RMSSD (ms)", 58.0, 9.0),
    ("bp_systolic", "Systolic BP (mmHg)", 116.0, 9.0),
    ("bp_diastolic", "Diastolic BP (mmHg)", 72.0, 6.0),
    ("glucose_mg_dl", "Blood Glucose (mg/dL)", 94.0, 10.0),
    ("temperature_c", "Body Temp (C)", 36.7, 0.35),
    ("spo2_pct", "SpO2 Saturation (%)", 98.2, 1.1),
    ("respiration_rpm", "Respiratory Rate (rpm)", 14.5, 2.2),
    ("sleep_hours", "Sleep Duration (h)", 5.9, 0.6),
    ("mood_score", "Mood Check-In (1-5)", 4.3, 0.6),
    ("radiation_msv_h", "Radiation Rate (mSv/h)", 0.031, 0.01),
    ("ctb_reaction_time_ms", "CTB Reaction Time (ms)", 275.0, 20.0),
    ("sleep_low_nights", "Nights < 4.5 h in a row", 0.0, 1.0),
    ("nutrition_goal_pct", "Nutrition Goal (%)", 88.0, 12.0),
    ("minutes_since_last_exercise", "Time Since Exercise (min)", 300.0, 140.0),
    ("cabin_co2_mmhg", "Cabin CO2 (mmHg)", 2.5, 0.6),
    ("personal_envelope_deviations", "Personal Envelope Deviations", 0.0, 1.0),
    ("donki_activity", "NASA DONKI Space Weather Level", 0.0, 0.5),
    ("radiation_symptom_flag", "Radiation-Compatible Symptom Report", 0.0, 0.3),
    ("behavioural_symptom_flag", "Behavioural / Sensory Symptom Report", 0.0, 0.3),
    ("individual_hr_z_score", "Personal HR Drift (z-score)", 0.0, 1.0),
    ("individual_hrv_z_score", "Personal HRV Drift (z-score)", 0.0, 1.0),
]
FEATURE_KEYS = [k for k, *_ in FEATURE_SPECS]
DERIVED_KEYS = {"individual_hr_z_score", "individual_hrv_z_score"}

_DONKI_LEVEL = {"NOMINAL": 0.0, "WARNING": 1.0, "CRITICAL": 2.0}


def symptom_flags(reported: list[str]) -> tuple[float, float]:
    text = _norm(" | ".join(reported))
    return float(bool(RADIATION_SYMPTOMS.search(text))), float(bool(SENSORY_BEHAVIOURAL.search(text)))


def feature_vector(
    vitals: VitalSigns,
    nutrition: NutritionHydrationState,
    context: MissionContext,
    ind_hr_z: float,
    ind_hrv_z: float,
    personal_baseline: PersonalBaseline | None = None,
    space_weather: SpaceWeatherSummary | None = None,
) -> list[float]:
    nutrition_pct = min(130.0, max(10.0, nutrition.calories_kcal / max(nutrition.goal_calories_kcal, 1.0) * 100.0))
    deviations = 0
    if personal_baseline is not None:
        _, devs, _ = evaluate_personal_baseline(vitals, personal_baseline)
        deviations = len(devs)
    rad_flag, beh_flag = symptom_flags(vitals.reported_symptoms)
    return [
        vitals.heart_rate_bpm,
        vitals.hrv_ms,
        vitals.bp_systolic,
        vitals.bp_diastolic,
        vitals.glucose_mg_dl,
        vitals.temperature_c,
        vitals.spo2_pct,
        vitals.respiration_rpm,
        vitals.sleep_hours,
        float(vitals.mood_score),
        vitals.radiation_msv_h,
        vitals.ctb_reaction_time_ms,
        float(vitals.sleep_streak_low_days),
        nutrition_pct,
        context.minutes_since_last_exercise,
        context.cabin_co2_mmhg,
        float(deviations),
        _DONKI_LEVEL.get(space_weather.alert_level, 0.0) if space_weather else 0.0,
        rad_flag,
        beh_flag,
        ind_hr_z,
        ind_hrv_z,
    ]


def live_feature_vector(
    vitals: VitalSigns,
    nutrition: NutritionHydrationState,
    context: MissionContext,
    adaptive_baseline: AdaptiveBaselineProfile,
    personal_baseline: PersonalBaseline | None,
    space_weather: SpaceWeatherSummary | None,
) -> np.ndarray:
    return np.array(
        [
            feature_vector(
                vitals,
                nutrition,
                context,
                adaptive_baseline.metrics["heart_rate_bpm"].individual_z_score,
                adaptive_baseline.metrics["hrv_ms"].individual_z_score,
                personal_baseline,
                space_weather,
            )
        ],
        dtype=float,
    )


def build_generator_cohort(
    catalog: dict[str, Any], days_per_case: int = 24, seed: int = 42
) -> tuple[np.ndarray, np.ndarray, int]:
    """Training set: every roster astronaut x every crisis profile x `days_per_case` mission days.

    Context (exercise timing, cabin CO2, intake), DONKI level and crew symptom reports are jittered so the
    model cannot memorise a scenario from a single constant field. Storm drills mostly carry an active
    DONKI event, but other crises also see random solar activity: DONKI alone must not decide the class.
    """
    rng = np.random.default_rng(seed)
    scenarios = {s["id"]: s for s in catalog.get("scenarios", [])}
    profiles = catalog.get("astronaut_profiles", [])
    X: list[list[float]] = []
    y: list[str] = []

    for profile in profiles:
        envelope = build_personal_baseline_from_profile(profile)
        for crisis in CRISIS_PROFILES:
            sc = scenarios.get(crisis, scenarios.get("nominal", {}))
            ctx_raw = dict(sc.get("mission_context", {}))
            gen = TelemetryGenerator(profile, ctx_raw.get("mission_phase", "chronic_microgravity_cruise"))
            for k in range(days_per_case):
                day = 100 + 3 * k
                if crisis == "nominal" or k % 2 == 0:
                    vitals_d, _ = gen.generate(crisis, day)  # full-blown state, as the live system shows it
                else:
                    # early / prodromal reading (15-100 % of the way): overlaps normal variability on purpose,
                    # so validation metrics stay honest and the model learns early detection
                    vitals_d = gen.reading_at_progress(crisis, float(rng.uniform(0.15, 1.0)), day, rng)

                rad_symptom = rng.random() < (0.75 if crisis == "solar_storm" else 0.03)
                beh_symptom = rng.random() < (0.7 if crisis == "behavioral_fatigue" else 0.04)
                vitals_d["reported_symptoms"] = (["light flashes"] if rad_symptom else []) + (
                    ["irritability"] if beh_symptom else []
                )
                vitals = VitalSigns(**vitals_d)

                # Context is informative only where it is the cause (exercise, CO2 pocket, caloric deficit).
                # Elsewhere it is drawn from the nominal mission distribution: otherwise each scenario's fixed
                # context leaks the label and the model "recognises the scenario" instead of the physiology.
                ctx = MissionContext(**ctx_raw)
                if crisis == "post_exercise_physiological":
                    ctx.minutes_since_last_exercise = float(rng.uniform(5, 45))
                else:
                    ctx.minutes_since_last_exercise = float(rng.uniform(90, 900))
                ctx.cabin_co2_mmhg = float(
                    rng.uniform(3.6, 5.2) if crisis == "cabin_co2_pocket" else max(1.2, rng.normal(2.5, 0.35))
                )
                nut = NutritionHydrationState(**scenarios["nominal"]["nutrition"])
                goal = nut.goal_calories_kcal
                nut.calories_kcal = float(goal * (rng.uniform(0.25, 0.55) if crisis == "hypoglycemia" else rng.uniform(0.6, 1.1)))

                if crisis == "solar_storm":
                    level = "CRITICAL" if rng.random() < 0.85 else "WARNING"
                else:
                    r = rng.random()
                    level = "CRITICAL" if r < 0.05 else ("WARNING" if r < 0.2 else "NOMINAL")
                sw = SpaceWeatherSummary(
                    source="curated_local_fallback", fetched_at="", alert_level=level, active_flare_count=0,
                    active_sep_count=0, recommended_dose_limit_msv_h=0.5, alara_instruction="",
                )

                hr_z = (vitals.heart_rate_bpm - gen.centre("heart_rate_bpm")) / max(gen.std("heart_rate_bpm"), 1e-6)
                hrv_z = (vitals.hrv_ms - gen.centre("hrv_ms")) / max(gen.std("hrv_ms"), 1e-6)
                X.append(feature_vector(vitals, nut, ctx, hr_z, hrv_z, envelope, sw))
                y.append(crisis)

    return np.array(X, dtype=float), np.array(y), len(profiles)
