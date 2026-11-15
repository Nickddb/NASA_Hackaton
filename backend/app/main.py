from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
    CrewRosterResponse,
    DispatchAlertRequest,
    EarthSyncPackage,
    EscalateCaseRequest,
    ExplainableAlert,
    MeasurementResponse,
    MissionState,
    MLValidationMetrics,
    PsychBiofeedbackEvaluation,
    PsychTriggerRequest,
    RecordActionRequest,
    RecordConfirmationRequest,
    SpaceWeatherSummary,
    StabilizeRequest,
    TelemedicineDossier,
)
from app.state_manager import MissionStateManager

state_manager = MissionStateManager()
orchestrator = AstraCareOrchestrator(state_manager)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Pull NASA DONKI once at start-up without blocking it; offline -> cache/sample is already loaded.
    task = asyncio.create_task(state_manager.refresh_space_weather())
    yield
    task.cancel()


app = FastAPI(
    title="AstraCare AI — Real ML & Clinical Continuity Backend",
    version="0.3.0",
    description=(
        "6-Pillar Aerospace Medical Backend + Multi-Crew Hub: "
        "(1) Adaptive Individual Baseline, "
        "(2) Contextual Mission Intelligence, "
        "(3) Closed-Loop Follow-Up Cycle, "
        "(4) Explainable & Auditable Calibrated ML, "
        "(5) Spacecraft–Earth Store-and-Forward Continuity, "
        "(6) Psychophysiological Biofeedback Countermeasure & Central BHP Alert."
    ),
    lifespan=lifespan,
)


@app.exception_handler(ValueError)
async def invalid_transition_handler(_: Request, exc: ValueError) -> JSONResponse:
    # e.g. trying to modify a follow-up case that is already RESOLVED
    return JSONResponse(status_code=409, content={"detail": str(exc)})


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
        "service": "AstraCare AI Real ML & Clinical Continuity Engine",
        "ml_models_ready": bool(state_manager.ml_predictor.classes_),
        "ml_classes": state_manager.ml_predictor.classes_,
        "ml_validation": state_manager.ml_predictor.validation_metrics.model_dump()
        if state_manager.ml_predictor.validation_metrics
        else None,
        "astronaut_id": state_manager.astronaut_id,
        "active_crew_id": state_manager.active_crew_id,
        "total_crew": len(state_manager.crew_records),
        "scenario": state_manager.scenario_id,
        "environment": state_manager.environment_id,
        "pending_earth_sync_packages": state_manager.earth_sync.pending_count(),
    }


@app.get("/api/state", response_model=MissionState)
def get_mission_state(crew_id: str | None = None) -> MissionState:
    return state_manager.get_state(crew_id=crew_id)


# --- Multi-Crew Hub Endpoints ---
@app.get("/api/crew", response_model=CrewRosterResponse)
def get_crew_roster() -> CrewRosterResponse:
    return state_manager.get_crew_roster()


