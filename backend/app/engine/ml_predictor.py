from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from app.models.schemas import (
    FeatureImportanceItem,
    MLPredictionResult,
    NutritionHydrationState,
    VitalSigns,
)

FEATURE_SPECS: list[tuple[str, str, float, float]] = [
    # (key, label, nominal_baseline, scale_std)
    ("heart_rate_bpm", "Heart Rate (bpm)", 68.0, 8.0),
    ("hrv_ms", "HRV RMSSD (ms)", 58.0, 9.0),
    ("bp_systolic", "Systolic BP (mmHg)", 116.0, 9.0),
    ("bp_diastolic", "Diastolic BP (mmHg)", 74.0, 6.0),
    ("glucose_mg_dl", "Blood Glucose (mg/dL)", 94.0, 10.0),
    ("temperature_c", "Body Temp (C)", 36.7, 0.35),
    ("sleep_hours", "Sleep Duration (h)", 7.4, 0.8),
    ("mood_score", "Mood Check-In (1-5)", 4.6, 0.6),
    ("radiation_msv_h", "Radiation Rate (mSv/h)", 0.04, 0.03),
    ("nutrition_goal_pct", "Nutrition Goal (%)", 88.0, 12.0),
]

SYNDROME_LABELS: dict[str, str] = {
    "nominal": "Nominal Mission State",
    "systemic_infection": "Systemic Infection / Acute Viral State",
    "orthostatic_intolerance": "Orthostatic Intolerance / Fluid Shift",
    "behavioral_fatigue": "Severe Behavioral Fatigue & Circadian Desynchrony",
    "hypoglycemia": "Caloric-Deficit Hypoglycemia",
    "solar_storm": "Solar Particle Event (SPE) Radiation Spike",
}


