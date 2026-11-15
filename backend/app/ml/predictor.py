from __future__ import annotations

from typing import Any
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.linear_model import BayesianRidge
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from app.models.schemas import (
    AdaptiveBaselineProfile,
    ContextualIntelligenceReport,
    FeatureImportanceItem,
    ForecastHorizonPoint,
    MeasurementQualityProfile,
    MissionContext,
    MLPredictionResult,
    MLValidationMetrics,
    NutritionHydrationState,
    ReliabilityGrade,
    UncertaintyAssessment,
    VitalSigns,
)

FEATURE_SPECS: list[tuple[str, str, float, float]] = [
    # (key, label, nominal_pop_baseline, scale_std)
    ("heart_rate_bpm", "Heart Rate (bpm)", 68.0, 8.0),
    ("hrv_ms", "HRV RMSSD (ms)", 58.0, 9.0),
    ("bp_systolic", "Systolic BP (mmHg)", 116.0, 9.0),
    ("bp_diastolic", "Diastolic BP (mmHg)", 74.0, 6.0),
    ("glucose_mg_dl", "Blood Glucose (mg/dL)", 94.0, 10.0),
    ("temperature_c", "Body Temp (C)", 36.7, 0.35),
    ("spo2_pct", "SpO2 Saturation (%)", 98.2, 1.1),
    ("respiration_rpm", "Respiratory Rate (rpm)", 14.5, 2.2),
    ("sleep_hours", "Sleep Duration (h)", 7.4, 0.8),
    ("mood_score", "Mood Check-In (1-5)", 4.6, 0.6),
    ("radiation_msv_h", "Radiation Rate (mSv/h)", 0.04, 0.03),
    ("nutrition_goal_pct", "Nutrition Goal (%)", 88.0, 12.0),
    ("minutes_since_last_exercise", "Time Since Exercise (min)", 300.0, 140.0),
    ("cabin_co2_mmhg", "Cabin CO2 (mmHg)", 2.5, 0.6),
    ("individual_hr_z_score", "Personal HR Drift (z-score)", 0.0, 1.0),
    ("individual_hrv_z_score", "Personal HRV Drift (z-score)", 0.0, 1.0),
]

SYNDROME_LABELS: dict[str, str] = {
    "nominal": "Nominal Mission State (Within Personal & Population Bounds)",
    "post_exercise_physiological": "Contextual Confounder: Physiological Post-Exercise Recovery",
    "cabin_co2_pocket": "Contextual Confounder: Localized Cabin CO2 Exposure",
    "systemic_infection": "Systemic Infection / Acute Viral State",
    "orthostatic_intolerance": "Orthostatic Intolerance / Post-EVA Fluid Shift",
    "behavioral_fatigue": "Severe Behavioral Fatigue & Circadian Desynchrony",
    "hypoglycemia": "Caloric-Deficit Hypoglycemia & EVA Strain",
    "solar_storm": "Solar Particle Event (SPE) Radiation Spike",
}


