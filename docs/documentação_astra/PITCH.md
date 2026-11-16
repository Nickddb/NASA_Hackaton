# AstraCare AI — Local Event Pitch Script (`PITCH.md`)

> **Format:** 4-minute pitch + 2 minutes Q&A · 6 slides · at most 3 bullets of ≤ 8 words per slide · one key number per slide. Slides in English; spoken delivery can follow the judges' language.

---

## Slide 1 · Hook · 25 s
- **Title:** Eleven Minutes Between Symptoms and Earth
- **Image:** Diagnosis → Earth link tab showing the live JPL Horizons delay (no NASA logos).
- **Say:** "Today, a message from a Mars-bound crew takes about eleven minutes to reach Earth, and eleven more to come back. When a fever, a solar storm or a sleepless week hits, the astronaut on board has to decide alone."

## Slide 2 · Challenge and Solution · 36 s
- **Title:** AstraCare AI
- **Bullets:**
  - Challenge 05: astronaut health monitoring
  - Onboard medical officer, offline-first
  - Built for non-medical crews
- **Say:** "For Challenge 05 we built AstraCare AI: an onboard medical officer that compares each astronaut with their own baseline, explains why something is wrong and tells the crew what to do next, even with no link to Earth."

## Slide 3 · Demo · 96 s
- **Title:** From a Sore Chest to a Flight Surgeon Package
- **Image:** Live app, or screenshots: Vitals with the 3D body and pain map → Diagnosis cause tree → Assistant with the executed tools.
- **Say:** "Here is Liam, our deep-space habitat specialist. His heart rate and temperature are outside *his* personal range, not just a population table. He taps his chest on the 3D body and reports pain, and the machine-learning model takes that into account. In Diagnosis, the cause tree first checks live NASA DONKI space weather. No solar event explains this, so it points to a physiological cause, an infection. Then I ask the assistant to analyse Liam and warn Earth if it is serious. It runs the smartwatch exam, the diagnosis and the central alert by itself, and the package waits for the communication window computed from JPL Horizons."

## Slide 4 · NASA Data · 36 s
- **Title:** Live NASA Data, NASA Rules
- **Bullets:**
  - DONKI space weather in every diagnosis
  - JPL Horizons sets the Earth delay
  - NASA-STD-3001, OCHMO and OSDR calibration
- **Say:** "We use NASA data live, not as decoration. DONKI events decide whether a symptom is space weather before we call it physical or psychological. JPL Horizons gives the real light-time to Earth. Every threshold comes from NASA-STD-3001, OCHMO briefs or OSDR standard measures, with its source written next to it in the code."

## Slide 5 · Impact · 36 s
- **Title:** Safer Crews Beyond Low Earth Orbit
- **Bullets:**
  - Personal baselines, not population averages
  - Psychology only after ruling out physics
  - Next: real wearables and CHeCS data
- **Say:** "Any crew member gets plain-language guidance on day one. Psychological support is offered only after physical and environmental causes are ruled out, so a radiation problem is never mistaken for stress. Next, we connect real Bluetooth wearables and train on NASA standard-measures data instead of our calibrated generator."

## Slide 6 · Close · 10 s
- **Title:** AstraCare AI
- **Bullets:**
  - `[Insert public URL]`
  - Built with NASA data
  - `[Insert team name & members]`
- **Say:** "AstraCare AI: a flight surgeon's reasoning on every astronaut's wrist. Thank you."

---

## Judge Q&A prep

1. **"Who would use this?"** Non-medical crew members on the ISS, the Lunar Gateway, Artemis surface habitats and Mars transit vehicles, plus analogue crews (HERA, CHAPEA) today. Most crew members are engineers or scientists, and Earth is minutes away.
2. **"What is new compared with a vitals dashboard?"** Personal baselines with drift quarantine, a cause tree that checks live space weather first, explainable and calibrated ML that includes crew-reported pain, a closed follow-up loop, and an AI agent that chains exam → diagnosis → alert → countermeasure.
3. **"How do you know the numbers are right?"** Thresholds come from NASA-STD-3001, OCHMO briefs, HRP and OSDR, and each value in `nasa_calibration.py` cites its source and whether we verified it in the document. The ML is trained on a generator calibrated to those ranges. We say openly that its ~99 % synthetic accuracy is not clinical performance.
4. **"What if the AI is wrong?"** It cannot act alone. Diagnosis and treatment are blocked by design, every action is a protocol checklist that a human confirms, and escalation to Earth is a human decision. Offline or without a key, a deterministic pipeline gives the same structured answer.
5. **"Why an LLM at all?"** For natural language: "check Kenji every 30 minutes" or "I ate two apples" become tool calls. The medical reasoning stays in the deterministic rules and the ML. The LLM only chooses and chains tools, and reports what they returned.
6. **"What did AI do and what did you do?"** We designed the architecture, the clinical logic and the NASA data mapping. AI coding assistants sped up implementation and documentation. Inside the app, scikit-learn does the scoring and Qwen on Groq orchestrates the tools.
