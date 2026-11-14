# AstraCare AI — Development Plan (`plan.md`)

> **Challenge:** NASA Space Apps Challenge 2026 — *05. Create Health Monitoring Software for Astronauts on Space Missions* (AEB / Rodrigo Leonardi)  
> **Project Board:** https://github.com/users/Nickddb/projects/5  
> **Task Breakdown & Model Allocation:** [TASKS.md](TASKS.md)  
> **Target UI Language:** English (`EN`) — aligned with NASA Space Apps 2026 judging & submission rules.

---

## 1. Product Vision & Core Differentiator

**AstraCare AI** is an autonomous, offline-first onboard medical officer for long-duration space missions (Deep Space Transit, Orbital Stations, and Lunar/Martian Surfaces) where Earth communication latency (up to ~20 min each way on Mars) prevents real-time flight surgeon intervention.

Our primary differentiator is the **AI Agent (`AstraCare Medical Officer`)**, which combines:
1. **Deterministic NASA-STD-3001 Clinical Rules** (safety-first primary guardrail),
2. **Predictive Machine Learning (`scikit-learn`)** for multivariate anomaly detection and syndrome classification, and
3. **LangChain Tool-Calling Agent + LLM** (with automatic offline-first deterministic/NLP fallback) to guide non-medical astronauts step by step.

---

## 2. Tech Stack

- **Frontend (`frontend/`):**
  - **Vite + React + Tailwind CSS**
  - **Three.js / React Three Fiber (`@react-three/fiber`, `@react-three/drei`)** — procedural holographic 3D anatomical body model
  - **Recharts** — vital-sign trend charts & nutrition/sleep progress
  - **Lucide React** — medical & mission-control iconography
- **Backend (`backend/`):**
  - **Python 3.12 (via `uv`) + FastAPI**
  - **LangChain (`langchain`, `langchain-core`, `langchain-google-genai`)** — agent orchestration & tool calling
  - **Machine Learning (`scikit-learn`, `numpy`, `pandas`)** — `IsolationForest` + `RandomForestClassifier`
  - **NASA Real Data:** `httpx` client for **NASA DONKI API** (`FLR` / `SEP` solar radiation events) with local fallback (`nasa_donki_sample.json`)

---

## 3. AI Agent Architecture (3-Layer Hybrid Edge AI)

1. **Layer 1 — Deterministic Clinical Safety (`clinical_rules.py`):**
   - Evaluates 8 core indicators: Heart Rate & HRV, Blood Pressure, Blood Glucose, Body Temperature, Sleep & Circadian Rhythm (using [polissonografia.md](docs/pesquisas/polissonografia.md) & [dessincronia-circadiana.md](docs/materiais/dessincronia-circadiana.md) as clinical references), Mood/Cognitive Load, Absorbed Radiation Dose, and Nutrition/Hydration Balance.
   - Classifies 6 anatomical systems (`cardiovascular`, `nervous_sleep`, `respiratory`, `metabolic`, `musculoskeletal`, `radiation`) into `NOMINAL` (Green), `WARNING` (Yellow), or `CRITICAL` (Red).
   - Evaluates the 5 combined predictive scenarios from [astracare-ai-visao-geral.md](docs/astracare-ai-visao-geral.md):
     1. *Systemic Infection / Acute Viral State* (`CRITICAL`)
     2. *Orthostatic Intolerance / Fluid Shift Hypotension* (`WARNING`)
     3. *Severe Behavioral Fatigue & Circadian Desynchrony* (`CRITICAL`)
     4. *Caloric-Deficit Hypoglycemia* (`WARNING`)
     5. *Solar Particle Event (SPE) Acute Radiation Spike* (`CRITICAL`)
   - Applies environment-specific calibration: `Deep Space Transit` (0g fluid-shift correction), `Orbital Station` (circadian lighting sync), and `Planetary Surface` (mandatory lunar regolith / Martian dust decontamination checklist before active exams).

2. **Layer 2 — Predictive Machine Learning (`ml_predictor.py`):**
   - Trained in `< 0.5s` on server startup using a calibrated synthetic astronaut dataset (inspired by NASA OSDR / Standard Measures):
     - **`IsolationForest`:** outputs a continuous `anomaly_score` (0–100%) to catch subtle multivariate drift before thresholds are breached.
     - **`RandomForestClassifier`:** predicts probabilities across the 6 mission states and extracts `feature_importances` so the UI explains *which* vitals drove the alert.

