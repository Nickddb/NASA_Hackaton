from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

SeverityStatus = Literal["NOMINAL", "WARNING", "CRITICAL"]
ReliabilityGrade = Literal["HIGH", "MODERATE", "LOW_REQUIRES_CONFIRMATION"]
FollowUpStatus = Literal[
    "OPEN_PENDING_CONFIRMATION",
    "CONFIRMED_ACTIVE_MONITORING",
    "ACTION_EXECUTED_AWAITING_REASSESSMENT",
    "DOWNGRADED_CONFOUNDER_OR_ARTIFACT",
    "RESOLVED",
    "ESCALATED_TO_EARTH",
]
SyncStatus = Literal["QUEUED_OFFLINE", "SYNCHRONIZED_WITH_MCC_HOUSTON"]


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


class MeasurementQualityProfile(BaseModel):
    overall_quality_pct: float = Field(95.0, ge=0.0, le=100.0)
    wearable_ppg_quality_pct: float = Field(95.0, ge=0.0, le=100.0)
    nibp_cuff_verified: bool = True
    cgm_calibration_age_hours: float = 6.0
    motion_artifact_detected: bool = False
    ambient_temp_compensated: bool = True
    reliability_grade: ReliabilityGrade = "HIGH"
    sensor_notes: str = "Continuous telemetry nominal."


class MissionContext(BaseModel):
    mission_phase: Literal[
        "pre_flight_1g",
        "acute_microgravity_adaptation",
        "chronic_microgravity_cruise",
        "lunar_partial_g_016",
        "martian_partial_g_038",
    ] = "chronic_microgravity_cruise"
    gravitational_g: float = 0.0
    exercise_minutes_24h: float = 120.0
    exercise_modality: Literal["ARED_resistive", "T2_treadmill", "CEVIS_cycle", "none"] = "ARED_resistive"
    minutes_since_last_exercise: float = 300.0
    eva_status: Literal["none", "pre_eva_prebreathe", "active_eva", "post_eva_recovery"] = "none"
    hours_since_last_eva: float = 72.0
    cabin_co2_mmhg: float = 2.5
    cabin_o2_pct: float = 20.9
    cabin_pressure_psia: float = 14.7
    cabin_temp_c: float = 22.1
    cabin_humidity_pct: float = 44.0
    circadian_shift_hours: float = 0.2


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


# --- PILLAR 1: Adaptive Individual Baseline ---
class AdaptiveMetricBaseline(BaseModel):
    metric: str
    label: str
    unit: str
    current_value: float
    pre_flight_baseline: float
    phase_expected_offset: float
    phase_adapted_baseline: float
    rolling_ewma_baseline: float
    rolling_mad_std: float
    population_baseline: float
    population_std: float
    individual_z_score: float
    population_z_score: float
    deviation_from_personal_pct: float
    status_vs_personal: Literal[
        "WITHIN_PERSONAL_BAND",
        "EXPECTED_PHASE_ADAPTATION",
        "MILD_PERSONAL_DRIFT",
        "SIGNIFICANT_PERSONAL_DEVIATION",
    ]
    # Longitudinal transparency: how much personal history fed the baseline and how the metric is trending
    history_points_used: int = 0
    history_points_quarantined: int = Field(
        0, description="Prior readings excluded from the baseline because they were already anomalous (anti 'boiling frog')."
    )
    trend_slope_sigma_per_day: float = 0.0
    trend_status: Literal["STABLE", "GRADUAL_DRIFT", "SUSTAINED_DRIFT"] = "STABLE"


class AdaptiveBaselineProfile(BaseModel):
    astronaut_id: str
    astronaut_name: str
    mission_day: int
    mission_phase: str
    gravitational_g: float
    ewma_alpha: float = 0.25
    history_window_days: int = 7
    multivariate_mahalanobis_distance: float
    personal_drift_score: float = Field(..., ge=0.0, le=100.0)
    is_personally_anomalous: bool
    adaptation_summary: str
    osdr_reference_study: str = "NASA OSDR OSD-570 / OSD-571 Spaceflight Standard Measures"
    covariance_source: str = "synthetic_physiological_prior"
    drifting_metrics: list[str] = Field(default_factory=list)
    metrics: dict[str, AdaptiveMetricBaseline]


