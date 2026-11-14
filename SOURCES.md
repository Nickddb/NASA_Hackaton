# Sources & References

> Complete log of NASA datasets, OCHMO technical briefs, space agency partner resources, design references, and open-source libraries used in **AstraCare AI**.

## NASA Data, Standards & Clinical Resources
- **NASA Space Apps Challenge 2026 — Challenge 05 (*Create Health Monitoring Software for Astronauts on Space Missions*):** https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/
- **NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information) API (`FLR` & `SEP`):** https://api.nasa.gov/DONKI/FLR and https://api.nasa.gov/DONKI/SEP (Public Domain; queried via backend proxy with local curated sample fallback `nasa_donki_sample.json`).
- **NASA Human Research Program (HRP) — *5 Hazards of Human Spaceflight*:** https://www.nasa.gov/hrp/hazards/
- **NASA Human Research Program (HRP) — *Risks of Human Spaceflight*:** https://www.nasa.gov/hrp/risks/
- **NASA Human Research Program (HRP) — *Ongoing HRP Research in Space*:** https://www.nasa.gov/hrp/ongoing-hrp-research/
- **NASA OCHMO — *Space Flight Human-System Standard (NASA-STD-3001)*:** https://www.nasa.gov/wp-content/uploads/2025/01/nasas-agency-level-space-flight-human-system-standards.pdf
- **NASA OCHMO-MTB-006 — *Shoulder Injury Prevention & EVA Suit Biomechanics*:** https://www.nasa.gov/wp-content/uploads/2025/09/ochmo-mtb-006-shoulder-injury.pdf?emrc=580943
- **NASA OCHMO-MTB-009 — *Circadian Desynchrony & Fatigue Management*:** https://www.nasa.gov/wp-content/uploads/2026/03/ochmo-mtb-009-circadian-desynchrony.pdf?emrc=80a788
- **NASA OCHMO-MTB-011 — *Patent Foramen Ovale (PFO) & EVA Decompression Risk*:** https://www.nasa.gov/wp-content/uploads/2026/11/ochmo-mtb-011-patent-foramen-ovale-pfo.pdf?emrc=b0b1b8
- **NASA OCHMO-TB-043 — *Longitudinal Health Surveillance (LHS)*:** https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-043-longitudinal-health-surveillance.pdf?emrc=6af87f5d781ae
- **NASA OCHMO-TB-044 — *Medical Operations Requirements Document (MORD)*:** https://www.nasa.gov/wp-content/uploads/2025/08/ochmo-tb-044-medical-operations.pdf?emrc=6af87f5d790d0
- **NASA OCHMO-TB-051 — *Crew Medical Support (Entry, Descent, Landing & Standards)*:** https://www.nasa.gov/wp-content/uploads/2026/05/ochmo-tb-051-crew-medical-support-entry-descent-landing.pdf?emrc=82d496
- **NASA ISS Crew Health Care System (CHeCS) & Hardware (`i-STAT`, `Tempus Pro`, `Ultrasound 2`, `Urolux`, `CMRS`, `ARED`, `MELFI`):** https://www.nasa.gov/mission/international-space-station/crew-health-care-system/
- **NASA Space Station Cold Storage (`MELFI` & `MERLIN`):** https://www.nasa.gov/international-space-station/space-station-research-and-technology/melfi-freezer/
- **NASA Space Food Systems Portfolio (Sodium `<=3500mg` & Iron `<=10mg` Spaceflight Dietary Caps):** https://www.nasa.gov/space-food-systems-portfolio/
- **NASA Open Science Data Repository (OSDR — GeneLab / ALSDA) & Life Sciences Portal (NLSP) *Standard Measures*:** https://osdr.nasa.gov/

## Space Agency Partner Resources
- **Agência Espacial Brasileira (AEB):** Space Apps 2026 Challenge 05 curation and aerospace human health mentorship.
- **Canadian Space Agency (CSA) — *Monitoring radiation for astronaut health*:** https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp
- **Canadian Space Agency (CSA) — *Astroskin Bio-Monitor System*:** https://www.asc-csa.gc.ca/eng/iss/bio-monitor.asp
- **Canadian Space Agency (CSA) — *Why Do We Conduct Science Experiments in Space?*:** https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp

## Design System, Libraries & Tools
- **Design system adapted from `VoltAgent/awesome-design-md` (`spacex/DESIGN.md` & `sentry/DESIGN.md`), MIT License:** https://github.com/VoltAgent/awesome-design-md
- **Frontend Stack:** React, Vite, Tailwind CSS (`@tailwindcss/vite`), Three.js (`three`, `@react-three/fiber`, `@react-three/drei`), Recharts (`recharts`), Lucide React (`lucide-react`) — MIT / ISC Licenses.
- **Backend & AI Stack:** Python 3, FastAPI, Uvicorn, Pydantic, HTTPX, scikit-learn, NumPy, Pandas, LangChain (`langchain`, `langchain-core`, `langchain-google-genai`) — MIT / BSD-3-Clause Licenses.
- **Typography:** Google Fonts (`Space Grotesk`, `Inter`, `JetBrains Mono`) — SIL Open Font License 1.1.
- **3D Anatomical Base Mesh Reference (`base_male_body`):** by **xiaofeihui** on Sketchfab — https://sketchfab.com/3d-models/base-male-body-0119efadabf64016ad9227b107a55509