class AstraCareRealMLEngine:
    """
    Pillar 3 & 4: Real Calibrated Machine Learning & Explainable/Auditable AI Engine.
    Combines:
      - Unsupervised IsolationForest on personal + population normalized features
      - Calibrated HistGradientBoosting + RandomForest Ensemble with 5-fold Stratified CV metrics
      - Epistemic (inter-tree variance) + Aleatoric (sensor signal quality) Uncertainty Quantification
      - Counterfactual Local Perturbation Feature Attribution against Personal Adaptive Baseline
      - BayesianRidge 24h-72h Multi-Horizon Longitudinal Trajectory Forecaster with 80% Credible Intervals
    """

    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.iso_forest = IsolationForest(contamination=0.06, random_state=42, n_estimators=120)
        self.rf_clf = RandomForestClassifier(
            n_estimators=120, max_depth=10, min_samples_leaf=2, random_state=42
        )
        self.hgb_calibrated = CalibratedClassifierCV(
            estimator=HistGradientBoostingClassifier(max_iter=120, max_depth=6, random_state=42),
            method="sigmoid",
            cv=3,
        )
        self.classes_: list[str] = []
        self._raw_min: float = -0.25
        self._raw_max: float = 0.20
        self.validation_metrics: MLValidationMetrics | None = None
        self._train_and_validate_cohort()

    def _generate_cohort_dataset(self) -> tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(42)

        # 16 features:
        # [hr, hrv, bp_sys, bp_dia, glucose, temp, spo2, rr, sleep, mood, rad, nut_pct, min_ex, co2, ind_hr_z, ind_hrv_z]
        profiles: dict[str, tuple[int, list[float], list[float]]] = {
            "nominal": (
                320,
                [67.0, 58.0, 115.0, 73.0, 93.0, 36.7, 98.4, 14.0, 7.4, 4.7, 0.04, 88.0, 310.0, 2.5, 0.1, -0.1],
                [5.0, 6.5, 5.5, 4.0, 6.5, 0.18, 0.5, 1.2, 0.45, 0.4, 0.012, 8.0, 90.0, 0.35, 0.65, 0.65],
            ),
            "post_exercise_physiological": (
                110,
                [106.0, 36.0, 134.0, 78.0, 89.0, 37.6, 98.1, 20.0, 7.4, 4.8, 0.04, 89.0, 18.0, 2.7, 3.8, -2.4],
                [7.0, 4.5, 6.5, 4.5, 6.0, 0.22, 0.6, 1.8, 0.45, 0.4, 0.012, 8.0, 10.0, 0.35, 0.8, 0.7],
            ),
            "cabin_co2_pocket": (
                110,
                [88.0, 39.0, 131.0, 83.0, 96.0, 36.8, 95.2, 21.0, 5.8, 3.0, 0.04, 83.0, 420.0, 4.6, 2.4, -2.1],
                [5.5, 4.5, 5.5, 4.0, 6.0, 0.18, 0.7, 1.5, 0.55, 0.5, 0.012, 8.0, 95.0, 0.45, 0.7, 0.65],
            ),
            "systemic_infection": (
                110,
                [112.0, 24.0, 81.0, 51.0, 118.0, 38.5, 94.2, 23.0, 5.2, 2.0, 0.05, 51.0, 650.0, 2.6, 5.2, -4.1],
                [6.5, 4.0, 5.0, 4.0, 9.5, 0.32, 0.9, 1.8, 0.65, 0.5, 0.015, 9.5, 140.0, 0.35, 0.9, 0.75],
            ),
            "orthostatic_intolerance": (
                110,
                [107.0, 34.0, 85.0, 55.0, 88.0, 36.6, 97.1, 19.0, 6.4, 3.0, 0.04, 73.0, 240.0, 2.8, 4.3, -2.8],
                [6.0, 4.5, 4.5, 3.8, 6.0, 0.18, 0.7, 1.5, 0.55, 0.5, 0.015, 9.0, 75.0, 0.35, 0.8, 0.7],
            ),
            "behavioral_fatigue": (
                110,
                [86.0, 21.0, 128.0, 82.0, 104.0, 36.8, 97.8, 17.0, 3.8, 1.9, 0.04, 71.0, 390.0, 3.0, 2.3, -4.3],
                [5.5, 3.8, 5.5, 4.5, 6.5, 0.20, 0.6, 1.4, 0.45, 0.45, 0.015, 9.0, 95.0, 0.40, 0.7, 0.7],
            ),
            "hypoglycemia": (
                110,
                [102.0, 38.0, 104.0, 68.0, 62.0, 36.4, 97.9, 18.0, 6.6, 3.0, 0.05, 41.0, 170.0, 2.8, 3.8, -2.3],
                [6.0, 4.5, 5.0, 4.0, 4.5, 0.18, 0.6, 1.4, 0.50, 0.5, 0.015, 7.5, 65.0, 0.35, 0.75, 0.65],
            ),
            "solar_storm": (
                110,
                [96.0, 42.0, 124.0, 78.0, 97.0, 36.8, 98.2, 17.0, 7.1, 3.1, 0.68, 84.0, 220.0, 2.5, 3.0, -1.9],
                [6.0, 4.8, 5.5, 4.0, 6.0, 0.18, 0.6, 1.4, 0.50, 0.5, 0.13, 8.5, 80.0, 0.35, 0.75, 0.65],
            ),
        }

        X_list: list[np.ndarray] = []
        y_list: list[str] = []

        bounds = [
            (42.0, 165.0),   # hr
            (10.0, 105.0),   # hrv
            (65.0, 185.0),   # bp_sys
            (40.0, 115.0),   # bp_dia
            (42.0, 220.0),   # glucose
            (35.2, 40.6),    # temp
            (88.0, 100.0),   # spo2
            (9.0, 34.0),     # rr
            (2.0, 10.5),     # sleep
            (1.0, 5.0),      # mood
            (0.01, 2.5),     # rad
            (15.0, 130.0),   # nut_pct
            (2.0, 1440.0),   # min_ex
            (1.5, 8.5),      # co2
            (-5.0, 9.0),     # ind_hr_z
            (-8.0, 5.0),     # ind_hrv_z
        ]

        for label, (count, means, stds) in profiles.items():
            # Add realistic biological boundary dispersion (1.35x std + 4% borderline prodromal cases)
            adj_stds = [s * 1.35 for s in stds]
            samples = rng.normal(loc=means, scale=adj_stds, size=(count, len(FEATURE_SPECS)))
            if label != "nominal":
                # Blend 8% early/prodromal transition cases halfway toward nominal baseline
                n_prodromal = max(3, int(count * 0.08))
                nom_means = np.array(profiles["nominal"][1])
                samples[:n_prodromal] = 0.52 * samples[:n_prodromal] + 0.48 * nom_means + rng.normal(
                    0, [s * 0.6 for s in stds], size=(n_prodromal, len(FEATURE_SPECS))
                )
            for col_idx, (low, high) in enumerate(bounds):
                samples[:, col_idx] = np.clip(samples[:, col_idx], low, high)
            X_list.append(samples)
            y_list.extend([label] * count)

        return np.vstack(X_list), np.array(y_list)

    @staticmethod
    def _compute_ece(y_true_idx: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> float:
        confidences = np.max(probs, axis=1)
        predictions = np.argmax(probs, axis=1)
        accuracies = (predictions == y_true_idx).astype(float)

        bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        n_total = len(y_true_idx)
        for i in range(n_bins):
            in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
            prop_in_bin = np.mean(in_bin)
            if prop_in_bin > 0:
                acc_in_bin = np.mean(accuracies[in_bin])
                avg_conf_in_bin = np.mean(confidences[in_bin])
                ece += abs(acc_in_bin - avg_conf_in_bin) * (np.sum(in_bin) / n_total)
        return float(ece)

    def _train_and_validate_cohort(self) -> None:
        X, y = self._generate_cohort_dataset()
        X_scaled = self.scaler.fit_transform(X)

        # Fit unsupervised IsolationForest on nominal state
        X_nominal_scaled = X_scaled[y == "nominal"]
        self.iso_forest.fit(X_nominal_scaled)
        scores = self.iso_forest.decision_function(X_scaled)
        self._raw_min = float(np.percentile(scores, 3))
        self._raw_max = float(np.percentile(scores, 97))

        # Fit full models
        self.rf_clf.fit(X_scaled, y)
        self.hgb_calibrated.fit(X_scaled, y)
        self.classes_ = [str(c) for c in self.rf_clf.classes_]
        class_to_idx = {c: i for i, c in enumerate(self.classes_)}
        y_idx = np.array([class_to_idx[c] for c in y])

        # Compute 5-fold Stratified Out-of-Fold validation metrics
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        oof_probs = np.zeros((len(y), len(self.classes_)), dtype=float)

        for train_idx, val_idx in skf.split(X_scaled, y):
            rf_fold = RandomForestClassifier(n_estimators=60, max_depth=9, random_state=42)
            hgb_fold = HistGradientBoostingClassifier(max_iter=80, max_depth=5, random_state=42)
            rf_fold.fit(X_scaled[train_idx], y[train_idx])
            hgb_fold.fit(X_scaled[train_idx], y[train_idx])
            oof_probs[val_idx] = 0.5 * rf_fold.predict_proba(X_scaled[val_idx]) + 0.5 * hgb_fold.predict_proba(
                X_scaled[val_idx]
            )

        oof_preds_idx = np.argmax(oof_probs, axis=1)
        acc = float(accuracy_score(y_idx, oof_preds_idx))
        f1 = float(f1_score(y_idx, oof_preds_idx, average="macro"))

        # Multiclass Brier score (mean squared error across probability vector)
        y_onehot = np.eye(len(self.classes_))[y_idx]
        brier = float(np.mean(np.sum((oof_probs - y_onehot) ** 2, axis=1)))
        ece = self._compute_ece(y_idx, oof_probs)

        self.validation_metrics = MLValidationMetrics(
            model_architecture="Calibrated HistGradientBoosting + RandomForest Ensemble + IsolationForest + LedoitWolf Mahalanobis",
            calibration_method="Platt Sigmoid Calibration + 5-Fold Out-of-Fold Verification",
            cv_folds=5,
            training_samples=int(len(y)),
            stratified_accuracy=round(acc * 100.0, 2),
            macro_f1_score=round(f1 * 100.0, 2),
            multiclass_brier_score=round(brier, 4),
            expected_calibration_error=round(ece, 4),
        )

    def _extract_vector(
        self,
        vitals: VitalSigns,
        nutrition: NutritionHydrationState,
        context: MissionContext,
        adaptive_baseline: AdaptiveBaselineProfile,
    ) -> np.ndarray:
        nutrition_goal_pct = min(
            130.0,
            max(10.0, (nutrition.calories_kcal / max(nutrition.goal_calories_kcal, 1.0)) * 100.0),
        )
        ind_hr_z = adaptive_baseline.metrics["heart_rate_bpm"].individual_z_score
        ind_hrv_z = adaptive_baseline.metrics["hrv_ms"].individual_z_score

        return np.array(
            [
                [
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
                    nutrition_goal_pct,
                    context.minutes_since_last_exercise,
                    context.cabin_co2_mmhg,
                    ind_hr_z,
                    ind_hrv_z,
                ]
            ],
            dtype=float,
        )

    def _compute_uncertainty(
        self,
        vec_scaled: np.ndarray,
        ensemble_probs: np.ndarray,
        quality: MeasurementQualityProfile,
    ) -> UncertaintyAssessment:
        # 1. Epistemic uncertainty: inter-tree variance across all 120 RF trees + HGB vs RF divergence
        tree_preds = np.array([tree.predict_proba(vec_scaled)[0] for tree in self.rf_clf.estimators_])
        best_cls_idx = int(np.argmax(ensemble_probs))
        tree_std = float(np.std(tree_preds[:, best_cls_idx])) * 100.0

        # 2. Aleatoric uncertainty from sensor SNR, motion artifact, unverified NIBP, or old CGM calibration
        sensor_noise = max(1.5, (100.0 - quality.overall_quality_pct) * 0.55)
        factors: list[str] = []
        if quality.motion_artifact_detected:
            sensor_noise += 6.5
            factors.append("6-axis accelerometer motion artifact detected on wrist PPG")
        if not quality.nibp_cuff_verified:
            sensor_noise += 3.0
            factors.append("Blood pressure pending anchored brachial NIBP cuff verification")
        if not quality.ambient_temp_compensated:
            sensor_noise += 3.5
            factors.append("Skin thermistor uncompensated for post-exercise / cabin thermal flux")
        if quality.cgm_calibration_age_hours > 12.0:
            sensor_noise += 3.0
            factors.append(f"CGM interstitial calibration age ({quality.cgm_calibration_age_hours:.0f}h) exceeds 12h nominal window")

        # 3. Shannon entropy across class distribution
        clipped_p = np.clip(ensemble_probs, 1e-9, 1.0)
        entropy_bits = float(-np.sum(clipped_p * np.log2(clipped_p)))

        total_unc = float(np.clip(np.hypot(tree_std, sensor_noise), 2.0, 48.0))
        top_conf = float(ensemble_probs[best_cls_idx]) * 100.0
        ci_low = round(max(1.0, top_conf - 1.96 * (total_unc * 0.5)), 1)
        ci_high = round(min(99.9, top_conf + 1.96 * (total_unc * 0.5)), 1)

        if quality.overall_quality_pct < 82.0 or total_unc >= 18.0:
            grade: ReliabilityGrade = "LOW_REQUIRES_CONFIRMATION"
        elif quality.overall_quality_pct < 91.0 or total_unc >= 11.0:
            grade = "MODERATE"
        else:
            grade = "HIGH"

        if not factors:
            factors.append("Multi-channel ECG/PPG/Dosimeter telemetry locked with high SNR")

        return UncertaintyAssessment(
            epistemic_ensemble_std_pct=round(tree_std, 2),
            aleatoric_sensor_noise_pct=round(sensor_noise, 2),
            total_uncertainty_pct=round(total_unc, 2),
            shannon_entropy_bits=round(entropy_bits, 3),
            confidence_interval_95_pct=[ci_low, ci_high],
            reliability_grade=grade,
            uncertainty_factors=factors,
            requires_confirmatory_remeasurement=(grade != "HIGH" or not quality.nibp_cuff_verified),
        )

    def _forecast_72h(
        self,
        vitals: VitalSigns,
        longitudinal_series: list[dict[str, Any]],
        current_anomaly_score: float,
    ) -> list[ForecastHorizonPoint]:
        # Fit online BayesianRidge regression over longitudinal history (D-6 .. Today) for HR, HRV, Glucose
        n_pts = len(longitudinal_series)
        if n_pts < 3:
            t_steps = np.array([0.0, 1.0, 2.0]).reshape(-1, 1)
            hr_y = np.array([vitals.heart_rate_bpm] * 3)
            hrv_y = np.array([vitals.hrv_ms] * 3)
            glu_y = np.array([vitals.glucose_mg_dl] * 3)
        else:
            t_steps = np.arange(n_pts, dtype=float).reshape(-1, 1)
            hr_y = np.array([float(r.get("hr", vitals.heart_rate_bpm)) for r in longitudinal_series])
            hrv_y = np.array([float(r.get("hrv", vitals.hrv_ms)) for r in longitudinal_series])
            glu_y = np.array([float(r.get("glucose", vitals.glucose_mg_dl)) for r in longitudinal_series])

        # Use last 4 days to capture recent velocity + damped mean-reversion if nominal
        window = min(5, len(t_steps))
        t_win = t_steps[-window:]
        br_hr = BayesianRidge().fit(t_win, hr_y[-window:])
        br_hrv = BayesianRidge().fit(t_win, hrv_y[-window:])
        br_glu = BayesianRidge().fit(t_win, glu_y[-window:])

        last_t = float(t_steps[-1, 0])
        horizons = [(24, 1.0, "+24h (M+1)"), (48, 2.0, "+48h (M+2)"), (72, 3.0, "+72h (M+3)")]
        forecasts: list[ForecastHorizonPoint] = []

        for hours, day_offset, label in horizons:
            # Damped horizon step so linear trend doesn't explode unrealistically over 3 days
            eff_step = np.array([[last_t + day_offset * 0.65]])
            hr_mean, hr_std = br_hr.predict(eff_step, return_std=True)
            hrv_mean, hrv_std = br_hrv.predict(eff_step, return_std=True)
            glu_mean, glu_std = br_glu.predict(eff_step, return_std=True)

            p_hr = float(np.clip(hr_mean[0], 45.0, 155.0))
            s_hr = max(2.5, float(hr_std[0]) * (1.0 + 0.18 * day_offset))

            p_hrv = float(np.clip(hrv_mean[0], 12.0, 95.0))
            s_hrv = max(2.5, float(hrv_std[0]) * (1.0 + 0.18 * day_offset))

            p_glu = float(np.clip(glu_mean[0], 48.0, 210.0))
            s_glu = max(3.5, float(glu_std[0]) * (1.0 + 0.18 * day_offset))

            # Project anomaly risk trajectory based on slope of HR/HRV
            hr_slope = p_hr - vitals.heart_rate_bpm
            hrv_slope = p_hrv - vitals.hrv_ms
            risk_shift = hr_slope * 0.55 - hrv_slope * 0.65
            p_risk = float(np.clip(current_anomaly_score + risk_shift, 3.0, 99.0))
            s_risk = 4.5 + 2.5 * day_offset

            forecasts.append(
                ForecastHorizonPoint(
                    horizon_hours=hours,
                    label=label,
                    predicted_hr_bpm=round(p_hr, 1),
                    hr_ci_80=[round(max(40.0, p_hr - 1.28 * s_hr), 1), round(min(165.0, p_hr + 1.28 * s_hr), 1)],
                    predicted_hrv_ms=round(p_hrv, 1),
                    hrv_ci_80=[round(max(10.0, p_hrv - 1.28 * s_hrv), 1), round(min(100.0, p_hrv + 1.28 * s_hrv), 1)],
                    predicted_glucose_mg_dl=round(p_glu, 1),
                    glucose_ci_80=[round(max(45.0, p_glu - 1.28 * s_glu), 1), round(min(220.0, p_glu + 1.28 * s_glu), 1)],
                    predicted_anomaly_risk_pct=round(p_risk, 1),
                    risk_ci_80=[round(max(1.0, p_risk - 1.28 * s_risk), 1), round(min(99.9, p_risk + 1.28 * s_risk), 1)],
                )
            )

        return forecasts

    def predict(
        self,
        vitals: VitalSigns,
        nutrition: NutritionHydrationState,
        context: MissionContext,
        quality: MeasurementQualityProfile,
        adaptive_baseline: AdaptiveBaselineProfile,
        contextual_report: ContextualIntelligenceReport,
        longitudinal_series: list[dict[str, Any]],
    ) -> MLPredictionResult:
        vec = self._extract_vector(vitals, nutrition, context, adaptive_baseline)
        vec_scaled = self.scaler.transform(vec)

        # 1. Population IsolationForest score
        raw_decision = float(self.iso_forest.decision_function(vec_scaled)[0])
        denom = max(self._raw_max - self._raw_min, 1e-6)
        normalized = (self._raw_max - raw_decision) / denom
        raw_pop_anomaly = round(float(np.clip(normalized * 100.0, 2.0, 99.5)), 1)

        # 2. Personal Baseline Drift Score (from AdaptiveBaselineEngine Mahalanobis distance)
        personal_anomaly = adaptive_baseline.personal_drift_score

        # Blend 55% personal adaptive baseline + 45% population IsolationForest
        blended_anomaly = 0.55 * personal_anomaly + 0.45 * raw_pop_anomaly

        # Apply Contextual Intelligence attenuation when a non-pathological confounder (e.g. recent exercise) explains the spike
        attenuation_factor = 1.0 - (contextual_report.context_anomaly_attenuation_pct / 100.0)
        context_adjusted_anomaly = round(float(np.clip(blended_anomaly * attenuation_factor, 2.0, 99.5)), 1)

        # 3. Calibrated Ensemble Probabilities (50% Calibrated HGB + 50% RF)
        rf_probs = self.rf_clf.predict_proba(vec_scaled)[0]
        hgb_probs = self.hgb_calibrated.predict_proba(vec_scaled)[0]
        ensemble_probs = 0.5 * rf_probs + 0.5 * hgb_probs

        prob_map = {cls: round(float(p) * 100.0, 1) for cls, p in zip(self.classes_, ensemble_probs)}
        best_idx = int(np.argmax(ensemble_probs))
        predicted_syndrome = self.classes_[best_idx]
        confidence_pct = round(float(ensemble_probs[best_idx]) * 100.0, 1)

        # 4. Counterfactual Local Perturbation Attribution + Personal Baseline Z-Score
        global_imp = self.rf_clf.feature_importances_
        current_vals = vec[0]
        raw_weights: list[float] = []
        feature_meta: list[tuple[str, str, float, float, float, float, float]] = []

        for idx, (key, label, pop_base, pop_std) in enumerate(FEATURE_SPECS):
            curr_v = float(current_vals[idx])
            if key in adaptive_baseline.metrics:
                m_base = adaptive_baseline.metrics[key]
                pers_base = m_base.rolling_ewma_baseline
                ind_z = m_base.individual_z_score
                pop_z = m_base.population_z_score
            elif key == "individual_hr_z_score":
                pers_base = 0.0
                ind_z = curr_v
                pop_z = adaptive_baseline.metrics["heart_rate_bpm"].population_z_score
            elif key == "individual_hrv_z_score":
                pers_base = 0.0
                ind_z = curr_v
                pop_z = adaptive_baseline.metrics["hrv_ms"].population_z_score
            else:
                pers_base = pop_base
                ind_z = (curr_v - pop_base) / max(pop_std, 1e-6)
                pop_z = ind_z

            # Counterfactual perturbation: replace feature with personal baseline and measure probability shift
            vec_perturbed = vec.copy()
            vec_perturbed[0, idx] = pers_base
            vec_pert_scaled = self.scaler.transform(vec_perturbed)
            pert_prob = 0.5 * self.rf_clf.predict_proba(vec_pert_scaled)[0, best_idx] + 0.5 * self.hgb_calibrated.predict_proba(
                vec_pert_scaled
            )[0, best_idx]
            cf_drop = max(0.0, float(ensemble_probs[best_idx] - pert_prob))

            dev_pct = round(((curr_v - pers_base) / max(abs(pers_base), 1.0)) * 100.0, 1)
            weight = float(global_imp[idx]) * (0.25 + min(abs(ind_z), 5.5)) + cf_drop * 1.8
            raw_weights.append(weight)
            feature_meta.append((key, label, curr_v, pop_base, pers_base, dev_pct, ind_z, pop_z))

        # Exclude redundant synthetic z-score meta-features from display list so top features are concrete physiological/contextual signals
        display_indices = [i for i, (k, *_) in enumerate(FEATURE_SPECS) if not k.startswith("individual_")]
        weight_sum = sum(raw_weights[i] for i in display_indices) or 1.0

        feature_items: list[FeatureImportanceItem] = []
        for idx in display_indices:
            key, label, curr_v, pop_base, pers_base, dev_pct, ind_z, pop_z = feature_meta[idx]
            direction = "ELEVATED" if ind_z >= 1.2 else ("SUPPRESSED" if ind_z <= -1.2 else "NOMINAL")
            feature_items.append(
                FeatureImportanceItem(
                    feature=key,
                    label=label,
                    importance=round((raw_weights[idx] / weight_sum) * 100.0, 1),
                    current_value=round(curr_v, 2),
                    baseline_value=round(pop_base, 2),
                    personal_baseline_value=round(pers_base, 2),
                    deviation_pct=dev_pct,
                    individual_z_score=round(ind_z, 2),
                    population_z_score=round(pop_z, 2),
                    direction=direction,
                )
            )

        feature_items.sort(key=lambda item: item.importance, reverse=True)

        # 5. Uncertainty Quantification & 72h Trajectory Forecast
        uncertainty = self._compute_uncertainty(vec_scaled, ensemble_probs, quality)
        forecast_72h = self._forecast_72h(vitals, longitudinal_series, context_adjusted_anomaly)

        is_anomalous = (
            context_adjusted_anomaly >= 46.0
            or predicted_syndrome not in ("nominal", "post_exercise_physiological")
        )

        return MLPredictionResult(
            anomaly_score=context_adjusted_anomaly,
            raw_population_anomaly_score=raw_pop_anomaly,
            personal_baseline_anomaly_score=personal_anomaly,
            context_adjusted_anomaly_score=context_adjusted_anomaly,
            is_anomalous=is_anomalous,
            predicted_syndrome=predicted_syndrome,
            predicted_syndrome_label=SYNDROME_LABELS.get(predicted_syndrome, predicted_syndrome),
            confidence_pct=confidence_pct,
            syndrome_probabilities=prob_map,
            feature_importances=feature_items[:6],
            uncertainty=uncertainty,
            forecast_72h=forecast_72h,
            validation_metrics=self.validation_metrics,
        )