# --- PILLAR 2: Contextual Mission Intelligence ---
class ContextualAssociation(BaseModel):
    factor_id: str
    factor_name: str
    observed_context_value: str
    correlated_metrics: list[str]
    association_strength: float = Field(..., ge=0.0, le=1.0)
    relationship_type: Literal[
        "EXPECTED_PHYSIOLOGICAL_RESPONSE",
        "ENVIRONMENTAL_EXPOSURE_CORRELATION",
        "OPERATIONAL_WORKLOAD_CORRELATION",
        "GRAVITATIONAL_PHASE_TRANSITION",
        "UNEXPLAINED_BY_CONTEXT",
    ]
    rationale: str
    scientific_source: str


class ContextualIntelligenceReport(BaseModel):
    mission_context: MissionContext
    associations: list[ContextualAssociation] = Field(default_factory=list)
    plausible_non_pathological_confounders: list[str] = Field(default_factory=list)
    context_explains_deviation: bool = False
    context_anomaly_attenuation_pct: float = 0.0
    primary_contextual_summary: str
    causal_disclaimer: str = (
        "OBSERVATIONAL CORRELATION ONLY: Contextual associations link physiological readings with sleep, "
        "exercise, EVA, gravity phase, and cabin environment without assuming automatic causality. "
        "Targeted confirmation measurements are required before clinical attribution."
    )


# --- PILLAR 4: Explainable & Auditable Real ML ---
class FeatureImportanceItem(BaseModel):
    feature: str
    label: str
    importance: float
    current_value: float
    baseline_value: float
    personal_baseline_value: float = 0.0
    deviation_pct: float
    individual_z_score: float = 0.0
    population_z_score: float = 0.0
    direction: Literal["ELEVATED", "SUPPRESSED", "NOMINAL"] = "NOMINAL"


class UncertaintyAssessment(BaseModel):
    epistemic_ensemble_std_pct: float = Field(..., description="Disagreement across calibrated ensemble estimators")
    aleatoric_sensor_noise_pct: float = Field(..., description="Uncertainty induced by sensor SNR/motion/calibration age")
    total_uncertainty_pct: float = Field(..., ge=0.0, le=100.0)
    shannon_entropy_bits: float
    confidence_interval_95_pct: list[float]
    reliability_grade: ReliabilityGrade
    uncertainty_factors: list[str] = Field(default_factory=list)
    requires_confirmatory_remeasurement: bool = False


class ForecastHorizonPoint(BaseModel):
    horizon_hours: int
    label: str
    predicted_hr_bpm: float
    hr_ci_80: list[float]
    predicted_hrv_ms: float
    hrv_ci_80: list[float]
    predicted_glucose_mg_dl: float
    glucose_ci_80: list[float]
    predicted_anomaly_risk_pct: float
    risk_ci_80: list[float]


class MLValidationMetrics(BaseModel):
    model_architecture: str
    calibration_method: str
    cv_folds: int
    training_samples: int
    stratified_accuracy: float
    macro_f1_score: float
    multiclass_brier_score: float
    expected_calibration_error: float


class MLPredictionResult(BaseModel):
    anomaly_score: float = Field(..., ge=0.0, le=100.0)
    raw_population_anomaly_score: float = Field(0.0, ge=0.0, le=100.0)
    personal_baseline_anomaly_score: float = Field(0.0, ge=0.0, le=100.0)
    context_adjusted_anomaly_score: float = Field(0.0, ge=0.0, le=100.0)
    is_anomalous: bool
    predicted_syndrome: str
    predicted_syndrome_label: str
    confidence_pct: float
    syndrome_probabilities: dict[str, float]
    feature_importances: list[FeatureImportanceItem]
    uncertainty: UncertaintyAssessment
    forecast_72h: list[ForecastHorizonPoint] = Field(default_factory=list)
    validation_metrics: MLValidationMetrics | None = None