class AstraCareMLPredictor:
    """Layer 2 Predictive Machine Learning Engine (IsolationForest + RandomForestClassifier)."""

    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.iso_forest = IsolationForest(contamination=0.18, random_state=42, n_estimators=100)
        self.rf_clf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42)
        self.classes_: list[str] = []
        self._raw_min: float = -0.25
        self._raw_max: float = 0.20
        self._train_on_synthetic_cohort()

    def _train_on_synthetic_cohort(self) -> None:
        rng = np.random.default_rng(42)

        # Synthetic NASA OSDR / Standard Measures calibrated astronaut cohort (600 samples)
        profiles: dict[str, tuple[int, list[float], list[float]]] = {
            "nominal": (
                250,
                [68.0, 58.0, 116.0, 74.0, 94.0, 36.7, 7.4, 4.7, 0.04, 88.0],
                [5.5, 7.0, 6.0, 4.5, 7.0, 0.2, 0.5, 0.45, 0.015, 9.0],
            ),
            "systemic_infection": (
                70,
                [112.0, 24.0, 82.0, 52.0, 118.0, 38.5, 5.2, 2.0, 0.05, 52.0],
                [7.0, 4.0, 5.0, 4.0, 10.0, 0.35, 0.7, 0.5, 0.015, 10.0],
            ),
            "orthostatic_intolerance": (
                70,
                [106.0, 34.0, 85.0, 55.0, 88.0, 36.6, 6.4, 3.0, 0.04, 72.0],
                [6.0, 5.0, 4.5, 4.0, 6.0, 0.2, 0.6, 0.5, 0.015, 10.0],
            ),
            "behavioral_fatigue": (
                70,
                [86.0, 21.0, 127.0, 82.0, 104.0, 36.8, 3.8, 1.8, 0.04, 70.0],
                [6.0, 4.0, 6.0, 5.0, 7.0, 0.25, 0.5, 0.45, 0.015, 10.0],
            ),
            "hypoglycemia": (
                70,
                [101.0, 38.0, 104.0, 68.0, 62.0, 36.4, 6.6, 3.0, 0.05, 41.0],
                [6.0, 5.0, 5.0, 4.0, 4.5, 0.2, 0.5, 0.5, 0.015, 8.0],
            ),
            "solar_storm": (
                70,
                [95.0, 42.0, 123.0, 78.0, 96.0, 36.8, 7.0, 3.2, 0.68, 84.0],
                [6.0, 5.0, 5.5, 4.0, 6.0, 0.2, 0.5, 0.5, 0.14, 9.0],
            ),
        }

        X_list: list[np.ndarray] = []
        y_list: list[str] = []

        for label, (count, means, stds) in profiles.items():
            samples = rng.normal(loc=means, scale=stds, size=(count, len(FEATURE_SPECS)))
            # Clip realistic bounds
            samples[:, 0] = np.clip(samples[:, 0], 40, 160)
            samples[:, 1] = np.clip(samples[:, 1], 10, 100)
            samples[:, 2] = np.clip(samples[:, 2], 65, 180)
            samples[:, 3] = np.clip(samples[:, 3], 40, 110)
            samples[:, 4] = np.clip(samples[:, 4], 45, 220)
            samples[:, 5] = np.clip(samples[:, 5], 35.0, 40.5)
            samples[:, 6] = np.clip(samples[:, 6], 2.0, 10.0)
            samples[:, 7] = np.clip(samples[:, 7], 1.0, 5.0)
            samples[:, 8] = np.clip(samples[:, 8], 0.01, 2.0)
            samples[:, 9] = np.clip(samples[:, 9], 15.0, 130.0)
            X_list.append(samples)
            y_list.extend([label] * count)

        X = np.vstack(X_list)
        y = np.array(y_list)

        X_scaled = self.scaler.fit_transform(X)
        # Fit IsolationForest strictly on healthy nominal baseline so syndromes score as clear anomalies
        X_nominal_scaled = X_scaled[y == "nominal"]
        self.iso_forest = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
        self.iso_forest.fit(X_nominal_scaled)
        scores = self.iso_forest.decision_function(X_scaled)
        self._raw_min = float(np.percentile(scores, 3))
        self._raw_max = float(np.percentile(scores, 97))

        self.rf_clf.fit(X_scaled, y)
        self.classes_ = [str(c) for c in self.rf_clf.classes_]

    def _extract_vector(self, vitals: VitalSigns, nutrition: NutritionHydrationState) -> np.ndarray:
        nutrition_goal_pct = min(
            130.0,
            max(10.0, (nutrition.calories_kcal / max(nutrition.goal_calories_kcal, 1.0)) * 100.0),
        )
        return np.array(
            [
                [
                    vitals.heart_rate_bpm,
                    vitals.hrv_ms,
                    vitals.bp_systolic,
                    vitals.bp_diastolic,
                    vitals.glucose_mg_dl,
                    vitals.temperature_c,
                    vitals.sleep_hours,
                    float(vitals.mood_score),
                    vitals.radiation_msv_h,
                    nutrition_goal_pct,
                ]
            ],
            dtype=float,
        )

    def predict(self, vitals: VitalSigns, nutrition: NutritionHydrationState) -> MLPredictionResult:
        vec = self._extract_vector(vitals, nutrition)
        vec_scaled = self.scaler.transform(vec)

        raw_decision = float(self.iso_forest.decision_function(vec_scaled)[0])
        # Map higher decision_function (inlier) -> lower anomaly_score, lower -> higher anomaly_score (0..100)
        denom = max(self._raw_max - self._raw_min, 1e-6)
        normalized = (self._raw_max - raw_decision) / denom
        anomaly_score = round(float(np.clip(normalized * 100.0, 2.0, 99.5)), 1)

        probs = self.rf_clf.predict_proba(vec_scaled)[0]
        prob_map = {cls: round(float(p) * 100.0, 1) for cls, p in zip(self.classes_, probs)}
        best_idx = int(np.argmax(probs))
        predicted_syndrome = self.classes_[best_idx]
        confidence_pct = round(float(probs[best_idx]) * 100.0, 1)

        # Case-specific driver attribution: combine global RF importances with standardized clinical deviation
        global_imp = self.rf_clf.feature_importances_
        current_vals = vec[0]
        raw_weights: list[float] = []
        deviations: list[float] = []

        for idx, (_, _, baseline, std) in enumerate(FEATURE_SPECS):
            z_dev = abs(float(current_vals[idx]) - baseline) / max(std, 1e-6)
            deviations.append(round(((float(current_vals[idx]) - baseline) / max(baseline, 1e-6)) * 100.0, 1))
            raw_weights.append(float(global_imp[idx]) * (0.35 + min(z_dev, 5.0)))

        weight_sum = sum(raw_weights) or 1.0
        feature_items: list[FeatureImportanceItem] = []
        for idx, (key, label, baseline, _) in enumerate(FEATURE_SPECS):
            feature_items.append(
                FeatureImportanceItem(
                    feature=key,
                    label=label,
                    importance=round((raw_weights[idx] / weight_sum) * 100.0, 1),
                    current_value=round(float(current_vals[idx]), 2),
                    baseline_value=baseline,
                    deviation_pct=deviations[idx],
                )
            )

        feature_items.sort(key=lambda item: item.importance, reverse=True)

        return MLPredictionResult(
            anomaly_score=anomaly_score,
            is_anomalous=anomaly_score >= 50.0 or predicted_syndrome != "nominal",
            predicted_syndrome=predicted_syndrome,
            predicted_syndrome_label=SYNDROME_LABELS.get(predicted_syndrome, predicted_syndrome),
            confidence_pct=confidence_pct,
            syndrome_probabilities=prob_map,
            feature_importances=feature_items[:5],
        )
