# AstraCare AI — Autonomous Spaceflight Medical Officer

> **NASA Space Apps Challenge 2026 · Challenge 05:** *Create Health Monitoring Software for Astronauts on Space Missions*
> Built with NASA data · NASA-STD-3001 & OCHMO clinical standards

On a Mars mission a message to Earth takes **3 to 22 minutes each way**. When a fever, a solar particle event or a sleepless week hits, the crew cannot wait for a Flight Surgeon. **AstraCare AI** is an offline-first onboard medical officer that watches every crew member against their **own** baseline, explains *why* something is wrong, tells a non-medical astronaut what to do next, and keeps a tamper-evident record for Earth.

It never diagnoses or treats on its own: every action is a NASA-STD-3001 / OCHMO checklist that the Crew Medical Officer or the Earth Flight Surgeon confirms.

---

## What it does

| Screen | What the crew sees |
| --- | --- |
| **Crew** | All 5 astronauts at a glance (ISS orbit and deep-space transit), traffic-light status, alerts that cannot be silenced until a new reading is back inside the personal baseline. |
| **Vitals** | Personal-baseline vitals, a realistic **3D anatomical body split into 25 selectable parts** (tap where it hurts), "How to measure / Why it matters" guides, trends and a full-body exam. |
| **Diagnosis** | The **cause tree** (nominal → space weather → onboard environment / physiology → psychological), explainable alerts, baseline & context, and the **Ship ↔ Earth link** with the live light-time delay. |
| **Mind** | Behavioural-health readiness per astronaut and the psychological countermeasure (Personal Crew Vault: family videos, friends' audio messages, nature and animal sounds, interest-based games). |
| **Assistant** | A tool-calling AI medical officer that chains exams, diagnosis, central alerts and countermeasures in natural language (EN/PT). |
| **Environment** | Live NASA DONKI space weather and the mission habitats (deep-space transit, orbital station, planetary surface). |

## How it works

```
 Smartwatch telemetry ─┐                      ┌─> Crew alert + checklist (NASA-STD-3001 / OCHMO)
 Pain map (3D body) ───┤   Personal baseline  │
 Sleep / mood / meals ─┼─> + NASA thresholds ─┼─> Cause tree ──> Psychological countermeasure
 NASA DONKI (SEP/FLR/RBE)  + calibrated ML    │      (DONKI first, psych only by exclusion)
 NASA JPL Horizons ────┘   + context          └─> SHA-256 store-and-forward package to Earth
                                                   (sent when the JPL Horizons link window allows)
```

1. **Adaptive individual baseline** — EWMA + MAD per astronaut, Ledoit-Wolf Mahalanobis distance, OSDR gravity-phase priors, quarantine of anomalous readings so a slow pathological drift is not learned as "normal".
2. **Contextual mission intelligence** — exercise (ARED/T2/CEVIS), EVA, sleep, cabin CO₂ and gravity phase explain benign deviations; correlations are explicitly *not* treated as causes.
3. **Calibrated, explainable ML** — an ensemble of HistGradientBoosting + RandomForest (Platt-calibrated) + IsolationForest over **26 features** (vitals, context, DONKI activity, crew-reported pain and symptoms, personal z-scores) classifies **8 syndromes** (nominal, systemic infection, orthostatic intolerance, behavioural fatigue, hypoglycaemia, solar storm, post-exercise physiology, cabin CO₂ pocket), with epistemic + sensor uncertainty, counterfactual attribution and a 72 h forecast.
4. **Cross-diagnosis cause tree** — checks live **NASA DONKI** space weather before blaming the body, and calls a behavioural change *psychological* only when no physical or external cause explains it.
5. **Closed-loop follow-up** — every alert opens a case: confirmation measurement → crew action → timed reassessment → resolved or escalated by a human.
6. **Spacecraft–Earth continuity** — hash-chained store-and-forward packages and audit log; the one-way delay comes from the live Earth–Mars range in **NASA JPL Horizons**.

### The AI agent (tool chaining)

The agent has **16 tools** (on Groq's free tier it offers the model a 7-tool subset by default, configurable). Four of them form a monitoring chain where each output decides the next call:

`schedule_smartwatch_exam` → `analyze_telemetry_and_diagnose` → `trigger_central_alert` (CRITICAL or escalated WARNING) → `activate_psychological_stimuli` (only when the cause is psychological)

- **LLM:** Qwen 3.8 27B on **Groq** (free tier) by default; Gemini is supported as an alternative.
- **Offline-first:** with no key, no network or a provider error, a deterministic bilingual pipeline runs the same tools and the same chain.
- **Autonomous mode:** scheduled smartwatch exams run the whole chain in the background.

## Real NASA data in use

| Source | How AstraCare uses it |
| --- | --- |
| **NASA DONKI** (`api.nasa.gov`, SEP / FLR / RBE) | Live space-weather events feed the cause tree and the ML; 30-min cache, per-feed fallback, curated sample offline. |
| **NASA JPL Horizons** (`ssd.jpl.nasa.gov/api/horizons.api`) | Live Earth–Mars range → one-way light-time delay for deep-space crews; 6 h cache and offline fallback. |
| **NASA-STD-3001, OCHMO briefs, HRP risks, OSDR** | Thresholds, protocols, gravity-phase priors and the calibration of the telemetry generator (`backend/app/engine/nasa_calibration.py`, each value with its source). |

Full list: [docs/instruções/SOURCES.md](docs/instruções/SOURCES.md).

## Tech stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, scikit-learn, NumPy, Pandas, HTTPX. 71 automated tests (`pytest`).
- **Frontend:** React 19, Vite, Tailwind CSS 4, Three.js / React Three Fiber / drei, Recharts, Lucide.
- **3D body:** MakeHuman base mesh (CC0), segmented into 25 regions by skeleton weights (`frontend/scripts/build_anatomy_model.py`).

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt   # macOS / Linux
cp .env.example .env    # optional keys: GROQ_API_KEY, NASA_API_KEY
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Every key is optional: without `GROQ_API_KEY` the assistant runs offline, and without `NASA_API_KEY` DONKI uses `DEMO_KEY` (10 requests/hour) and then the cached or curated data. JPL Horizons needs no key. All variables are documented in [backend/.env.example](backend/.env.example) and [backend/README.md](backend/README.md).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` (the Vite proxy sends `/api` to port 8000). If the backend is unreachable, the app keeps working with an in-browser simulation and says so on screen.

For a single server, run `npm run build` in `frontend/` and start the backend: FastAPI serves `frontend/dist`.

### Tests

```bash
cd backend
.venv/Scripts/python -m pytest -q
```

## Honest limits

- The ML is trained on a **NASA-calibrated stochastic generator**, not on astronaut medical records; its validation metrics (≈99 % on synthetic data) are optimistic and are not an estimate of clinical performance.
- Smartwatch readings are simulated; no hardware is connected yet.
- The deep-space transit delay uses the range to Mars (the destination) as its worst case; the orbital station keeps a reference relay latency.
- Groq's free tier allows roughly one chained question per minute; above that the answer is assembled directly from the tool results.

## Use of AI

AI coding assistants (Claude, Gemini) helped write code and documentation during the hackathon; the team reviewed and directed the work. Inside the app, scikit-learn models score anomalies and syndromes locally, and an LLM (Qwen 3.8 27B on Groq, or Gemini) orchestrates the tools in the chat, always gated by deterministic NASA-STD-3001 / OCHMO rules. No AI-generated images, audio or video are used.
