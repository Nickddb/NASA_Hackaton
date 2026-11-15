from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.orchestrator import AstraCareOrchestrator
from app.models.schemas import (
    AdaptiveBaselineProfile,
    CentralPsychAlertRecord,
    ChatRequest,
    ChatResponse,
    ClinicalFollowUpCase,
    CompleteReassessmentRequest,
    ContextualIntelligenceReport,
    ContextUpdateRequest,
    EarthSyncPackage,
    ExplainableAlert,
    MeasurementResponse,
    MissionState,
    MLValidationMetrics,
    PsychBiofeedbackEvaluation,
    PsychTriggerRequest,
    RecordActionRequest,
    RecordConfirmationRequest,
    SpaceWeatherSummary,
    TelemedicineDossier,
)
from app.state_manager import MissionStateManager

state_manager = MissionStateManager()
orchestrator = AstraCareOrchestrator(state_manager)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="AstraCare AI — Real ML & Clinical Continuity Backend (Teste)",
    version="0.2.0",
    description=(
        "5-Pillar Aerospace Medical Backend: "
        "(1) Adaptive Individual Baseline, "
        "(2) Contextual Mission Intelligence, "
        "(3) Closed-Loop Follow-Up Cycle, "
        "(4) Explainable & Auditable Calibrated ML, "
        "(5) Spacecraft–Earth Store-and-Forward Continuity."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "AstraCare AI Real ML & Clinical Continuity Engine (teste)",
        "ml_models_ready": bool(state_manager.ml_predictor.classes_),
        "ml_classes": state_manager.ml_predictor.classes_,
        "ml_validation": state_manager.ml_predictor.validation_metrics.model_dump()
        if state_manager.ml_predictor.validation_metrics
        else None,
        "astronaut_id": state_manager.astronaut_id,
        "scenario": state_manager.scenario_id,
        "environment": state_manager.environment_id,
        "pending_earth_sync_packages": state_manager.earth_sync.pending_count(),
    }


@app.get("/api/state", response_model=MissionState)
def get_mission_state() -> MissionState:
    return state_manager.get_state()


