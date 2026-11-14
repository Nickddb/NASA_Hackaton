# AstraCare AI — Local Event Pitch Deck Script (`PITCH.md`)

> **Target Format:** 4-minute timed pitch + 2 minutes Q&A (6 slides, max 3 bullets of <= 8 words per slide, 1 key number per slide). Slides in English; spoken delivery adaptable to local judges' language.

---

## Slide 1 · Hook · 25 s
- **Title:** Twenty Minutes Between Symptoms and Earth
- **Image:** Screenshot of AstraCare AI Critical Emergency banner showing Mars 12-min latency countdown (no NASA logos).
- **Say:** "On a Mars mission, a medical message takes up to 20 minutes each way. When fever or solar radiation hits, an astronaut without a doctor onboard has to act in seconds, not forty minutes."

## Slide 2 · Challenge and Solution · 36 s
- **Title:** AstraCare AI
- **Bullets:**
  - Challenge 05: Astronaut Health Monitoring Software
  - Autonomous offline-first onboard medical officer
  - Built for non-medical spaceflight crews
- **Say:** "We built AstraCare AI for Challenge 05: an autonomous, offline-first medical officer inside a single mission cockpit. Instead of forcing astronauts to read raw spreadsheets, it combines a wearable smartwatch, an interactive 3D body scanner, and a conversational AI agent."

## Slide 3 · Demo · 96 s
- **Title:** Log a Meal, Triage a Crisis, Downlink Earth
- **Image:** Screen recording (or side-by-side screenshots: Natural-language chat nutrition update + 3D Critical Solar Storm / Systemic Infection triage).
- **Say:** "Watch what happens live. First, I type 'I ate 2 apples and drank 500ml of water'—the LangChain tool updates calories, hydration, and blood glucose instantly while enforcing NASA sodium and iron caps. Now I trigger the Systemic Infection scenario: the 3D body turns red on heart and lungs, our IsolationForest anomaly score jumps to 99%, and the Critical Protocol opens with step-by-step CHeCS isolation instructions. On a lunar or Martian surface, it even blocks active cuff scans until the astronaut checks off the regolith dust decontamination list. Finally, one click compiles a Flight Surgeon Telemedicine Dossier ready for asynchronous transmission."

## Slide 4 · NASA Data · 36 s
- **Title:** Built on NASA-STD-3001, OCHMO & DONKI
- **Bullets:**
  - NASA HRP 5 Hazards & OCHMO Briefs
  - Live NASA DONKI solar flare/proton feed
  - Three-layer rules, scikit-learn ML, and LangChain
- **Say:** "Safety comes first, so AI never guesses alone. Layer 1 runs deterministic NASA-STD-3001 and OCHMO rules for circadian desynchrony, EVA shoulder injuries, and PFO decompression risks; Layer 2 runs local IsolationForest and RandomForest models to explain which vitals drove the alert; and Layer 3 correlates live NASA DONKI space weather with a local offline fallback."

## Slide 5 · Impact · 36 s
- **Title:** Safer Autonomous Crews Beyond Low Earth Orbit
- **Bullets:**
  - Empowers any crewmember with plain instructions
  - Adapts across 0g, orbital, and surface bases
  - Next: BLE smartwatch and CHeCS hardware bridge
- **Say:** "Any crewmember on Artemis or Mars transit gains clear 'How to Measure' and 'Why It Matters' guidance on day one. Next, we will connect real Bluetooth Low Energy wearables and ISS i-STAT diagnostic feeds directly into our FastAPI edge engine."

## Slide 6 · Close · 10 s
- **Title:** AstraCare AI
- **Bullets:**
  - `[Insert Public URL]`
  - Built with NASA Data
  - `[Insert Team Name & Members]`
- **Say:** "AstraCare AI brings autonomous flight-surgeon intelligence to every astronaut's wrist and mission console—thank you."

---

## Judge Q&A Prep (6 Expected Questions)

1. **Impact — "Who would actually use this, and how many of them?"**  
   Any non-medical astronaut crewmember on ISS, Lunar Gateway, Artemis surface habitats, or future Mars transit vehicles—and analog mission crews (e.g., HERA/CHAPEA) today. Because every crew rotation includes engineers and scientists without medical degrees, autonomous triage reduces Flight Surgeon dependency across every human spaceflight mission.
2. **Creativity — "What does this do that existing dashboards do not?"**  
   Existing tools display isolated vital numbers; AstraCare AI fuses multi-variable `NASA-STD-3001` clinical rules with `IsolationForest` anomaly attribution, a 3D clickable body scanner, and a natural-language LangChain agent that logs meals, enforces spaceflight Na/Fe limits, and auto-generates MORD telemedicine bundles.
3. **Validity — "How do you know the clinical numbers and alerts are right?"**  
   Every hard threshold is anchored in NASA OCHMO Technical Briefs (`MTB-006` Shoulder, `MTB-009` Circadian, `MTB-011` PFO, `TB-043` LHS, `TB-044` MORD) and `NASA-STD-3001`, while our `scikit-learn` models are trained on synthetic physiological cohorts calibrated to those envelopes (explicitly scoped as simulated telemetry rather than clinical patient records).
4. **Relevance — "The challenge asked for real space environments and non-medical guidance; where is that?"**  
   AstraCare dynamically calibrates across 0g Transit, Orbital Station, and Planetary Surface—including a mandatory regolith decontamination gate—and embeds plain-English *"How to Measure"* and *"Why It Matters"* guides on every biomarker card and 3D system node.
5. **Future — "What would you build next with one more week?"**  
   We would integrate WebBluetooth streaming from a physical PPG/ECG smartwatch, add offline local audio/vision guidance for portable ultrasound positioning (`Ultrasound 2`), and store longitudinal trend logs in an encrypted onboard SQLite EMR.
6. **AI Split — "What did the AI do and what did you do?"**  
   Our team engineered the full React/Three.js cockpit, FastAPI architecture, and NASA clinical rule mappings, while AI assistants accelerated code scaffolding and AstraCare uses `scikit-learn` + `LangChain` internally for anomaly scoring and natural-language logging gated by deterministic safety rules.
