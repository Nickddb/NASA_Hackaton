from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agent.orchestrator import AstraCareOrchestrator
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    MeasurementResponse,
    MissionState,
    SpaceWeatherSummary,
    TelemedicineDossier,
)
from app.state_manager import MissionStateManager

state_manager = MissionStateManager()
orchestrator = AstraCareOrchestrator(state_manager)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup is instantaneous offline-first; live NASA DONKI is queried on-demand via /api/nasa/space-weather
    yield


app = FastAPI(
    title="AstraCare AI API",
    version="0.1.0",
    description="Autonomous Offline-First Spaceflight Medical Officer Backend (NASA-STD-3001 + ML + LangChain)",
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
def health_check() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "AstraCare AI Medical Officer",
        "ml_models_ready": bool(state_manager.ml_predictor.classes_),
        "ml_classes": state_manager.ml_predictor.classes_,
        "scenario": state_manager.scenario_id,
        "environment": state_manager.environment_id,
    }


@app.get("/api/state", response_model=MissionState)
def get_mission_state() -> MissionState:
    return state_manager.get_state()


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


@app.post("/api/agent/chat", response_model=ChatResponse)
async def agent_chat(payload: ChatRequest) -> ChatResponse:
    return await orchestrator.handle_chat(payload.message)


@app.get("/api/nasa/space-weather", response_model=SpaceWeatherSummary)
async def get_space_weather() -> SpaceWeatherSummary:
    return await state_manager.refresh_space_weather()


@app.post("/api/telemedicine/dossier", response_model=TelemedicineDossier)
def generate_telemedicine_dossier() -> TelemedicineDossier:
    return state_manager.compile_dossier()


# Optional SPA static hosting if frontend/dist is already built
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
