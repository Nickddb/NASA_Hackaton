# Challenge 05: Create Health Monitoring Software for Astronauts on Space Missions

- **Official Page:** https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/
- **Difficulty:** Intermediate
- **Categories:** Human Exploration, Software, Space Exploration
- **Author / Sponsor:** NASA Human Research Program (HRP) & Agência Espacial Brasileira (AEB)

## Challenge Objective
Create a visual software tool that gathers astronaut health indicators during long-duration space missions (Earth orbit, deep space transit, Moon, and Mars) and empowers non-medical crew members to evaluate their physical and behavioral health, understand *how* and *why* measurements are performed in space, detect multi-variable clinical anomalies despite communication delays with Earth, and receive actionable preventive or emergency treatment guidance.

## Key Requirements Addressed by AstraCare AI
1. **Multimodal Input:** Continuous wearable smartwatch telemetry (`HR`, `HRV`, `BP`, `Glucose`, `Temp`, `Sleep`, `Dosimetry`), clickable 3D anatomical region triggers, and conversational natural-language nutrition/symptom logging.
2. **Environment Adaptation:** Tailored calibration and checklists across **Deep Space Transit (0g)**, **Orbital Station (ISS / Lunar Gateway)**, and **Planetary Surface (Lunar/Martian regolith decontamination)**.
3. **Intuitive Visuals & Gamification:** Interactive holographic 3D human body with traffic-light system status (`NOMINAL`, `WARNING`, `CRITICAL`), longitudinal trend charts, and daily nutrition/hydration/exercise goal tracking.
4. **Offline-First Autonomous Edge AI:** Combines deterministic `NASA-STD-3001` & `OCHMO` clinical safety rules, local `scikit-learn` anomaly & syndrome prediction, and a LangChain tool-calling medical officer agent with asynchronous Earth Telemedicine Dossier generation.
