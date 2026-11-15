from __future__ import annotations

from typing import Any
import numpy as np
from sklearn.covariance import LedoitWolf

from app.models.schemas import (
    AdaptiveBaselineProfile,
    AdaptiveMetricBaseline,
    MissionContext,
    VitalSigns,
)

# Population reference means & stds from NASA-STD-3001 / OSDR astronaut cohort
POPULATION_REFERENCE: dict[str, tuple[str, str, float, float]] = {
    # metric_key: (label, unit, pop_mean, pop_std)
    "heart_rate_bpm": ("Heart Rate", "bpm", 68.0, 8.0),
    "hrv_ms": ("HRV (RMSSD)", "ms", 56.0, 9.5),
    "bp_systolic": ("Systolic BP", "mmHg", 116.0, 9.0),
    "bp_diastolic": ("Diastolic BP", "mmHg", 74.0, 6.0),
    "glucose_mg_dl": ("Blood Glucose", "mg/dL", 93.0, 9.5),
    "temperature_c": ("Core Body Temp", "C", 36.7, 0.30),
    "spo2_pct": ("SpO2 Saturation", "%", 98.2, 1.0),
    "respiration_rpm": ("Respiratory Rate", "rpm", 14.5, 2.0),
    "sleep_hours": ("Sleep Duration", "h", 7.3, 0.75),
    "rem_sleep_pct": ("REM Sleep Share", "%", 21.0, 2.8),
    "mood_score": ("Mood Check-In", "1-5", 4.6, 0.55),
    "stress_index": ("Autonomic Stress Index", "%", 24.0, 10.0),
    "radiation_msv_h": ("Radiation Dose Rate", "mSv/h", 0.04, 0.025),
    "urinary_calcium_mg_d": ("Urinary Calcium (Urolux)", "mg/d", 175.0, 28.0),
    "intraocular_pressure_mmhg": ("Intraocular Pressure (IOP)", "mmHg", 14.8, 1.6),
}

# NASA OSDR OSD-570 / OSD-571 physiological adaptation offsets by gravitational phase
PHASE_ADAPTATION_PRIORS: dict[str, dict[str, float]] = {
    "pre_flight_1g": {k: 0.0 for k in POPULATION_REFERENCE},
    "acute_microgravity_adaptation": {
        "heart_rate_bpm": -3.5,
        "hrv_ms": -4.0,
        "bp_systolic": -6.0,
        "bp_diastolic": -4.0,
        "glucose_mg_dl": 2.0,
        "temperature_c": 0.10,
        "spo2_pct": -0.3,
        "respiration_rpm": 0.5,
        "sleep_hours": -0.8,
        "rem_sleep_pct": -3.0,
        "mood_score": -0.2,
        "stress_index": 6.0,
        "radiation_msv_h": 0.02,
        "urinary_calcium_mg_d": 25.0,
        "intraocular_pressure_mmhg": 3.1,
    },
    "chronic_microgravity_cruise": {
        "heart_rate_bpm": 3.5,
        "hrv_ms": -3.0,
        "bp_systolic": -2.5,
        "bp_diastolic": -2.0,
        "glucose_mg_dl": 3.0,
        "temperature_c": 0.08,
        "spo2_pct": -0.2,
        "respiration_rpm": 0.4,
        "sleep_hours": -0.3,
        "rem_sleep_pct": -1.5,
        "mood_score": -0.1,
        "stress_index": 3.5,
        "radiation_msv_h": 0.03,
        "urinary_calcium_mg_d": 32.0,
        "intraocular_pressure_mmhg": 1.6,
    },
    "lunar_partial_g_016": {
        "heart_rate_bpm": 5.0,
        "hrv_ms": -4.5,
        "bp_systolic": -4.0,
        "bp_diastolic": -2.5,
        "glucose_mg_dl": 1.5,
        "temperature_c": 0.05,
        "spo2_pct": -0.4,
        "respiration_rpm": 0.8,
        "sleep_hours": -0.4,
        "rem_sleep_pct": -1.8,
        "mood_score": -0.1,
        "stress_index": 5.0,
        "radiation_msv_h": 0.03,
        "urinary_calcium_mg_d": 22.0,
        "intraocular_pressure_mmhg": 1.0,
    },
    "martian_partial_g_038": {
        "heart_rate_bpm": 4.0,
        "hrv_ms": -3.5,
        "bp_systolic": -2.0,
        "bp_diastolic": -1.5,
        "glucose_mg_dl": 1.0,
        "temperature_c": 0.04,
        "spo2_pct": -0.3,
        "respiration_rpm": 0.6,
        "sleep_hours": -0.3,
        "rem_sleep_pct": -1.2,
        "mood_score": -0.1,
        "stress_index": 4.0,
        "radiation_msv_h": 0.025,
        "urinary_calcium_mg_d": 18.0,
        "intraocular_pressure_mmhg": 0.7,
    },
}

SERIES_KEY_MAP: dict[str, str] = {
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
}