class AutonomyGuardrail(BaseModel):
    human_in_the_loop_required: bool = True
    autonomous_diagnosis_blocked: bool = True
    autonomous_treatment_blocked: bool = True
    decision_authority: str = "Crew Medical Officer (CMO) Onboard / Earth Flight Surgeon (MCC-H)"
    governance_notice: str = (
        "AUDITABLE DECISION SUPPORT ONLY: AstraCare AI surfaces statistical deviations, contextual correlations, "
        "and NASA-STD-3001 / OCHMO protocol checklists. It never invents treatments or executes autonomous medical decisions."
    )


class ExplainableAlert(BaseModel):
    alert_id: str
    created_at: str
    severity: SeverityStatus
    system_id: str
    syndrome_candidate: str
    title: str
    explanation_summary: str
    originating_signals: list[dict[str, Any]] = Field(default_factory=list)
    measurement_quality: MeasurementQualityProfile
    uncertainty: UncertaintyAssessment
    contextual_factors: list[str] = Field(default_factory=list)
    causal_disclaimer: str
    scientific_references: list[dict[str, str]] = Field(default_factory=list)
    recommended_verification_steps: list[str] = Field(default_factory=list)
    autonomy_guardrail: AutonomyGuardrail = Field(default_factory=AutonomyGuardrail)
    followup_case_id: str | None = None


# --- PILLAR 3: Closed-Loop Follow-Up Cycle ---
class ConfirmationMeasurementRecord(BaseModel):
    confirmation_id: str
    recorded_at: str
    metric: str
    measured_value: float
    unit: str
    device_used: str
    signal_quality_pct: float
    confirms_anomaly: bool
    notes: str


class ExecutedActionRecord(BaseModel):
    action_id: str
    executed_at: str
    performed_by: str
    protocol_reference: str
    action_description: str
    outcome_note: str


class ScheduledReassessmentRecord(BaseModel):
    reassessment_id: str
    scheduled_for_offset_minutes: int
    target_system: str
    target_metrics: list[str]
    protocol_reason: str
    status: Literal["PENDING", "COMPLETED", "OVERDUE"] = "PENDING"
    scheduled_at: str | None = None
    due_at: str | None = None
    completed_at: str | None = None
    post_reassessment_summary: str | None = None


class ClinicalFollowUpCase(BaseModel):
    case_id: str
    alert_id: str
    astronaut_id: str
    astronaut_name: str
    mission_day: int
    system_id: str
    syndrome_code: str
    title: str
    severity: SeverityStatus
    status: FollowUpStatus
    created_at: str
    updated_at: str
    required_confirmations: list[str] = Field(default_factory=list)
    confirmations_recorded: list[ConfirmationMeasurementRecord] = Field(default_factory=list)
    recommended_protocol_actions: list[str] = Field(default_factory=list)
    actions_executed: list[ExecutedActionRecord] = Field(default_factory=list)
    reassessments_scheduled: list[ScheduledReassessmentRecord] = Field(default_factory=list)
    resolution_notes: str | None = None
    # Derived on every read so the crew/ground can see at a glance what is still owed on this case
    next_due_at: str | None = None
    overdue_reassessments: int = 0
    pending_items: list[str] = Field(default_factory=list)
    escalation_reason: str | None = None


class RecordConfirmationRequest(BaseModel):
    metric: str = Field(..., description="Metric confirmed, e.g., temperature_c, bp_systolic, glucose_mg_dl")
    measured_value: float
    unit: str = ""
    device_used: str = "CHeCS Reference Instrument (Tempus Pro / i-STAT)"
    signal_quality_pct: float = Field(98.0, ge=0.0, le=100.0)
    notes: str = "Confirmatory reading after 15-min rest protocol."


class RecordActionRequest(BaseModel):
    performed_by: str = "Crew Medical Officer (CMO)"
    protocol_reference: str = "NASA-STD-3001 / OCHMO-TB-044"
    action_description: str
    schedule_reassessment_in_minutes: int = Field(30, ge=5, le=1440)
    outcome_note: str = "Protocol step completed; monitoring crew member."


class CompleteReassessmentRequest(BaseModel):
    reassessment_id: str
    resolve_case: bool = False
    summary: str = "Reassessment completed; trend stabilizing toward personal baseline."


class EscalateCaseRequest(BaseModel):
    requested_by: str = "Crew Medical Officer (CMO)"
    reason: str = "Crew requests Flight Surgeon review."


