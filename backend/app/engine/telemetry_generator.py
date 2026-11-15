"""
Stochastic telemetry generator calibrated on NASA in-flight ranges (see nasa_calibration.py).

Replaces the static vitals/series that used to live in scenarios.json. For each astronaut it draws:
  * a nominal centre per metric = personal pre-flight baseline + gravitational phase prior,
    clamped to the NASA in-flight nominal range;
  * gaussian day-to-day noise scaled by the astronaut's own natural variability;
  * an optional crisis profile that ramps selected metrics toward values past the NASA critical triggers
    over the last N days (slow drift) or only today (acute step).

Generation is reproducible: the same astronaut + crisis + mission day always yields the same series,
so tests and demos are stable, while `next_reading` keeps producing fresh noisy readings.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.engine import nasa_calibration as cal
from app.ml.adaptive_baseline import PHASE_ADAPTATION_PRIORS

SERIES_FIELDS: dict[str, str] = {
    "heart_rate_bpm": "hr",
    "hrv_ms": "hrv",
    "bp_systolic": "bp_sys",
    "bp_diastolic": "bp_dia",
    "temperature_c": "temp",
    "spo2_pct": "spo2",
    "respiration_rpm": "rr",
    "glucose_mg_dl": "glucose",
    "sleep_hours": "sleep",
    "rem_sleep_pct": "rem",
    "radiation_msv_h": "radiation",
    "mood_score": "mood",
    "stress_index": "stress",
    "ctb_reaction_time_ms": "ctb",
}

# Fallback personal variability when a profile does not define one (approx. population SD x 0.65)
DEFAULT_STD: dict[str, float] = {
    "heart_rate_bpm": 4.5,
    "hrv_ms": 5.5,
    "bp_systolic": 5.0,
    "bp_diastolic": 3.8,
    "temperature_c": 0.15,
    "spo2_pct": 0.5,
    "respiration_rpm": 1.1,
    "glucose_mg_dl": 5.5,
    "sleep_hours": 0.35,
    "rem_sleep_pct": 1.8,
    "radiation_msv_h": 0.004,
    "mood_score": 0.35,
    "stress_index": 6.0,
    "ctb_reaction_time_ms": 12.0,
    "urinary_calcium_mg_d": 15.0,
    "intraocular_pressure_mmhg": 0.9,
}

# Physiological hard bounds so noise can never produce impossible values
HARD_BOUNDS: dict[str, tuple[float, float]] = {
    "heart_rate_bpm": (30, 190),
    "hrv_ms": (8, 140),
    "bp_systolic": (60, 200),
    "bp_diastolic": (35, 130),
    "temperature_c": (34.5, 41.5),
    "spo2_pct": (80, 100),
    "respiration_rpm": (6, 40),
    "glucose_mg_dl": (40, 350),
    "sleep_hours": (1.5, 10),
    "rem_sleep_pct": (5, 35),
    "radiation_msv_h": (0.005, 5.0),
    "mood_score": (1, 5),
    "stress_index": (0, 100),
    "ctb_reaction_time_ms": (180, 700),
    "urinary_calcium_mg_d": (80, 400),
    "intraocular_pressure_mmhg": (8, 30),
}

REF_NOMINAL_RANGE = {k: cal.NOMINAL[k] for k in cal.NOMINAL if k in HARD_BOUNDS}

# Metrics with no pre-flight value in the astronaut profile fall back to these in-flight centres
DEFAULT_CENTRE = {
    "ctb_reaction_time_ms": cal.NOMINAL["ctb_reaction_time_ms"].mid,
    "spo2_pct": 98.2,
    "rem_sleep_pct": 20.0,
}


@dataclass(frozen=True)
class CrisisProfile:
    """Targets reached on the current day; ramp_days=1 means an acute same-day change."""

    targets: dict[str, float]
    ramp_days: int = 5
    shape: float = 1.4  # >1 accelerating drift, 1 linear
    extras: dict[str, Any] = field(default_factory=dict)
    extra_cumulative_msv: float = 0.0


# Targets sit past the NASA critical triggers in nasa_calibration so the rules fire for the right reason.
CRISIS_PROFILES: dict[str, CrisisProfile] = {
    "nominal": CrisisProfile(targets={}, ramp_days=1),
    "systemic_infection": CrisisProfile(
        targets={
            "temperature_c": 38.6, "heart_rate_bpm": 108, "hrv_ms": 26, "bp_systolic": 98, "bp_diastolic": 60,
            "spo2_pct": 94.6, "respiration_rpm": 22, "sleep_hours": 4.9, "mood_score": 3, "stress_index": 70,
            "glucose_mg_dl": 116, "ctb_reaction_time_ms": 330,
        },
        ramp_days=5,
    ),
    "orthostatic_intolerance": CrisisProfile(
        targets={
            "bp_systolic": 84, "bp_diastolic": 54, "heart_rate_bpm": 110, "hrv_ms": 34, "respiration_rpm": 19,
            "stress_index": 58, "intraocular_pressure_mmhg": 18.4, "urinary_calcium_mg_d": 235,
        },
        ramp_days=4,
        extras={"pfo_decompression_risk": "MODERATE", "shoulder_pain_score": 2},
    ),
    # Psychological / neurocognitive overload with NO physical or external cause
    "behavioral_fatigue": CrisisProfile(
        targets={
            "sleep_hours": 3.9, "mood_score": 2, "ctb_reaction_time_ms": 415, "stress_index": 82,
            "hrv_ms": 32, "rem_sleep_pct": 12,
        },
        ramp_days=6,
        shape=1.2,
    ),
    "hypoglycemia": CrisisProfile(
        targets={"glucose_mg_dl": 58, "heart_rate_bpm": 102, "temperature_c": 36.4, "stress_index": 62, "hrv_ms": 38},
        ramp_days=3,
        extras={"shoulder_pain_score": 6},
    ),
    # Radiation spike: needs a DONKI SEP/FLR/RBE event to be attributed to an external cause
    "solar_storm": CrisisProfile(
        targets={"radiation_msv_h": 0.68, "heart_rate_bpm": 92, "stress_index": 68, "mood_score": 3},
        ramp_days=2,
        shape=2.5,
        extra_cumulative_msv=22.0,
    ),
    "post_exercise_physiological": CrisisProfile(
        targets={"heart_rate_bpm": 106, "temperature_c": 37.6, "hrv_ms": 36, "bp_systolic": 134, "respiration_rpm": 20},
        ramp_days=1,
    ),
    "cabin_co2_pocket": CrisisProfile(
        targets={
            "respiration_rpm": 21, "spo2_pct": 95.2, "bp_systolic": 132, "bp_diastolic": 84, "sleep_hours": 5.3,
            "intraocular_pressure_mmhg": 17.8, "stress_index": 56, "hrv_ms": 39,
        },
        ramp_days=5,
    ),
}


def _stable_seed(*parts: Any) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:8], 16)


class TelemetryGenerator:
    """Generates calibrated vitals and a daily longitudinal series for one astronaut and mission phase."""

    def __init__(self, astronaut_profile: dict[str, Any], mission_phase: str) -> None:
        self.profile = astronaut_profile
        self.astronaut_id = str(astronaut_profile.get("astronaut_id", "unknown"))
        self.mission_phase = mission_phase
        self._pre = astronaut_profile.get("pre_flight_baseline", {})
        self._std = astronaut_profile.get("natural_std", {})
        self._prior = PHASE_ADAPTATION_PRIORS.get(mission_phase, PHASE_ADAPTATION_PRIORS["chronic_microgravity_cruise"])

    # ---------- per-metric parameters ----------
    def centre(self, metric: str) -> float:
        base = self._pre.get(metric)
        if base is None:
            base = DEFAULT_CENTRE.get(metric, REF_NOMINAL_RANGE[metric].mid if metric in REF_NOMINAL_RANGE else 0.0)
        value = float(base) + float(self._prior.get(metric, 0.0))
        rng = REF_NOMINAL_RANGE.get(metric)
        # On Earth (pre-flight) the in-flight ranges do not apply
        if rng is not None and self.mission_phase != "pre_flight_1g":
            value = rng.clamp(value)
        return value

    def std(self, metric: str) -> float:
        return float(self._std.get(metric, DEFAULT_STD.get(metric, 1.0)))

    @staticmethod
    def _bound(metric: str, value: float) -> float:
        lo, hi = HARD_BOUNDS.get(metric, (-1e9, 1e9))
        return float(min(hi, max(lo, value)))

    # ---------- generation ----------
    def _value(self, metric: str, weight: float, crisis: CrisisProfile, rng: np.random.Generator, noise_k: float) -> float:
        c = self.centre(metric)
        target = crisis.targets.get(metric)
        mean = c + weight * (target - c) if target is not None else c
        # Metrics driven by the crisis get half the noise: a crisis target sits just past a NASA trigger and
        # full noise would randomly push it back to the nominal side, making scenarios flaky.
        sd = self.std(metric) * noise_k * (0.5 if target is not None and weight > 0 else 1.0)
        return self._bound(metric, rng.normal(mean, sd))

    def generate(self, crisis_id: str, mission_day: int, days: int = 7) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        crisis = CRISIS_PROFILES.get(crisis_id, CRISIS_PROFILES["nominal"])
        rng = np.random.default_rng(_stable_seed(self.astronaut_id, crisis_id, mission_day, self.mission_phase))
        start = days - crisis.ramp_days

        series: list[dict[str, Any]] = []
        for d in range(days):
            w = 0.0 if d < start else ((d - start + 1) / crisis.ramp_days) ** crisis.shape
            row: dict[str, Any] = {"day": "Today" if d == days - 1 else f"D-{days - 1 - d}"}
            for metric, key in SERIES_FIELDS.items():
                v = self._value(metric, w, crisis, rng, noise_k=0.6)
                row[key] = int(round(v)) if metric == "mood_score" else round(v, 3 if metric == "radiation_msv_h" else 1)
            series.append(row)

        vitals = self._vitals_from_today(series, crisis, rng, mission_day)
        return vitals, series

    def _vitals_from_today(
        self, series: list[dict[str, Any]], crisis: CrisisProfile, rng: np.random.Generator, mission_day: int
    ) -> dict[str, Any]:
        today = series[-1]
        vitals: dict[str, Any] = {metric: today[key] for metric, key in SERIES_FIELDS.items()}
        vitals["mood_score"] = int(min(5, max(1, round(vitals["mood_score"]))))

        streak = 0
        for row in reversed(series):
            if row["sleep"] < cal.SLEEP_CRIT_H:
                streak += 1
            else:
                break
        vitals["sleep_streak_low_days"] = streak

        for metric in ("urinary_calcium_mg_d", "intraocular_pressure_mmhg"):
            vitals[metric] = round(self._value(metric, 1.0, crisis, rng, noise_k=0.5), 1)

        # Cumulative dose: mission days at the nominal transit daily dose + any SPE contribution
        daily_dose = cal.NOMINAL["radiation_msv_h"].mid * 24.0
        vitals["cumulative_radiation_msv"] = round(mission_day * daily_dose + crisis.extra_cumulative_msv, 1)
        vitals["shoulder_pain_score"] = int(crisis.extras.get("shoulder_pain_score", 0))
        vitals["pfo_decompression_risk"] = crisis.extras.get("pfo_decompression_risk", "LOW")
        vitals["reported_symptoms"] = []
        return vitals

    def reading_at_progress(
        self, crisis_id: str, progress: float, mission_day: int, rng: np.random.Generator
    ) -> dict[str, Any]:
        """A single reading part-way through a crisis (progress 0 = nominal, 1 = full crisis). Used to train
        the ML on early/prodromal states that overlap with normal variability."""
        crisis = CRISIS_PROFILES.get(crisis_id, CRISIS_PROFILES["nominal"])
        vitals: dict[str, Any] = {}
        for metric in SERIES_FIELDS:
            v = self._value(metric, progress, crisis, rng, noise_k=0.6)
            vitals[metric] = round(v, 3 if metric == "radiation_msv_h" else 1)
        vitals["mood_score"] = int(min(5, max(1, round(vitals["mood_score"]))))
        short = vitals["sleep_hours"] < cal.SLEEP_CRIT_H
        vitals["sleep_streak_low_days"] = int(short) + int(short and rng.random() < progress)
        for metric in ("urinary_calcium_mg_d", "intraocular_pressure_mmhg"):
            vitals[metric] = round(self._value(metric, progress, crisis, rng, noise_k=0.5), 1)
        daily = cal.NOMINAL["radiation_msv_h"].mid * 24.0
        vitals["cumulative_radiation_msv"] = round(mission_day * daily + progress * crisis.extra_cumulative_msv, 1)
        vitals["shoulder_pain_score"] = int(crisis.extras.get("shoulder_pain_score", 0)) if progress > 0.5 else 0
        vitals["pfo_decompression_risk"] = crisis.extras.get("pfo_decompression_risk", "LOW") if progress > 0.5 else "LOW"
        vitals["reported_symptoms"] = []
        return vitals

    def next_reading(self, crisis_id: str, current: dict[str, Any], rng: np.random.Generator) -> dict[str, Any]:
        """A fresh instantaneous reading for 'today': same trajectory, new sensor noise."""
        crisis = CRISIS_PROFILES.get(crisis_id, CRISIS_PROFILES["nominal"])
        updated = dict(current)
        for metric in SERIES_FIELDS:
            if metric in ("sleep_hours", "rem_sleep_pct", "mood_score"):
                continue  # once-a-day measures do not change between readings
            updated[metric] = round(
                self._value(metric, 1.0, crisis, rng, noise_k=0.35), 3 if metric == "radiation_msv_h" else 1
            )
        return updated