CORE_MAHALANOBIS_KEYS: list[str] = [
    "heart_rate_bpm",
    "hrv_ms",
    "bp_systolic",
    "bp_diastolic",
    "glucose_mg_dl",
    "temperature_c",
    "sleep_hours",
    "stress_index",
]


class AdaptiveBaselineEngine:
    """
    Pillar 1: Adaptive Individual Baseline Engine.
    Combines pre-flight personal baseline, NASA OSDR gravitational phase priors,
    and rolling EWMA + MAD longitudinal history with Ledoit-Wolf shrunk covariance
    to measure how each astronaut evolves relative to their own physiology.
    """

    def __init__(self, ewma_alpha: float = 0.25) -> None:
        self.ewma_alpha = ewma_alpha
        self._cov_models: dict[tuple[str, str], tuple[np.ndarray, LedoitWolf]] = {}

    def _get_or_fit_personal_covariance(
        self,
        astronaut_id: str,
        mission_phase: str,
        personal_means: np.ndarray,
        personal_stds: np.ndarray,
    ) -> tuple[np.ndarray, LedoitWolf]:
        cache_key = (astronaut_id, mission_phase)
        if cache_key in self._cov_models:
            return self._cov_models[cache_key]

        rng = np.random.default_rng(abs(hash(cache_key)) % (2**31 - 1))
        n_dim = len(CORE_MAHALANOBIS_KEYS)
        # Construct realistic physiological correlation structure (e.g. HR negatively correlated with HRV, positively with stress)
        corr = np.eye(n_dim)
        # 0:hr, 1:hrv, 2:bp_sys, 3:bp_dia, 4:glucose, 5:temp, 6:sleep, 7:stress
        corr[0, 1] = corr[1, 0] = -0.58  # HR vs HRV
        corr[0, 7] = corr[7, 0] = 0.52   # HR vs Stress
        corr[1, 6] = corr[6, 1] = 0.48   # HRV vs Sleep
        corr[1, 7] = corr[7, 1] = -0.62  # HRV vs Stress
        corr[2, 3] = corr[3, 2] = 0.72   # Systolic vs Diastolic BP
        corr[0, 5] = corr[5, 0] = 0.38   # HR vs Core Temp

        D = np.diag(personal_stds)
        cov_matrix = D @ corr @ D
        synthetic_personal_history = rng.multivariate_normal(
            mean=personal_means, cov=cov_matrix, size=180
        )
        lw = LedoitWolf().fit(synthetic_personal_history)
        self._cov_models[cache_key] = (personal_means, lw)
        return personal_means, lw

    def evaluate(
        self,
        astronaut_profile: dict[str, Any],
        vitals: VitalSigns,
        context: MissionContext,
        longitudinal_series: list[dict[str, Any]],
        mission_day: int,
    ) -> AdaptiveBaselineProfile:
        astronaut_id = str(astronaut_profile.get("astronaut_id", "elena_vance"))
        astronaut_name = str(astronaut_profile.get("name", "CDR Elena Vance (EVA-1)"))
        pre_flight = astronaut_profile.get("pre_flight_baseline", {})
        natural_std = astronaut_profile.get("natural_std", {})
        phase = context.mission_phase
        phase_priors = PHASE_ADAPTATION_PRIORS.get(
            phase, PHASE_ADAPTATION_PRIORS["chronic_microgravity_cruise"]
        )

        vitals_dict = vitals.model_dump()
        metrics_out: dict[str, AdaptiveMetricBaseline] = {}

        # Compute per-metric adaptive baseline (Pre-flight + Phase Prior + Rolling EWMA on prior days D-6..D-2)
        prior_days = longitudinal_series[:-1] if len(longitudinal_series) > 1 else longitudinal_series

        for metric_key, (label, unit, pop_mean, pop_std) in POPULATION_REFERENCE.items():
            current_val = float(vitals_dict.get(metric_key, pop_mean))
            pf_base = float(pre_flight.get(metric_key, pop_mean))
            ind_std_prior = float(natural_std.get(metric_key, pop_std * 0.65))
            phase_offset = float(phase_priors.get(metric_key, 0.0))
            phase_adapted = pf_base + phase_offset

            # Rolling EWMA & Robust MAD from early longitudinal window ( anchored to phase_adapted )
            series_field = SERIES_KEY_MAP.get(metric_key)
            hist_vals: list[float] = []
            if series_field and prior_days:
                for row in prior_days[:4]:  # Baseline reference window before acute event peak
                    if series_field in row and row[series_field] is not None:
                        hist_vals.append(float(row[series_field]))

            if hist_vals:
                ewma_val = phase_adapted
                for hv in hist_vals:
                    # Clip extreme outliers when updating rolling baseline so acute pathology doesn't corrupt baseline
                    clipped_hv = float(
                        np.clip(hv, phase_adapted - 2.2 * ind_std_prior, phase_adapted + 2.2 * ind_std_prior)
                    )
                    ewma_val = (1.0 - self.ewma_alpha) * ewma_val + self.ewma_alpha * clipped_hv
                median_val = float(np.median(hist_vals))
                mad = float(np.median(np.abs(np.array(hist_vals) - median_val))) * 1.4826
                rolling_std = max(ind_std_prior * 0.75, min(ind_std_prior * 1.35, 0.7 * ind_std_prior + 0.3 * mad))
            else:
                ewma_val = phase_adapted
                rolling_std = ind_std_prior

            ind_z = (current_val - ewma_val) / max(rolling_std, 1e-6)
            pop_z = (current_val - pop_mean) / max(pop_std, 1e-6)
            dev_pct = ((current_val - ewma_val) / max(abs(ewma_val), 1e-6)) * 100.0

            abs_ind_z = abs(ind_z)
            if abs_ind_z >= 2.5:
                status_vs_personal = "SIGNIFICANT_PERSONAL_DEVIATION"
            elif abs_ind_z >= 1.5:
                status_vs_personal = "MILD_PERSONAL_DRIFT"
            elif abs(current_val - pf_base) / max(ind_std_prior, 1e-6) >= 1.0 and abs_ind_z < 1.5:
                status_vs_personal = "EXPECTED_PHASE_ADAPTATION"
            else:
                status_vs_personal = "WITHIN_PERSONAL_BAND"

            metrics_out[metric_key] = AdaptiveMetricBaseline(
                metric=metric_key,
                label=label,
                unit=unit,
                current_value=round(current_val, 2),
                pre_flight_baseline=round(pf_base, 2),
                phase_expected_offset=round(phase_offset, 2),
                phase_adapted_baseline=round(phase_adapted, 2),
                rolling_ewma_baseline=round(ewma_val, 2),
                rolling_mad_std=round(rolling_std, 2),
                population_baseline=round(pop_mean, 2),
                population_std=round(pop_std, 2),
                individual_z_score=round(ind_z, 2),
                population_z_score=round(pop_z, 2),
                deviation_from_personal_pct=round(dev_pct, 1),
                status_vs_personal=status_vs_personal,
            )

        # Multivariate Mahalanobis distance on core 8 metrics
        p_means = np.array([metrics_out[k].rolling_ewma_baseline for k in CORE_MAHALANOBIS_KEYS], dtype=float)
        p_stds = np.array([metrics_out[k].rolling_mad_std for k in CORE_MAHALANOBIS_KEYS], dtype=float)
        x_curr = np.array([metrics_out[k].current_value for k in CORE_MAHALANOBIS_KEYS], dtype=float)

        _, lw_model = self._get_or_fit_personal_covariance(astronaut_id, phase, p_means, p_stds)
        diff = (x_curr - p_means).reshape(1, -1)
        maha_sq = float((diff @ lw_model.precision_ @ diff.T).item())
        maha_dist = float(np.sqrt(max(0.0, maha_sq)))

        # Map Mahalanobis distance (chi-square df=8, expected nominal ~2.6) to 0..100 personal drift score
        raw_drift = (maha_dist - 1.8) / 8.5 * 100.0
        personal_drift_score = round(float(np.clip(raw_drift, 3.0, 99.5)), 1)

        sig_metrics = [
            m for m in metrics_out.values() if m.status_vs_personal == "SIGNIFICANT_PERSONAL_DEVIATION"
        ]
        is_personally_anomalous = personal_drift_score >= 45.0 or len(sig_metrics) >= 2

        if sig_metrics:
            top_sig = sorted(sig_metrics, key=lambda m: abs(m.individual_z_score), reverse=True)[:3]
            details = ", ".join(
                f"{m.label} ({m.current_value} {m.unit} vs personal {m.rolling_ewma_baseline} {m.unit}, z={m.individual_z_score:+.1f}σ)"
                for m in top_sig
            )
            summary = (
                f"Significant deviation from {astronaut_name}'s phase-adapted baseline ({phase}): {details}. "
                f"Multivariate Mahalanobis distance = {maha_dist:.2f} (Drift Score {personal_drift_score:.1f}%)."
            )
        else:
            summary = (
                f"{astronaut_name}'s biomarkers remain within personal phase-adapted EWMA bounds for {phase} "
                f"(Mahalanobis distance = {maha_dist:.2f}, Drift Score {personal_drift_score:.1f}%)."
            )

        return AdaptiveBaselineProfile(
            astronaut_id=astronaut_id,
            astronaut_name=astronaut_name,
            mission_day=mission_day,
            mission_phase=phase,
            gravitational_g=context.gravitational_g,
            ewma_alpha=self.ewma_alpha,
            history_window_days=len(longitudinal_series),
            multivariate_mahalanobis_distance=round(maha_dist, 2),
            personal_drift_score=personal_drift_score,
            is_personally_anomalous=is_personally_anomalous,
            adaptation_summary=summary,
            metrics=metrics_out,
        )