# --- Clinical Evaluation & Legacy Compatibility ---
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
    explainable_alerts: list[ExplainableAlert] = Field(default_factory=list)
    autonomy_guardrail: AutonomyGuardrail = Field(default_factory=AutonomyGuardrail)


# --- PILLAR 5: NASA Feeds & Spacecraft-Earth Continuity ---
class SpaceWeatherEvent(BaseModel):
    event_id: str
    event_type: Literal["FLR", "SEP", "CME", "GST"]
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
    active_cme_count: int = 0
    active_gst_count: int = 0
    comms_degradation_risk: Literal["NONE", "MODERATE_HF_SCINTILLATION", "SEVERE_BLACKOUT_WINDOW"] = "NONE"
    recommended_dose_limit_msv_h: float
    alara_instruction: str
    events: list[SpaceWeatherEvent] = Field(default_factory=list)


class HorizonsLinkStatus(BaseModel):
    source: Literal["live_nasa_jpl_horizons", "curated_local_fallback"]
    fetched_at: str
    target_body: str
    distance_km: float
    distance_au: float
    one_way_light_time_seconds: float
    round_trip_light_time_seconds: float
    bandwidth_kbps: float
    link_window_status: str
    comms_available: bool = True


class EarthSyncPackage(BaseModel):
    package_id: str
    created_at: str
    synchronized_at: str | None = None
    sync_status: SyncStatus
    sha256_integrity_hash: str
    astronaut_id: str
    crew_member: str
    mission_day: int
    environment_id: str
    horizons_link: HorizonsLinkStatus
    space_weather_alert: SeverityStatus
    executive_summary: str
    adaptive_baseline_snapshot: AdaptiveBaselineProfile
    contextual_report: ContextualIntelligenceReport
    ml_prediction: MLPredictionResult
    explainable_alerts: list[ExplainableAlert]
    followup_cases: list[ClinicalFollowUpCase]
    longitudinal_series: list[dict[str, Any]]
    forecast_72h: list[ForecastHorizonPoint]
    audit_log_entries: list[dict[str, Any]]


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
    adaptive_baseline: AdaptiveBaselineProfile | None = None
    contextual_intelligence: ContextualIntelligenceReport | None = None
    active_followup_cases: list[ClinicalFollowUpCase] = Field(default_factory=list)
    earth_sync_package_id: str | None = None
    vitals_snapshot: VitalSigns
    nutrition_snapshot: NutritionHydrationState
    space_weather_alert: str
    recommended_earth_questions: list[str]


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


class ToolTraceItem(BaseModel):
    tool_name: str
    status: Literal["OK", "WARNING", "CRITICAL"] = "OK"
    summary: str
    rule_or_score: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    mode: Literal["langchain_gemini", "offline_hybrid_edge", "ml_only_stage"]
    tool_trace: list[ToolTraceItem] = Field(default_factory=list)
    state: MissionState


class ContextUpdateRequest(BaseModel):
    exercise_minutes_24h: float | None = None
    exercise_modality: Literal["ARED_resistive", "T2_treadmill", "CEVIS_cycle", "none"] | None = None
    minutes_since_last_exercise: float | None = None
    eva_status: Literal["none", "pre_eva_prebreathe", "active_eva", "post_eva_recovery"] | None = None
    hours_since_last_eva: float | None = None
    cabin_co2_mmhg: float | None = None
    cabin_o2_pct: float | None = None
    cabin_temp_c: float | None = None
    signal_quality_pct: float | None = None
    motion_artifact_detected: bool | None = None
    nibp_cuff_verified: bool | None = None


# --- PILLAR 6: Psychophysiological Biofeedback Countermeasure & Central BHP Alert System ---
class PsychIndicatorWeight(BaseModel):
    metric: str
    label: str
    current_value: float
    personal_baseline: float
    individual_z_score: float
    weight_multiplier: float
    points_contributed: float
    target_diagnosis: str
    clinical_rationale: str


class PsychStimulusItem(BaseModel):
    stimulus_id: str
    title: str
    category: Literal[
        "family_video",
        "friends_audio",
        "nature_animals_audio",
        "interactive_game_interest",
        "guided_breathing_music",
    ]
    duration_min: int
    description: str
    target_effect: str
    delivery_mode: Literal[
        "CABIN_DISPLAY_AND_AUDIO",
        "PRIVATE_CREW_QUARTERS",
        "SUIT_AUDIO_ONLY_SAFE_MODE",
    ] = "CABIN_DISPLAY_AND_AUDIO"


