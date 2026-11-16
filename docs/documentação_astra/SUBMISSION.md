# NASA Space Apps Challenge 2026 — Official Submission Form (`SUBMISSION.md`)

> Copy each section below into the matching field of the Space Apps 2026 submission page. Paste **Link to Demo** and **Link to Final Project** only after opening both in an incognito window, without login.

---

## Project Name
**AstraCare AI**

---

## High-Level Summary
AstraCare AI is an offline-first onboard medical officer for long-duration missions, where a message to Earth can take up to 22 minutes each way. It compares every astronaut against their own adaptive baseline, checks live NASA DONKI space weather before blaming the body, explains each alert, and walks non-medical crew through NASA-STD-3001 / OCHMO checklists. A tool-calling AI agent chains smartwatch exams, diagnosis, central alerts and psychological countermeasures, while hash-chained packages wait for the communication window computed from live NASA JPL Horizons data.

---

## Link to Demo
`[Paste the public/unlisted 30-second video URL or the 7-slide PDF link — verified in an incognito window]`

---

## Link to Final Project
`[Paste the deployed public URL — verified without login in an incognito window]`
*(Public GitHub repository: https://github.com/Nickddb/NASA_Hackaton)*

---

## Detailed Description

**What it does.** AstraCare AI is a mission cockpit for a crew of five (ISS orbit and deep-space transit). Each astronaut has screens for **Vitals** (personal-baseline readings and a realistic 3D anatomical body split into 25 selectable parts, where the crew taps where it hurts), **Diagnosis** (cause tree, explainable alerts, follow-up cases and the Ship ↔ Earth link), **Mind** (behavioural readiness and countermeasures) and an **Assistant** (AI medical officer in English or Portuguese). Alerts cannot be silenced: they clear only after stabilisation and a new reading back inside the personal baseline.

**How it works.**
1. **Adaptive individual baseline:** EWMA + MAD per astronaut, Ledoit-Wolf Mahalanobis distance and NASA OSDR gravity-phase priors; anomalous readings are quarantined so a slow drift is never learned as normal.
2. **Contextual mission intelligence:** exercise (ARED/T2/CEVIS), EVA, sleep, cabin CO₂ and gravity phase explain benign deviations, and are reported as correlations, not causes.
3. **Calibrated, explainable machine learning:** a Platt-calibrated HistGradientBoosting + RandomForest ensemble plus IsolationForest uses 26 features (vitals, context, DONKI activity, crew-reported pain and symptoms, personal z-scores) to rank 8 syndromes. It reports epistemic and sensor uncertainty, counterfactual drivers and a 72-hour forecast.
4. **Cross-diagnosis cause tree:** first checks live NASA DONKI events (SEP, FLR, RBE), then onboard environment and physiology. A behavioural change is labelled psychological only when nothing physical or external explains it, and self-harm language always escalates to Earth.
5. **Closed-loop follow-up:** every alert opens a case: confirmation measurement → crew action → timed reassessment → resolved, or escalated to Earth by a human.
6. **Spacecraft–Earth continuity:** SHA-256 hash-chained store-and-forward packages and audit log. The one-way delay is computed from the live Earth–Mars range in NASA JPL Horizons (about 11 minutes on submission day).

**The AI agent.** The Assistant's agent has 16 tools. Four form a chain where each output decides the next call: `schedule_smartwatch_exam` → `analyze_telemetry_and_diagnose` → `trigger_central_alert` (CRITICAL or escalated WARNING) → `activate_psychological_stimuli` (psychological cause only). It runs on Qwen 3.8 27B through Groq. With no network or key, a deterministic bilingual pipeline runs the same tools, and scheduled smartwatch exams run the chain in the background.

**Why it matters.** Challenge 05 asks for a visual tool that lets astronauts evaluate their own health without medical training and get guidance despite communication delays. AstraCare AI answers that with personal baselines instead of population averages, causes instead of raw numbers, plain-language "How to measure / Why it matters" guides and an auditable record for Flight Surgeons.

**Honest limits.** The ML is trained on a NASA-calibrated stochastic generator, not on astronaut records; its ~99 % accuracy on synthetic data is not an estimate of clinical performance. Smartwatch readings are simulated.

**Tools.** Python, FastAPI, scikit-learn, React, Vite, Tailwind CSS, Three.js / React Three Fiber, Recharts, Groq API, NASA DONKI and JPL Horizons APIs.

---

## NASA Data
- **NASA DONKI API (SEP, FLR, RBE):** https://api.nasa.gov/ — live solar energetic particle, flare and radiation-belt events. They drive the cause tree and an ML feature, with cache and an offline fallback.
- **NASA JPL Horizons API:** https://ssd.jpl.nasa.gov/api/horizons.api — live Earth–Mars range, converted to the one-way and round-trip light-time used by the Earth link and the telemedicine dossier.
- **NASA-STD-3001 and OCHMO technical briefs** (radiation protection, MTB-006, MTB-009, MTB-011, TB-043, TB-044, TB-051): thresholds, crew checklists and Flight Surgeon roles.
- **NASA Human Research Program (hazards, risks, Human Research Roadmap) and NASA OSDR (OSD-570, OSD-571 standard measures):** physiological ranges and gravity-phase priors that calibrate the telemetry generator and the adaptive baseline.
- **NASA ISS Crew Health Care System (CHeCS) and Space Food Systems:** the "How to measure" device guides and dietary limits (sodium ≤ 3,500 mg/day, iron ≤ 10 mg/day).

---

## Space Agency Partner and Other Data
- **Agência Espacial Brasileira (AEB):** Challenge 05 co-sponsor and scope.
- **Canadian Space Agency (CSA):** Astroskin Bio-Monitor and radiation-monitoring references.
- **MakeHuman base mesh and skeleton weights (CC0 1.0):** the 3D anatomical body.
- **Design system:** adapted from `VoltAgent/awesome-design-md` (MIT).
- **Open-source libraries:** FastAPI, Uvicorn, Pydantic, HTTPX, scikit-learn, NumPy, Pandas, React, Vite, Tailwind CSS, Three.js, React Three Fiber, drei, Recharts, Lucide.

---

## Use of Artificial Intelligence
AI coding assistants (Claude, Gemini) helped write code and documentation during the hackathon; the team set the direction and reviewed the results. Inside the application, scikit-learn models score anomalies and syndromes locally, and a large language model (Qwen 3.8 27B on Groq, or optionally Gemini) orchestrates the clinical tools in the chat. Its answers are grounded in tool outputs and gated by deterministic NASA-STD-3001 / OCHMO rules, and it never prescribes treatment. No AI-generated images, audio or video appear in the app or demo materials.

---

## References
*(Paste the full contents of `docs/instruções/SOURCES.md`.)*

---

## Pre-Submission Eligibility Checklist
- [ ] Public URL of AstraCare AI opens in an incognito window without login.
- [x] GitHub repository (https://github.com/Nickddb/NASA_Hackaton) is public, with an English `README.md`.
- [ ] Demo is ≤ 30 seconds of video or ≤ 7 slides, in English, accessible without login.
- [ ] No NASA logos, insignia or "Space Apps" branding inside the app UI or slides.
- [ ] No under-18 likenesses or unlicensed media in the demo materials.
- [ ] Team Owner submits before **Sunday, November 15, 2026, 11:59 PM** local time.
