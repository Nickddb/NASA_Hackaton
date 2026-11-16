# AstraCare AI — Autonomous Spaceflight Medical Officer

> **Built with NASA Data • NASA-STD-3001 & OCHMO Clinical Standards**  
> **NASA Space Apps Challenge 2026:** *05. Create Health Monitoring Software for Astronauts on Space Missions*

**AstraCare AI** is an autonomous, offline-first onboard medical officer designed for long-duration spaceflight (Deep Space Transit, Orbital Stations, and Lunar/Martian Surfaces), where communication latency with Earth (up to ~20 minutes one-way from Mars) prevents real-time Flight Surgeon intervention.

---

## Key Features

- **3-Layer Hybrid Edge AI Architecture:**
  1. **Layer 1 — Deterministic Clinical Safety Engine (`clinical_rules.py`):** Evaluates 8 core indicators (Heart Rate & HRV, Blood Pressure, Blood Glucose, Body Temperature, Sleep & Circadian Rhythm, Mood & Cognitive Load, Absorbed Radiation Dose, and Nutrition/Hydration Balance) across 6 anatomical systems (`NOMINAL`, `WARNING`, `CRITICAL`), enforces NASA Space Food caps (`Sodium <= 3500 mg/day`, `Iron <= 10 mg/day`), and detects 5 multi-variable spaceflight syndromes plus `OCHMO-MTB-006` (EVA Shoulder Injury), `OCHMO-MTB-009` (Circadian Desynchrony), `OCHMO-MTB-011` (PFO / EVA Decompression Risk), and `OCHMO-TB-043` (LHS / SANS).
  2. **Layer 2 — Predictive Machine Learning (`ml_predictor.py`):** Trains `IsolationForest` (continuous `0–100%` anomaly score) and `RandomForestClassifier` (syndrome probabilities + case-specific *Feature Importance* attribution) on startup over a calibrated synthetic astronaut physiological cohort.
  3. **Layer 3 — LangChain Tool-Calling Agent (`agent/tools.py` & `agent/orchestrator.py`):** Exposes 6 `@tool` functions with optional Gemini (`GEMINI_API_KEY`) orchestration and an automatic deterministic + NLP offline-first fallback.
- **Interactive 3D Anatomical Holo-Scanner (`BodyModel3D.jsx`):** Three.js / React Three Fiber 3D body with 6 clickable systems, *"How to Measure / Why It Matters"* CHeCS hardware guides, and a mandatory **Planetary Surface Regolith Decontamination Checklist** before active surface exams.
- **Biometric Smartwatch Simulator & Live NASA DONKI Weather (`SmartwatchSim.jsx` & `nasa_donki.py`):** Live edge telemetry, 6 mission scenario presets, 3 space environments, and NASA DONKI Solar Flare (`FLR`) / Solar Particle Event (`SEP`) feeds with curated local fallback.
- **Critical Emergency Protocol ("B.O.") & MORD Telemedicine Dossier (`EmergencyProtocol.jsx` & `TelemedDossier.jsx`):** Auto-triggers stabilization checklists on `CRITICAL` alerts and compiles `OCHMO-TB-044` MORD pre-consultation bundles with Mars light-time latency simulation.

---

## How to Run Locally

### 1. Backend (Python + FastAPI + `uv`)
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```
*(Optional: set `GEMINI_API_KEY` for live Gemini LangChain reasoning and `NASA_API_KEY` for higher-quota NASA DONKI calls; otherwise AstraCare runs 100% offline-first.)*

### 2. Frontend (Vite + React + Tailwind + Three.js)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`. For a single-server production build, run `npm run build` in `frontend/` and launch `uvicorn app.main:app --port 8000` in `backend/` (FastAPI automatically serves `frontend/dist`).

---

## Sources & References
All NASA datasets, OCHMO Technical Briefs, CSA partner resources, and open-source libraries are documented in [SOURCES.md](SOURCES.md).
