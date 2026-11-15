# NASA Space Apps Challenge 2026 — Official Submission Form (`SUBMISSION.md`)

> Copy each section below into the corresponding field on the NASA Space Apps Challenge 2026 submission page. Ensure **Link to Demo** and **Link to Final Project** are pasted after final hosting verification in an incognito browser window.

---

## Project Name
**AstraCare AI**

---

## High-Level Summary
AstraCare AI is an autonomous, offline-first onboard medical officer that monitors astronaut physical, behavioral, nutritional, and radiation health during deep-space missions where up to 20-minute Earth communication delays prevent real-time medical care. Combining deterministic `NASA-STD-3001` & `OCHMO` clinical safety rules, local `scikit-learn` predictive anomaly detection (`IsolationForest` + `RandomForest`), an interactive 3D anatomical holo-scanner, and a LangChain tool-calling conversational agent, AstraCare empowers non-medical crew members to detect multi-variable syndromes early, execute step-by-step countermeasures, and transmit structured telemedicine dossiers to Earth Flight Surgeons. Built with NASA HRP 5 Hazards data, NASA OCHMO Technical Briefs, CHeCS protocols, and live NASA DONKI solar weather feeds.

---

## Link to Demo
`[Paste public/unlisted 30-second YouTube video URL or 7-slide PDF link here — verified in incognito window]`

---