# --- PILLAR 1: Adaptive Individual Baseline Endpoints ---
@app.post("/api/astronaut/{astronaut_id}", response_model=MissionState)
def set_astronaut(astronaut_id: str) -> MissionState:
    try:
        return state_manager.switch_astronaut(astronaut_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/ml/baseline", response_model=AdaptiveBaselineProfile)
def get_adaptive_baseline() -> AdaptiveBaselineProfile:
    return state_manager.get_state().adaptive_baseline


# --- PILLAR 2: Contextual Mission Intelligence Endpoints ---
@app.get("/api/ml/context", response_model=ContextualIntelligenceReport)
def get_contextual_intelligence() -> ContextualIntelligenceReport:
    return state_manager.get_state().contextual_intelligence


@app.post("/api/ml/context", response_model=MissionState)
def update_contextual_covariates(payload: ContextUpdateRequest) -> MissionState:
    return state_manager.update_context(payload)


# --- PILLAR 3: Closed-Loop Follow-Up Cycle Endpoints ---
@app.get("/api/followup/cases", response_model=list[ClinicalFollowUpCase])
def list_followup_cases() -> list[ClinicalFollowUpCase]:
    return state_manager.get_state().followup_cases


@app.post("/api/followup/{case_id}/confirm", response_model=ClinicalFollowUpCase)
def confirm_measurement(case_id: str, payload: RecordConfirmationRequest) -> ClinicalFollowUpCase:
    try:
        return state_manager.record_followup_confirmation(case_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/followup/{case_id}/action", response_model=ClinicalFollowUpCase)
def record_protocol_action(case_id: str, payload: RecordActionRequest) -> ClinicalFollowUpCase:
    try:
        return state_manager.record_followup_action(case_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/followup/{case_id}/reassess", response_model=ClinicalFollowUpCase)
def complete_reassessment(case_id: str, payload: CompleteReassessmentRequest) -> ClinicalFollowUpCase:
    try:
        return state_manager.complete_followup_reassessment(case_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- PILLAR 4: Explainable & Auditable ML Endpoints ---
@app.get("/api/ml/validation", response_model=MLValidationMetrics)
def get_ml_validation_metrics() -> MLValidationMetrics:
    if state_manager.ml_predictor.validation_metrics is None:
        raise HTTPException(status_code=500, detail="Validation metrics not initialized")
    return state_manager.ml_predictor.validation_metrics


@app.get("/api/ml/alerts", response_model=list[ExplainableAlert])
def get_explainable_alerts() -> list[ExplainableAlert]:
    return state_manager.get_state().explainable_alerts


# --- PILLAR 5: Spacecraft–Earth Continuity Endpoints ---
@app.post("/api/earth-sync/package", response_model=EarthSyncPackage)
def create_sync_package() -> EarthSyncPackage:
    return state_manager.create_earth_sync_package()


@app.post("/api/earth-sync/synchronize", response_model=list[EarthSyncPackage])
def synchronize_with_earth() -> list[EarthSyncPackage]:
    return state_manager.earth_sync.synchronize_queued_packages()


@app.get("/api/earth-sync/ledger")
def get_earth_sync_ledger() -> dict[str, Any]:
    return {
        "pending_queue_count": state_manager.earth_sync.pending_count(),
        "packages": [p.model_dump() for p in state_manager.earth_sync.packages[-10:]],
        "audit_log": state_manager.earth_sync.audit_log[-25:],
    }


# --- PILLAR 6: Psychophysiological Biofeedback Countermeasure & Central BHP Alert Endpoints ---
@app.get("/api/psych/evaluation", response_model=PsychBiofeedbackEvaluation)
def get_psych_evaluation() -> PsychBiofeedbackEvaluation:
    st = state_manager.get_state()
    if st.psych_biofeedback is None:
        raise HTTPException(status_code=500, detail="Psychophysiological evaluation not available")
    return st.psych_biofeedback


@app.post("/api/psych/trigger", response_model=CentralPsychAlertRecord)
def trigger_psych_countermeasure(payload: PsychTriggerRequest | None = None) -> CentralPsychAlertRecord:
    reason = payload.reason if payload else "Manual or scheduled biometric countermeasure trigger"
    return state_manager.trigger_psychological_biofeedback(reason=reason)


@app.get("/api/psych/central-alerts", response_model=list[CentralPsychAlertRecord])
def list_central_psych_alerts() -> list[CentralPsychAlertRecord]:
    return state_manager.get_state().central_psych_alerts


# --- Core Mission Scenarios, Measurements & NASA Feeds ---
@app.post("/api/scenario/{scenario_id}", response_model=MissionState)
def set_scenario(scenario_id: str) -> MissionState:
    try:
        return state_manager.switch_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/environment/{env_id}", response_model=MissionState)
def set_environment(env_id: str) -> MissionState:
    try:
        return state_manager.switch_environment(env_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/measure/{system_id}", response_model=MeasurementResponse)
def trigger_measurement(system_id: str) -> MeasurementResponse:
    try:
        return state_manager.trigger_measurement(system_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/nasa/space-weather", response_model=SpaceWeatherSummary)
async def get_space_weather() -> SpaceWeatherSummary:
    return await state_manager.refresh_space_weather()


@app.post("/api/telemedicine/dossier", response_model=TelemedicineDossier)
def generate_telemedicine_dossier() -> TelemedicineDossier:
    return state_manager.compile_dossier()


@app.post("/api/agent/chat", response_model=ChatResponse)
async def agent_chat(payload: ChatRequest) -> ChatResponse:
    """Phase 2 Agentic Chatbot & Clinical Decision-Support Orchestrator (9 Tools across 5 Pillars)."""
    return await orchestrator.handle_chat(payload.message)