class CentralPsychAlertRecord(BaseModel):
    central_alert_id: str
    dispatched_at: str
    astronaut_id: str
    astronaut_name: str
    mission_day: int
    recipient_station: str = (
        "MCC-Houston Behavioral Health & Performance (BHP) Console + Earth Flight Surgeon + Onboard CMO"
    )
    primary_psych_diagnosis: str
    primary_psych_label: str
    weighted_score_0_100: float
    schedule_window: str
    triggering_indicator_weights: list[PsychIndicatorWeight] = Field(default_factory=list)
    dispatched_stimuli: list[PsychStimulusItem] = Field(default_factory=list)
    pre_stimulus_vitals: dict[str, float] = Field(default_factory=dict)
    post_stimulus_vitals: dict[str, float] = Field(default_factory=dict)
    followup_case_id: str | None = None
    earth_sync_package_id: str | None = None
    reassessment_scheduled_in_minutes: int = 15


class PsychBiofeedbackEvaluation(BaseModel):
    astronaut_id: str
    astronaut_name: str
    schedule_window: Literal[
        "MID_SHIFT_DECOMPRESSION",
        "POST_EVA_RECOVERY_WINDOW",
        "PRE_SLEEP_CIRCADIAN_WIND_DOWN",
        "IMMEDIATE_RESTING_INTERVENTION",
        "EVA_ACTIVE_VISUAL_BLOCK_SAFE_AUDIO",
    ]
    auto_trigger_recommended: bool
    operational_block_active: bool
    primary_diagnosis_code: str
    primary_diagnosis_label: str
    primary_score_0_100: float
    diagnosis_scores: dict[str, float] = Field(default_factory=dict)
    indicator_weights: list[PsychIndicatorWeight] = Field(default_factory=list)
    recommended_stimuli: list[PsychStimulusItem] = Field(default_factory=list)
    biofeedback_mechanism_summary: str
    last_triggered_alert: CentralPsychAlertRecord | None = None


class PsychTriggerRequest(BaseModel):
    reason: str = "Automated biometric threshold or crew wellness intervention"
    preferred_category: str | None = None


class MissionState(BaseModel):
    mission_day: int = 142
    astronaut_id: str = "elena_vance"
    crew_member: str = "CDR Elena Vance (EVA-1)"
    scenario_id: str
    scenario_name: str
    scenario_description: str
    environment_id: str
    environment_name: str
    one_way_latency_seconds: int
    vitals: VitalSigns
    measurement_quality: MeasurementQualityProfile
    mission_context: MissionContext
    nutrition: NutritionHydrationState
    adaptive_baseline: AdaptiveBaselineProfile
    contextual_intelligence: ContextualIntelligenceReport
    clinical_evaluation: ClinicalEvaluationResult
    ml_prediction: MLPredictionResult
    psych_biofeedback: PsychBiofeedbackEvaluation | None = None
    central_psych_alerts: list[CentralPsychAlertRecord] = Field(default_factory=list)
    explainable_alerts: list[ExplainableAlert] = Field(default_factory=list)
    followup_cases: list[ClinicalFollowUpCase] = Field(default_factory=list)
    space_weather: SpaceWeatherSummary | None = None
    horizons_link: HorizonsLinkStatus | None = None
    earth_sync_queue_count: int = 0
    earth_sync_last_package_id: str | None = None
    astronauts_catalog: list[dict[str, Any]] = Field(default_factory=list)
    longitudinal_series: list[dict[str, Any]] = Field(default_factory=list)
    scenarios_catalog: list[dict[str, Any]] = Field(default_factory=list)
    environments_catalog: list[dict[str, Any]] = Field(default_factory=list)
    indicators_guide: list[dict[str, Any]] = Field(default_factory=list)
    systems_guide: dict[str, Any] = Field(default_factory=dict)
    last_updated: str


ChatResponse.model_rebuild()
MeasurementResponse.model_rebuild()