3. **Layer 3 — LangChain Orchestrator (`agent/tools.py` & `agent/orchestrator.py`):**
   - **6 `@tool` Functions:**
     1. `evaluate_clinical_rules_tool`
     2. `predict_ml_risk_tool`
     3. `check_nasa_donki_weather_tool`
     4. `log_nutrition_hydration_tool` (natural language parsing, e.g., *"I ate 2 apples and drank 500ml of water"*)
     5. `log_sleep_mood_checkin_tool`
     6. `compile_telemedicine_dossier_tool`
   - **Hybrid Execution:** Uses Gemini via LangChain when `GEMINI_API_KEY` is present; automatically falls back to deterministic local tool-pipeline + regex/heuristic NLP when offline or without an API key.

---

## 4. Target Folder Structure

```text
NASA_Hackaton/
├── backend/
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── models/schemas.py
│       ├── engine/
│       │   ├── clinical_rules.py
│       │   ├── ml_predictor.py
│       │   └── nasa_donki.py
│       ├── agent/
│       │   ├── tools.py
│       │   └── orchestrator.py
│       └── data/
│           ├── scenarios.json
│           └── nasa_donki_sample.json
├── frontend/
│   ├── package.json
│   └── src/
│       ├── components/
│       │   ├── BodyModel3D.jsx
│       │   ├── SmartwatchSim.jsx
│       │   ├── VitalsDashboard.jsx
│       │   ├── AgentChatPanel.jsx
│       │   ├── EmergencyProtocol.jsx
│       │   └── TelemedDossier.jsx
│       ├── services/api.js
│       └── App.jsx
├── docs/
├── scripts/sync_github_project.mjs
├── DESIGN.md
├── TASKS.md
├── plan.md
├── CHALLENGE.md
├── SOURCES.md
├── AGENTS.md
└── README.md
```

---

## 5. Backend API Contract

- `GET /api/health` — Service health & ML model readiness check.
- `GET /api/state` — Full current mission state (vitals, nutrition/hydration goals, environment, 3D system statuses, rules evaluation, ML prediction, active alerts).
- `POST /api/scenario/{scenario_id}` — Switch mission scenario (`nominal`, `systemic_infection`, `orthostatic_intolerance`, `behavioral_fatigue`, `hypoglycemia`, `solar_storm`) or environment (`transit`, `orbital_station`, `planetary_surface`).
- `POST /api/measure/{system_id}` — Trigger manual exam from the 3D body model or smartwatch (returns decontamination checklist if on `planetary_surface`).
- `POST /api/agent/chat` — Send astronaut message to LangChain agent; runs tools, updates state, returns guidance + `tool_trace` badges.
- `GET /api/nasa/space-weather` — Live NASA DONKI `FLR`/`SEP` solar events with local fallback.
- `POST /api/telemedicine/dossier` — Compile structured pre-consultation clinical dossier with Mars communication latency simulation.

---

## 6. Execution Order & Effort Policy

- **Effort Policy:** All tasks default to **`Medium`** effort (`Gemini 3.8 Flash (Medium)`, `Gemini 4 Hydrogen (Medium)`, `Gemini 4 Argon (Medium)`, `Claude Sonnet 5.5 (Medium)`, `Claude Opus 5.5 (Medium)`). **`High`** is reserved strictly as a last-resort fallback for `T13`, `T14`, and `T15`. All fallbacks are **100% Gemini**.
- **Execution Blocks:**
  1. **Block 1 (Foundation):** `T01` (`DESIGN.md`) → `T02` (FastAPI + `uv`) & `T04` (`scenarios.json`) → `T03` (Vite + React + Tailwind + R3F).
  2. **Block 2 (AI & Clinical Core):** `T06` (`clinical_rules.py`) + `T07` (`nasa_donki.py`) + `T13` (`ml_predictor.py`) → `T14` (LangChain Agent + 6 Tools).
  3. **Block 3 (Cockpit & 3D):** `T15` (`BodyModel3D.jsx`) + `T08` (`VitalsDashboard.jsx`) + `T09` (`SmartwatchSim.jsx`).
  4. **Block 4 (Agent UI & Emergency):** `T16` (`AgentChatPanel.jsx`) + `T10` (`EmergencyProtocol.jsx`) + `T11` (`TelemedDossier.jsx`).
  5. **Block 5 (Ship & Submit):** `T12` (Public Deploy without login) → `T05` (`README.md`, `SUBMISSION.md`, `DEMO.md`, `pitch-deck`).
