from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

SeverityStatus = Literal["NOMINAL", "WARNING", "CRITICAL"]


class VitalSigns(BaseModel):
    heart_rate_bpm: float = Field(..., description="Resting/active heart rate in beats per minute")
    hrv_ms: float = Field(..., description="Heart rate variability RMSSD in milliseconds")
    bp_systolic: float = Field(..., description="Systolic blood pressure in mmHg")
    bp_diastolic: float = Field(..., description="Diastolic blood pressure in mmHg")
    glucose_mg_dl: float = Field(..., description="Blood glucose in mg/dL")
    temperature_c: float = Field(..., description="Core/compensated skin temperature in Celsius")
    spo2_pct: float = Field(..., description="Blood oxygen saturation percentage")
    respiration_rpm: float = Field(..., description="Respiratory rate in breaths per minute")
    sleep_hours: float = Field(..., description="Latest sleep cycle duration in hours")
    sleep_streak_low_days: int = Field(0, description="Consecutive days with < 5.0h sleep")
    rem_sleep_pct: float = Field(21.0, description="REM sleep stage share (%)")
    mood_score: int = Field(..., ge=1, le=5, description="Subjective mood check-in (1-5)")
    stress_index: float = Field(..., ge=0, le=100, description="Composite physiological/behavioral stress index")
    radiation_msv_h: float = Field(..., description="Instantaneous radiation dose rate in mSv/h")
    cumulative_radiation_msv: float = Field(..., description="Mission cumulative radiation dose in mSv")
    shoulder_pain_score: int = Field(0, ge=0, le=10, description="EVA HUT shoulder pain VAS (0-10)")
    pfo_decompression_risk: Literal["LOW", "MODERATE", "HIGH"] = Field(
        "LOW", description="OCHMO-MTB-011 PFO / EVA DCS risk tier"
    )
    urinary_calcium_mg_d: float = Field(180.0, description="Urolux urinary calcium excretion mg/day")
    intraocular_pressure_mmhg: float = Field(15.0, description="Tonometry intraocular pressure for SANS screening")


class LoggedFoodItem(BaseModel):
    timestamp: str
    item: str
    calories_kcal: float
    water_ml: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fiber_g: float = 0.0
    sodium_mg: float = 0.0
    iron_mg: float = 0.0


class NutritionHydrationState(BaseModel):
    calories_kcal: float = 2150.0
    goal_calories_kcal: float = 2800.0
    water_ml: float = 1950.0
    goal_water_ml: float = 2500.0
    sodium_mg: float = 2400.0
    max_sodium_mg: float = 3500.0
    iron_mg: float = 7.4
    max_iron_mg: float = 10.0
    protein_g: float = 92.0
    goal_protein_g: float = 110.0
    carbs_g: float = 265.0
    goal_carbs_g: float = 340.0
    fiber_g: float = 24.0
    goal_fiber_g: float = 30.0
    logged_items: list[LoggedFoodItem] = Field(default_factory=list)


class SystemEvaluation(BaseModel):
    system_id: str
    name: str
    status: SeverityStatus
    summary: str
    active_alerts: list[str] = Field(default_factory=list)
    recommended_action: str
    checs_device: str
    reference_standard: str


class ClinicalEvaluationResult(BaseModel):
    overall_status: SeverityStatus
    primary_diagnosis: str
    syndrome_code: str
    matched_rules: list[str] = Field(default_factory=list)
    systems: dict[str, SystemEvaluation]
    stabilization_checklist: list[str] = Field(default_factory=list)
    notify_earth_flight_surgeon: bool = False
    notify_crew_onboard: bool = False
    environment_calibration_notes: list[str] = Field(default_factory=list)
    decontamination_required: bool = False
    decontamination_checklist: list[str] = Field(default_factory=list)


class FeatureImportanceItem(BaseModel):
    feature: str
    label: str
    importance: float
    current_value: float
    baseline_value: float
    deviation_pct: float


class MLPredictionResult(BaseModel):
    anomaly_score: float = Field(..., ge=0.0, le=100.0)
    is_anomalous: bool
    predicted_syndrome: str
    predicted_syndrome_label: str
    confidence_pct: float
    syndrome_probabilities: dict[str, float]
    feature_importances: list[FeatureImportanceItem]


class ToolTraceItem(BaseModel):
    tool_name: str
    status: Literal["OK", "WARNING", "CRITICAL"] = "OK"
    summary: str
    rule_or_score: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    mode: Literal["langchain_gemini", "offline_hybrid_edge"]
    tool_trace: list[ToolTraceItem] = Field(default_factory=list)
    state: MissionState


class SpaceWeatherEvent(BaseModel):
    event_id: str
    event_type: Literal["FLR", "SEP"]
    begin_time: str
    peak_time: str | None = None
    class_or_intensity: str
    source_location: str
    note: str


class SpaceWeatherSummary(BaseModel):
    source: Literal["live_nasa_donki", "curated_local_fallback"]
    fetched_at: str
    alert_level: SeverityStatus
    active_flare_count: int
    active_sep_count: int
    recommended_dose_limit_msv_h: float
    alara_instruction: str
    events: list[SpaceWeatherEvent] = Field(default_factory=list)


class MeasurementResponse(BaseModel):
    system_id: str
    system_name: str
    device_used: str
    decontamination_required: bool
    decontamination_checklist: list[str] = Field(default_factory=list)
    reading_summary: str
    status: SeverityStatus
    guidance: str
    state: MissionState


class TelemedicineDossier(BaseModel):
    dossier_id: str
    generated_at: str
    mission_day: int
    crew_member: str
    environment_id: str
    environment_name: str
    one_way_latency_seconds: int
    transmission_mode: str
    urgency: SeverityStatus
    recipient_roles: list[str]
    executive_summary: str
    clinical_evaluation: ClinicalEvaluationResult
    ml_prediction: MLPredictionResult
    vitals_snapshot: VitalSigns
    nutrition_snapshot: NutritionHydrationState
    space_weather_alert: str
    recommended_earth_questions: list[str]


class MissionState(BaseModel):
    mission_day: int = 142
    crew_member: str = "CDR Elena Vance (EVA-1)"
    scenario_id: str
    scenario_name: str
    scenario_description: str
    environment_id: str
    environment_name: str
    one_way_latency_seconds: int
    vitals: VitalSigns
    nutrition: NutritionHydrationState
    clinical_evaluation: ClinicalEvaluationResult
    ml_prediction: MLPredictionResult
    space_weather: SpaceWeatherSummary | None = None
    longitudinal_series: list[dict[str, Any]] = Field(default_factory=list)
    scenarios_catalog: list[dict[str, Any]] = Field(default_factory=list)
    environments_catalog: list[dict[str, Any]] = Field(default_factory=list)
    indicators_guide: list[dict[str, Any]] = Field(default_factory=list)
    systems_guide: dict[str, Any] = Field(default_factory=dict)
    last_updated: str


ChatResponse.model_rebuild()
MeasurementResponse.model_rebuild()