## Link to Final Project
`[Paste deployed public production URL here (e.g., Vercel / Render) — verified without login in incognito window]`  
*(Public GitHub Repository: https://github.com/Nickddb/NASA_Hackaton)*

---

## Detailed Description

**What it does & how it works:**  
AstraCare AI replaces fragmented spreadsheets with a unified *Deep Space Medical Cockpit* linking a simulated edge biometric smartwatch, an interactive 3D holographic human body (`Three.js` / React Three Fiber), longitudinal trend charts (`Recharts`), and a conversational AI Medical Officer (`LangChain`). Crew members can switch across 6 mission scenarios (*Nominal*, *Systemic Infection*, *Orthostatic Intolerance*, *Severe Behavioral Fatigue*, *Caloric-Deficit Hypoglycemia*, and *Solar Particle Event*) and 3 operational environments (*Deep Space Transit 0g*, *Orbital Station*, and *Planetary Surface*), log meals or sleep in natural language (e.g., *"I ate 2 apples and drank 500ml of water"*), and click any of 6 anatomical regions to inspect CHeCS measurement procedures and trigger manual sensor scans.

**3-Layer Hybrid Edge AI & Science Validity:**  
Because pure black-box LLMs risk clinical hallucinations in spaceflight, AstraCare enforces a 3-layer architecture:
1. **Layer 1 (Deterministic Safety):** `NASA-STD-3001` and NASA OCHMO Technical Brief rules evaluate 8 core biomarkers, spaceflight nutrition safety limits (`Sodium <= 3500 mg/day`, `Iron <= 10 mg/day`), EVA shoulder impingement (`OCHMO-MTB-006`), circadian desynchrony (`OCHMO-MTB-009`), Patent Foramen Ovale decompression risk (`OCHMO-MTB-011`), and mandatory lunar/Martian regolith decontamination prior to surface exams.
2. **Layer 2 (Predictive ML):** Startup-trained `IsolationForest` generates a continuous 0–100% anomaly score while `RandomForestClassifier` computes syndrome probabilities and feature drivers from synthetic physiological cohorts calibrated to NASA Standard Measures.
3. **Layer 3 (LangChain Agent + Telemetry Downlink):** Six `@tool` functions execute rule checks, ML scoring, NASA DONKI (`FLR`/`SEP`) solar storm correlation, natural-language nutrition/sleep updates, and `OCHMO-TB-044` MORD telemedicine dossier compilation—working seamlessly offline-first when no LLM API key or Earth link is available.

**Impact & Challenge Alignment:**  
AstraCare directly fulfills Challenge 05's objective to *"create a visual tool that helps astronauts evaluate their own health during space missions and provides guidance on treatments and health improvements"* without assuming medical training. In-app *"How to Measure"* and *"Why It Matters"* guides translate CHeCS devices (`i-STAT`, `CSA Astroskin`, `Ultrasound 2`, `Tempus Pro`, `Urolux`, `Polysomnography`) into plain crew instructions.

**AI Disclosure Summary:**  
AI coding assistants were used during hackathon software development, and AstraCare's diagnostic engine uses local `scikit-learn` models alongside optional LangChain/Gemini orchestration grounded strictly in deterministic NASA clinical rules.

---

## NASA Data
- **NASA Human Research Program (HRP) — 5 Hazards & Risks of Human Spaceflight:** https://www.nasa.gov/hrp/hazards/ & https://www.nasa.gov/hrp/risks/ — Grounds the 8 core physiological/behavioral biomarkers and 5 combined clinical triage scenarios.
- **NASA DONKI API (`FLR` & `SEP` Space Weather):** https://api.nasa.gov/DONKI/FLR & https://api.nasa.gov/DONKI/SEP — Queried by the backend (`nasa_donki.py`) with a curated local sample fallback (`nasa_donki_sample.json`) to correlate real solar flares and proton storms with astronaut radiation dose limits.
- **NASA OCHMO Standards & Technical Briefs (`NASA-STD-3001`, `OCHMO-MTB-006`, `OCHMO-MTB-009`, `OCHMO-MTB-011`, `OCHMO-TB-043`, `OCHMO-TB-044`, `OCHMO-TB-051`):** Rules for EVA shoulder injuries, circadian light/sleep countermeasures, PFO/DCS prebreathe screening, longitudinal health surveillance (SANS & bone loss), and MORD Flight Surgeon telemedicine roles.
- **NASA ISS Crew Health Care System (CHeCS) & Space Food Systems:** Hardware reference (`i-STAT`, `Tempus Pro`, `Ultrasound 2`, `MELFI`, `CMRS`, `ARED`) and spaceflight dietary caps (`Sodium <= 3500 mg/day`, `Iron <= 10 mg/day`).

---

## Space Agency Partner and Other Data
- **Agência Espacial Brasileira (AEB):** Challenge 05 sponsor and space medicine scope guidelines.
- **Canadian Space Agency (CSA) — Astroskin Bio-Monitor & Radiation Monitoring:** https://www.asc-csa.gc.ca/eng/iss/bio-monitor.asp & https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp
- **Design System:** Adapted from `VoltAgent/awesome-design-md` (`spacex` & `sentry`, MIT License).
- **Open-Source Libraries:** FastAPI, Uvicorn, Pydantic, HTTPX, scikit-learn, NumPy, Pandas, LangChain, React, Vite, Tailwind CSS, Three.js / React Three Fiber, Recharts, Lucide React.

---

## Use of Artificial Intelligence
Artificial Intelligence assistants supported code scaffolding and clinical documentation structuring during the hackathon. Inside the application, `scikit-learn` (`IsolationForest` and `RandomForestClassifier`) performs local anomaly/syndrome scoring and `LangChain` orchestrates 6 medical tools (with Gemini when configured and deterministic NLP fallback offline), gated by deterministic `NASA-STD-3001` clinical rules. No AI-generated audio, video, or photorealistic imagery of people is used.

---

## References
*(Paste full contents of `SOURCES.md`)*

---

## Pre-Submission Eligibility Checklist
- [ ] Public URL of AstraCare AI opens in an incognito browser window without login.
- [ ] GitHub repository (`https://github.com/Nickddb/NASA_Hackaton`) is public with English `README.md`.
- [ ] Demo is <= 30 seconds video or <= 7 slides in English, accessible without login.
- [ ] No NASA logos, insignia, or "Space Apps" branding inside the app UI or slides.
- [ ] No under-18 likenesses or unlicensed media appear in demo materials.
- [ ] Team Owner submits before **Sunday, November 15, 2026, 11:59 PM** local time.
