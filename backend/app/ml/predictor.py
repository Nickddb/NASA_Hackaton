from __future__ import annotations

from typing import Any
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.linear_model import BayesianRidge
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from app.engine.clinical_rules import load_scenarios_catalog
from app.ml.features import FEATURE_KEYS, FEATURE_SPECS, PAIN_FEATURES, build_generator_cohort, live_feature_vector
from app.models.schemas import (
    AdaptiveBaselineProfile,
    ContextualIntelligenceReport,
    FeatureImportanceItem,
    ForecastHorizonPoint,
    MeasurementQualityProfile,
    MissionContext,
    MLPredictionResult,
    MLValidationMetrics,
    PersonalBaseline,
    SpaceWeatherSummary,
    NutritionHydrationState,
    ReliabilityGrade,
    UncertaintyAssessment,
    VitalSigns,
)

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
        """Training data drawn from the NASA-calibrated telemetry generator for every roster astronaut."""
        X, y, n_astronauts = build_generator_cohort(load_scenarios_catalog())
        self._cohort_astronauts = n_astronauts
        return X, y

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
            training_data_source=(
                f"NASA-calibrated stochastic generator: {getattr(self, '_cohort_astronauts', 0)} roster astronauts x "
                f"{len(self.classes_)} profiles (half full-blown, half early 15-100 % of the way), jittered context, "
                "DONKI level and crew symptom reports. Metrics are measured on synthetic data and are optimistic: "
                "they are not an estimate of real-world clinical performance."
            ),
            feature_names=list(FEATURE_KEYS),
        )

    def _extract_vector(
        self,
        vitals: VitalSigns,
        nutrition: NutritionHydrationState,
        context: MissionContext,
        adaptive_baseline: AdaptiveBaselineProfile,
        personal_baseline: PersonalBaseline | None = None,
        space_weather: SpaceWeatherSummary | None = None,
    ) -> np.ndarray:
        return live_feature_vector(vitals, nutrition, context, adaptive_baseline, personal_baseline, space_weather)

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
        personal_baseline: PersonalBaseline | None = None,
        space_weather: SpaceWeatherSummary | None = None,
    ) -> MLPredictionResult:
        vec = self._extract_vector(vitals, nutrition, context, adaptive_baseline, personal_baseline, space_weather)
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

        # How the crew's pain report moved the model: same reading with the pain features zeroed.
        pain_influence: list[dict[str, Any]] = []
        pain_summary = ""
        pain_idx = [FEATURE_KEYS.index(k) for k in PAIN_FEATURES]
        if vitals.pain_reports and np.any(vec[0, pain_idx] > 0):
            no_pain = vec.copy()
            no_pain[0, pain_idx] = 0.0
            np_scaled = self.scaler.transform(no_pain)
            probs_no_pain = 0.5 * self.rf_clf.predict_proba(np_scaled)[0] + 0.5 * self.hgb_calibrated.predict_proba(np_scaled)[0]
            deltas = (ensemble_probs - probs_no_pain) * 100.0
            for cls_idx in np.argsort(-np.abs(deltas)):
                if abs(deltas[cls_idx]) < 1.0:
                    break
                cls = self.classes_[cls_idx]
                pain_influence.append(
                    {"syndrome": cls, "label": SYNDROME_LABELS.get(cls, cls), "delta_pct": round(float(deltas[cls_idx]), 1)}
                )
            regions = ", ".join(f"{r.region_label} {r.intensity}/10" for r in vitals.pain_reports)
            up = [i for i in pain_influence if i["delta_pct"] > 0][:2]
            pain_summary = (
                f"Reported pain ({regions}) raised: "
                + "; ".join(f"{i['label']} +{i['delta_pct']:.0f} pp" for i in up)
                if up
                else f"Reported pain ({regions}) did not change the syndrome probabilities by more than 1 pp."
            )
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

            dev_pct = round(((curr_v - pers_base) / max(abs(pers_base), 1.0)) * 100.0, 1)
            feature_meta.append((key, label, curr_v, pop_base, pers_base, dev_pct, ind_z, pop_z))

        # Counterfactual perturbation: replace each feature with the personal baseline and measure the probability
        # shift. All perturbed rows go through the models in ONE batch (was one predict_proba per feature, ~1 s/state).
        perturbed = np.repeat(vec, len(FEATURE_SPECS), axis=0)
        for idx, meta in enumerate(feature_meta):
            perturbed[idx, idx] = meta[4]
        pert_scaled = self.scaler.transform(perturbed)
        pert_probs = 0.5 * self.rf_clf.predict_proba(pert_scaled)[:, best_idx] + 0.5 * self.hgb_calibrated.predict_proba(
            pert_scaled
        )[:, best_idx]
        for idx, meta in enumerate(feature_meta):
            cf_drop = max(0.0, float(ensemble_probs[best_idx] - pert_probs[idx]))
            raw_weights.append(float(global_imp[idx]) * (0.25 + min(abs(meta[6]), 5.5)) + cf_drop * 1.8)

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
            pain_influence=pain_influence,
            pain_summary=pain_summary,
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