@app.post("/api/crew/{crew_id}/select", response_model=MissionState)
def select_crew_member(crew_id: str) -> MissionState:
    try:
        return state_manager.select_crew_member(crew_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/crew/{crew_id}/state", response_model=MissionState)
def get_crew_member_state(crew_id: str) -> MissionState:
    if crew_id not in state_manager.crew_records:
        raise HTTPException(status_code=404, detail=f"Unknown crew_id: {crew_id}")
    return state_manager.get_state(crew_id=crew_id)


@app.post("/api/crew/{crew_id}/alert", response_model=MissionState)
def dispatch_crew_alert(crew_id: str, payload: DispatchAlertRequest) -> MissionState:
    try:
        return state_manager.dispatch_alert(crew_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/crew/{crew_id}/acknowledge", response_model=MissionState)
def acknowledge_crew_alert(crew_id: str) -> MissionState:
    try:
        return state_manager.acknowledge_alert(crew_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/crew/{crew_id}/stabilize", response_model=MissionState)
def stabilize_crew_member(
    crew_id: str, payload: StabilizeRequest | None = None
) -> MissionState:
    try:
        return state_manager.stabilize_crew_member(crew_id, payload or StabilizeRequest())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/crew/{crew_id}/measure", response_model=MeasurementResponse)
def measure_crew_member(
    crew_id: str, system_id: str = "full_body"
) -> MeasurementResponse:
    try:
        return state_manager.trigger_measurement(system_id, crew_id=crew_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- PILLAR 1: Adaptive Individual Baseline Endpoints ---
@app.post("/api/astronaut/{astronaut_id}", response_model=MissionState)
def set_astronaut(astronaut_id: str) -> MissionState:
    try:
        return state_manager.switch_astronaut(astronaut_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/ml/baseline", response_model=AdaptiveBaselineProfile)
def get_adaptive_baseline(crew_id: str | None = None) -> AdaptiveBaselineProfile:
    return state_manager.get_state(crew_id=crew_id).adaptive_baseline


# --- PILLAR 2: Contextual Mission Intelligence Endpoints ---
@app.get("/api/ml/context", response_model=ContextualIntelligenceReport)
def get_contextual_intelligence(crew_id: str | None = None) -> ContextualIntelligenceReport:
    return state_manager.get_state(crew_id=crew_id).contextual_intelligence


@app.post("/api/ml/context", response_model=MissionState)
def update_contextual_covariates(
    payload: ContextUpdateRequest, crew_id: str | None = None
) -> MissionState:
    return state_manager.update_context(payload, crew_id=crew_id)


# --- PILLAR 3: Closed-Loop Follow-Up Cycle Endpoints ---
@app.get("/api/followup/cases", response_model=list[ClinicalFollowUpCase])
def list_followup_cases(crew_id: str | None = None) -> list[ClinicalFollowUpCase]:
    return state_manager.get_state(crew_id=crew_id).followup_cases


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


@app.post("/api/followup/{case_id}/escalate", response_model=ClinicalFollowUpCase)
def escalate_case(case_id: str, payload: EscalateCaseRequest | None = None) -> ClinicalFollowUpCase:
    """Human-requested escalation to the Earth Flight Surgeon (the AI never escalates on its own)."""
    try:
        return state_manager.escalate_followup_case(case_id, payload or EscalateCaseRequest())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- PILLAR 4: Explainable & Auditable ML Endpoints ---
@app.get("/api/ml/validation", response_model=MLValidationMetrics)
def get_ml_validation_metrics() -> MLValidationMetrics:
    if state_manager.ml_predictor.validation_metrics is None:
        raise HTTPException(status_code=500, detail="Validation metrics not initialized")
    return state_manager.ml_predictor.validation_metrics


@app.get("/api/ml/alerts", response_model=list[ExplainableAlert])
def get_explainable_alerts(crew_id: str | None = None) -> list[ExplainableAlert]:
    return state_manager.get_state(crew_id=crew_id).explainable_alerts


# --- PILLAR 5: Spacecraft–Earth Continuity Endpoints ---
@app.post("/api/earth-sync/package", response_model=EarthSyncPackage)
def create_sync_package() -> EarthSyncPackage:
    return state_manager.create_earth_sync_package()


@app.post("/api/earth-sync/synchronize", response_model=list[EarthSyncPackage])
def synchronize_with_earth() -> list[EarthSyncPackage]:
    return state_manager.synchronize_with_earth()


@app.get("/api/earth-sync/verify")
def verify_earth_sync_ledger() -> dict[str, Any]:
    """Recompute the package and audit hash chains (what ground does on receipt)."""
    return state_manager.earth_sync.verify_integrity()


@app.get("/api/earth-sync/ledger")
def get_earth_sync_ledger() -> dict[str, Any]:
    return {
        "pending_queue_count": state_manager.earth_sync.pending_count(),
        "packages": [p.model_dump() for p in state_manager.earth_sync.packages[-10:]],
        "audit_log": state_manager.earth_sync.audit_log[-25:],
    }


# --- PILLAR 6: Psychophysiological Biofeedback Countermeasure & Central BHP Alert Endpoints ---
@app.get("/api/psych/evaluation", response_model=PsychBiofeedbackEvaluation)
def get_psych_evaluation(crew_id: str | None = None) -> PsychBiofeedbackEvaluation:
    st = state_manager.get_state(crew_id=crew_id)
    if st.psych_biofeedback is None:
        raise HTTPException(status_code=500, detail="Psychophysiological evaluation not available")
    return st.psych_biofeedback


@app.post("/api/psych/trigger", response_model=CentralPsychAlertRecord)
def trigger_psych_countermeasure(payload: PsychTriggerRequest | None = None) -> CentralPsychAlertRecord:
    reason = payload.reason if payload else "Manual or scheduled biometric countermeasure trigger"
    return state_manager.trigger_psychological_biofeedback(reason=reason)


@app.get("/api/psych/central-alerts", response_model=list[CentralPsychAlertRecord])
def list_central_psych_alerts(crew_id: str | None = None) -> list[CentralPsychAlertRecord]:
    return state_manager.get_state(crew_id=crew_id).central_psych_alerts


# --- Core Mission Scenarios, Measurements & NASA Feeds ---
@app.post("/api/scenario/{scenario_id}", response_model=MissionState)
def set_scenario(scenario_id: str, crew_id: str | None = None) -> MissionState:
    try:
        return state_manager.switch_scenario(scenario_id, crew_id=crew_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/environment/{env_id}", response_model=MissionState)
def set_environment(env_id: str, crew_id: str | None = None) -> MissionState:
    try:
        return state_manager.switch_environment(env_id, crew_id=crew_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/measure/{system_id}", response_model=MeasurementResponse)
def trigger_measurement(system_id: str, crew_id: str | None = None) -> MeasurementResponse:
    try:
        return state_manager.trigger_measurement(system_id, crew_id=crew_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/nasa/space-weather", response_model=SpaceWeatherSummary)
async def get_space_weather(force: bool = False) -> SpaceWeatherSummary:
    """NASA DONKI SEP/FLR/RBE summary. Uses a 30-min cache to respect the DEMO_KEY quota; force=true bypasses it."""
    return await state_manager.refresh_space_weather(force=force)


@app.post("/api/telemetry/next", response_model=MissionState)
def next_telemetry_reading(
    crisis_probability: float = 0.0, crew_id: str | None = None
) -> MissionState:
    """New reading from the NASA-calibrated stochastic generator. crisis_probability (0-1) lets a nominal
    mission randomly enter a crisis profile."""
    if not 0.0 <= crisis_probability <= 1.0:
        raise HTTPException(status_code=422, detail="crisis_probability must be between 0 and 1")
    return state_manager.next_telemetry_reading(crisis_probability, crew_id=crew_id)


@app.post("/api/telemedicine/dossier", response_model=TelemedicineDossier)
def generate_telemedicine_dossier(crew_id: str | None = None) -> TelemedicineDossier:
    return state_manager.compile_dossier(crew_id=crew_id)


@app.post("/api/agent/chat", response_model=ChatResponse)
async def agent_chat(payload: ChatRequest) -> ChatResponse:
    """Phase 2 Agentic Chatbot & Clinical Decision-Support Orchestrator (10 Tools across 6 Pillars)."""
    return await orchestrator.handle_chat(payload.message, crew_id=payload.crew_id)


# --- Optional Static Frontend Hosting (SPA) ---
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="Frontend build not found")
