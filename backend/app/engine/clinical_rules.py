from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.schemas import (
    ClinicalEvaluationResult,
    NutritionHydrationState,
    SeverityStatus,
    SystemEvaluation,
    VitalSigns,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SEVERITY_RANK: dict[SeverityStatus, int] = {
    "NOMINAL": 0,
    "WARNING": 1,
    "CRITICAL": 2,
}


def _max_status(a: SeverityStatus, b: SeverityStatus) -> SeverityStatus:
    return a if SEVERITY_RANK[a] >= SEVERITY_RANK[b] else b


def load_scenarios_catalog() -> dict[str, Any]:
    with open(DATA_DIR / "scenarios.json", "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_clinical_rules(
    vitals: VitalSigns,
    nutrition: NutritionHydrationState,
    environment_id: str,
    catalog: dict[str, Any] | None = None,
) -> ClinicalEvaluationResult:
    """Layer 1 Deterministic Clinical Safety Engine grounded in NASA-STD-3001 & OCHMO briefs."""
    if catalog is None:
        catalog = load_scenarios_catalog()

    systems_guide = catalog.get("systems_guide", {})
    environments = {e["id"]: e for e in catalog.get("environments", [])}
    env_info = environments.get(environment_id, environments.get("transit", {}))

    matched_rules: list[str] = []
    stabilization_checklist: list[str] = []
    env_notes: list[str] = []

    # Environment-specific calibration notes
    if environment_id == "transit":
        env_notes.append(
            "0g Microgravity Transit Calibration: Cephalic fluid-shift correction (+6 mmHg hydrostatic compensation) applied to NIBP baseline; all sensors operating on low-power wireless BLE."
        )
    elif environment_id == "orbital_station":
        env_notes.append(
            "Orbital Station (ISS/Gateway) Calibration: Cabin circadian LED CCT synchronized to sleep shift (16 sunrises/day mitigation per OCHMO-MTB-009); full CHeCS rack (Ultrasound 2, MELFI, ARED) online."
        )
    elif environment_id == "planetary_surface":
        env_notes.append(
            "Planetary Surface Calibration (1/6g Lunar / 3/8g Mars): Mandatory electrostatic/HEPA regolith & perchlorate decontamination required before active capillary puncture or NIBP cuff exams."
        )

    # Track per-system alerts & severity
    sys_alerts: dict[str, list[str]] = {
        "cardiovascular": [],
        "nervous_sleep": [],
        "respiratory": [],
        "metabolic": [],
        "musculoskeletal": [],
        "radiation": [],
    }
    sys_status: dict[str, SeverityStatus] = {k: "NOMINAL" for k in sys_alerts}
    sys_actions: dict[str, str] = {
        "cardiovascular": "Maintain 2.5h daily CMS aerobic/resistive exercise and adequate hydration.",
        "nervous_sleep": "Continue circadian sleep hygiene (cool, dark bunk; limit blue CCT 1–2h pre-sleep).",
        "respiratory": "Cabin O2/CO2 scrubbing nominal; continue scheduled smartwatch thermal monitoring.",
        "metabolic": "Maintain balanced caloric intake (2800 kcal/day), hydration (2500 ml), and Na/Fe caps.",
        "musculoskeletal": "Execute daily ARED/T2 countermeasure protocol and post-EVA shoulder mobility stretches.",
        "radiation": "Dosimetry within ALARA baseline; continue passive BLE monitoring.",
    }

    # --- Individual NASA-STD-3001 & OCHMO thresholds ---
    # 1. Cardiovascular (HR, HRV, BP, PFO)
    if vitals.heart_rate_bpm >= 110 or vitals.heart_rate_bpm <= 44:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "CRITICAL")
        sys_alerts["cardiovascular"].append(f"Heart rate out of flight rule: {vitals.heart_rate_bpm:.0f} bpm")
        matched_rules.append("NASA-STD-3001-CV-HR-CRIT")
    elif vitals.heart_rate_bpm >= 95 or vitals.heart_rate_bpm <= 50:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "WARNING")
        sys_alerts["cardiovascular"].append(f"Elevated/borderline heart rate: {vitals.heart_rate_bpm:.0f} bpm")
        matched_rules.append("NASA-STD-3001-CV-HR-WARN")

    if vitals.bp_systolic <= 85 or vitals.bp_systolic >= 165:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "CRITICAL" if vitals.bp_systolic <= 82 else "WARNING")
        sys_alerts["cardiovascular"].append(f"Abnormal blood pressure: {vitals.bp_systolic:.0f}/{vitals.bp_diastolic:.0f} mmHg")
        matched_rules.append("NASA-STD-3001-CV-BP-ABNORMAL")
    elif vitals.bp_systolic <= 92:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "WARNING")
        sys_alerts["cardiovascular"].append(f"Low systolic pressure: {vitals.bp_systolic:.0f}/{vitals.bp_diastolic:.0f} mmHg")
        matched_rules.append("NASA-STD-3001-CV-BP-LOW")

    if vitals.hrv_ms <= 24:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "CRITICAL")
        sys_status["nervous_sleep"] = _max_status(sys_status["nervous_sleep"], "CRITICAL")
        sys_alerts["cardiovascular"].append(f"Severe HRV suppression ({vitals.hrv_ms:.0f} ms)")
        matched_rules.append("AUTONOMIC-HRV-COLLAPSE")
    elif vitals.hrv_ms < 35:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "WARNING")
        sys_alerts["cardiovascular"].append(f"Reduced HRV ({vitals.hrv_ms:.0f} ms)")
        matched_rules.append("AUTONOMIC-HRV-LOW")

    if vitals.pfo_decompression_risk in ("MODERATE", "HIGH"):
        sev: SeverityStatus = "CRITICAL" if vitals.pfo_decompression_risk == "HIGH" else "WARNING"
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], sev)
        sys_alerts["cardiovascular"].append(
            f"OCHMO-MTB-011 PFO/DCS EVA Risk ({vitals.pfo_decompression_risk}): Shunting screening & 4h O2/Campout prebreathe active."
        )
        matched_rules.append("OCHMO-MTB-011-PFO-DCS")

    # 2. Respiratory & Thermal
    if vitals.temperature_c >= 38.0:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "CRITICAL")
        sys_alerts["respiratory"].append(f"High fever detected: {vitals.temperature_c:.1f} C")
        matched_rules.append("NASA-STD-3001-TEMP-FEVER")
    elif vitals.temperature_c >= 37.5 or vitals.temperature_c < 35.8:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "WARNING")
        sys_alerts["respiratory"].append(f"Temperature outside nominal range: {vitals.temperature_c:.1f} C")
        matched_rules.append("NASA-STD-3001-TEMP-DRIFT")

    if vitals.spo2_pct < 94.0 or vitals.respiration_rpm >= 24:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "CRITICAL")
        sys_alerts["respiratory"].append(f"Hypoxemia / tachypnea: SpO2 {vitals.spo2_pct:.1f}%, RR {vitals.respiration_rpm:.0f} rpm")
        matched_rules.append("NASA-STD-3001-RESP-CRIT")
    elif vitals.spo2_pct < 95.5 or vitals.respiration_rpm >= 20:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "WARNING")
        sys_alerts["respiratory"].append(f"Borderline respiratory effort: SpO2 {vitals.spo2_pct:.1f}%, RR {vitals.respiration_rpm:.0f} rpm")
        matched_rules.append("NASA-STD-3001-RESP-WARN")

    # 3. Nervous, Sleep, Behavioral & SANS
    if vitals.sleep_hours < 4.5 or vitals.sleep_streak_low_days >= 3:
        sys_status["nervous_sleep"] = _max_status(sys_status["nervous_sleep"], "CRITICAL" if vitals.sleep_streak_low_days >= 3 else "WARNING")
        sys_alerts["nervous_sleep"].append(
            f"Sleep deficit ({vitals.sleep_hours:.1f}h; {vitals.sleep_streak_low_days} consecutive short nights; REM {vitals.rem_sleep_pct:.0f}%)"
        )
        matched_rules.append("OCHMO-MTB-009-SLEEP-DEFICIT")
    elif vitals.sleep_hours < 6.5:
        sys_status["nervous_sleep"] = _max_status(sys_status["nervous_sleep"], "WARNING")
        sys_alerts["nervous_sleep"].append(f"Sub-optimal sleep duration: {vitals.sleep_hours:.1f}h")
        matched_rules.append("OCHMO-MTB-009-SLEEP-DRIFT")

    if vitals.mood_score <= 2 or vitals.stress_index >= 75:
        sys_status["nervous_sleep"] = _max_status(sys_status["nervous_sleep"], "CRITICAL" if (vitals.mood_score <= 2 and vitals.sleep_streak_low_days >= 3) else "WARNING")
        sys_alerts["nervous_sleep"].append(f"Elevated behavioral strain (Mood {vitals.mood_score}/5, Stress {vitals.stress_index:.0f}%)")
        matched_rules.append("NASA-BHP-BEHAVIORAL-STRAIN")

    if vitals.intraocular_pressure_mmhg >= 20.0:
        sys_status["nervous_sleep"] = _max_status(sys_status["nervous_sleep"], "WARNING")
        sys_alerts["nervous_sleep"].append(f"Elevated IOP ({vitals.intraocular_pressure_mmhg:.1f} mmHg) — Screen for SANS via OCT/Fundoscope (OCHMO-TB-043).")
        matched_rules.append("OCHMO-TB-043-SANS-IOP")

    # 4. Metabolic & Nutrition / Space Food Safety Caps
    cal_pct = (nutrition.calories_kcal / max(nutrition.goal_calories_kcal, 1)) * 100.0
    water_pct = (nutrition.water_ml / max(nutrition.goal_water_ml, 1)) * 100.0

    if vitals.glucose_mg_dl < 60 or vitals.glucose_mg_dl >= 180:
        sys_status["metabolic"] = _max_status(sys_status["metabolic"], "CRITICAL")
        sys_alerts["metabolic"].append(f"Critical blood glucose: {vitals.glucose_mg_dl:.0f} mg/dL")
        matched_rules.append("NASA-STD-3001-GLUCOSE-CRIT")
    elif vitals.glucose_mg_dl <= 70 or vitals.glucose_mg_dl >= 140:
        sys_status["metabolic"] = _max_status(sys_status["metabolic"], "WARNING")
        sys_alerts["metabolic"].append(f"Glycemic excursion: {vitals.glucose_mg_dl:.0f} mg/dL")
        matched_rules.append("NASA-STD-3001-GLUCOSE-WARN")

    if cal_pct < 50.0 or water_pct < 55.0:
        sys_status["metabolic"] = _max_status(sys_status["metabolic"], "WARNING")
        sys_alerts["metabolic"].append(f"Nutritional/hydration deficit ({cal_pct:.0f}% kcal, {water_pct:.0f}% H2O goal)")
        matched_rules.append("SPACE-NUTRITION-DEFICIT")

    if nutrition.sodium_mg > nutrition.max_sodium_mg:
        sys_status["metabolic"] = _max_status(sys_status["metabolic"], "WARNING")
        sys_alerts["metabolic"].append(f"Sodium cap exceeded ({nutrition.sodium_mg:.0f} > {nutrition.max_sodium_mg:.0f} mg/day) — Fluid/bone risk.")
        matched_rules.append("NASA-FOOD-SODIUM-CAP")

    if nutrition.iron_mg > nutrition.max_iron_mg:
        sys_status["metabolic"] = _max_status(sys_status["metabolic"], "WARNING")
        sys_alerts["metabolic"].append(f"Iron cap exceeded ({nutrition.iron_mg:.1f} > {nutrition.max_iron_mg:.1f} mg/day) — Spaceflight RBC toxicity risk.")
        matched_rules.append("NASA-FOOD-IRON-CAP")

    # 5. Musculoskeletal (OCHMO-MTB-006 Shoulder & OCHMO-TB-043 Bone Resorption)
    if vitals.shoulder_pain_score >= 7:
        sys_status["musculoskeletal"] = _max_status(sys_status["musculoskeletal"], "CRITICAL")
        sys_alerts["musculoskeletal"].append(f"Severe EVA shoulder pain ({vitals.shoulder_pain_score}/10 VAS) — Suspect rotator cuff tear/impingement.")
        sys_actions["musculoskeletal"] = "Suspend EVA/overhead tasks; run portable Ultrasound 2 scan, Hawkin/Empty-Can test, apply ice & analgesic."
        matched_rules.append("OCHMO-MTB-006-SHOULDER-CRIT")
    elif vitals.shoulder_pain_score >= 4:
        sys_status["musculoskeletal"] = _max_status(sys_status["musculoskeletal"], "WARNING")
        sys_alerts["musculoskeletal"].append(f"Moderate EVA HUT shoulder pain ({vitals.shoulder_pain_score}/10 VAS) — Rotator cuff / bicipital tendonitis watch.")
        sys_actions["musculoskeletal"] = "Modify overhead EVA tasks, run portable musculoskeletal ultrasound, apply ice + NSAID + scapular rehab."
        matched_rules.append("OCHMO-MTB-006-SHOULDER-WARN")

    if vitals.urinary_calcium_mg_d > 250.0:
        sys_status["musculoskeletal"] = _max_status(sys_status["musculoskeletal"], "WARNING")
        sys_alerts["musculoskeletal"].append(f"Elevated Urolux urinary calcium ({vitals.urinary_calcium_mg_d:.0f} mg/day) — Accelerated bone resorption / stone risk.")
        matched_rules.append("OCHMO-TB-043-BONE-CALCIUM")

    # 6. Radiation (CSA Bio-Monitor & NASA ALARA)
    if vitals.radiation_msv_h >= 0.50:
        sys_status["radiation"] = _max_status(sys_status["radiation"], "CRITICAL")
        sys_alerts["radiation"].append(f"Acute Solar Particle Event dose spike: {vitals.radiation_msv_h:.2f} mSv/h (>0.50 threshold)")
        matched_rules.append("NASA-ALARA-SPE-CRIT")
    elif vitals.radiation_msv_h >= 0.15:
        sys_status["radiation"] = _max_status(sys_status["radiation"], "WARNING")
        sys_alerts["radiation"].append(f"Elevated cosmic/solar radiation rate: {vitals.radiation_msv_h:.2f} mSv/h")
        matched_rules.append("NASA-ALARA-RAD-WARN")

    # --- Evaluate the 5 Combined Predictive Syndromes (astracare-ai-visao-geral.md Sec 5) ---
    primary_diagnosis = "Nominal Spaceflight Physiological Status"
    syndrome_code = "nominal"
    notify_earth = False
    notify_crew = False

    # Check SPE Radiation Storm first (immediate physical hazard)
    if vitals.radiation_msv_h >= 0.50:
        syndrome_code = "solar_storm"
        primary_diagnosis = "Solar Particle Event (SPE) — Acute Radiation Spike"
        matched_rules.insert(0, "SYNDROME_SOLAR_PARTICLE_EVENT")
        sys_actions["radiation"] = "Relocate immediately to water/polyethylene-shielded storm shelter; halt EVA; transmit ALARA telemetry."
        stabilization_checklist = [
            "Acknowledge wristwatch haptic radiation alarm and cease all EVA/unshielded hull tasks immediately.",
            "Relocate all crew to the designated polyethylene/water-wall Radiation Storm Shelter.",
            "Verify personal BLE dosimeters and check NASA DONKI SEP proton flux decay trend every 15 minutes.",
            "Confirm automated Priority Telemetry Downlink receipt by Earth Radiation Health Officer (RHO).",
        ]
        notify_earth = True
        notify_crew = True

    # Systemic Infection / Acute Viral State
    elif vitals.temperature_c >= 38.0 and (vitals.bp_systolic <= 90 or vitals.heart_rate_bpm >= 105):
        syndrome_code = "systemic_infection"
        primary_diagnosis = "Systemic Infection / Acute Viral State with Dehydration Risk"
        matched_rules.insert(0, "SYNDROME_SYSTEMIC_INFECTION")
        sys_status["respiratory"] = "CRITICAL"
        sys_status["cardiovascular"] = "CRITICAL"
        sys_actions["respiratory"] = "Initiate HSP cabin isolation, administer antipyretic & monitor SpO2 via Tempus Pro."
        sys_actions["cardiovascular"] = "Administer oral/IV electrolyte rehydration and monitor BP every 15 min on CMRS."
        stabilization_checklist = [
            "Initiate Health Stabilization Program (HSP) cabin isolation to protect crewmates from airborne transmission.",
            "Administer oral electrolyte rehydration (PWD) and approved antipyretic from CHeCS Medical Kit B.",
            "Run i-STAT blood chemistry cartridge (lactate, electrolytes, glucose) and store backup serum sample in MELFI (+4C).",
            "Maintain continuous Astroskin / Tempus Pro monitoring and transmit Priority Telemedicine Packet to Flight Surgeon.",
        ]
        notify_earth = True
        notify_crew = True

    # Behavioral Fatigue & Circadian Desynchrony
    elif (vitals.sleep_hours < 4.5 or vitals.sleep_streak_low_days >= 3) and vitals.hrv_ms <= 30 and vitals.mood_score <= 2:
        syndrome_code = "behavioral_fatigue"
        primary_diagnosis = "Severe Behavioral Fatigue & Circadian Desynchrony (Operational Error Risk)"
        matched_rules.insert(0, "SYNDROME_BEHAVIORAL_FATIGUE")
        sys_status["nervous_sleep"] = "CRITICAL"
        sys_actions["nervous_sleep"] = "Suspend EVA/robotics immediately; enforce OCHMO-MTB-009 rest schedule, dim cabin blue light, consider FMS melatonin."
        stabilization_checklist = [
            "Notify Mission Commander and Earth Behavioral Health & Performance (BHP) team immediately.",
            "Suspend safety-critical tasks (EVA, robotic arm, docking operations) per OCHMO-TB-041 fatigue limits.",
            "Enforce 8-hour protected dark/quiet sleep block; eliminate blue-spectrum CCT light 2 hours prior to sleep.",
            "Evaluate pre-tested FMS circadian countermeasures (Melatonin 0.5–3 mg or Zaleplon if prescribed) and schedule Private Psychological Conference (PPC).",
        ]
        notify_earth = True
        notify_crew = True

    # Orthostatic Intolerance / Fluid Shift Hypotension
    elif vitals.temperature_c < 37.5 and vitals.bp_systolic <= 90 and vitals.heart_rate_bpm >= 98:
        syndrome_code = "orthostatic_intolerance"
        primary_diagnosis = "Orthostatic Intolerance / Fluid-Shift Hypotension"
        matched_rules.insert(0, "SYNDROME_ORTHOSTATIC_INTOLERANCE")
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "WARNING")
        sys_actions["cardiovascular"] = "Lie supine, activate lower-limb compression garments / LBNP, ingest 500 ml isotonic saline, recheck in 15 min."
        stabilization_checklist = [
            "Assist astronaut to supine/reclined posture immediately and elevate legs or engage compression trousers.",
            "Ingest 500 ml isotonic saline / electrolyte solution via Potable Water Dispenser (PWD).",
            "Screen for post-EVA decompression symptoms (OCHMO-MTB-011 PFO protocol) if returning from suit ops.",
            "Re-measure anchored NIBP and heart rate after 15 minutes.",
        ]

    # Caloric-Deficit Hypoglycemia
    elif vitals.glucose_mg_dl <= 70 and (cal_pct < 55.0 or vitals.heart_rate_bpm >= 95):
        syndrome_code = "hypoglycemia"
        primary_diagnosis = "Caloric-Deficit Hypoglycemia & EVA Workload Strain"
        matched_rules.insert(0, "SYNDROME_CALORIC_HYPOGLYCEMIA")
        sys_status["metabolic"] = _max_status(sys_status["metabolic"], "WARNING")
        sys_actions["metabolic"] = "Ingest 15–20g fast-acting carbohydrate gel immediately; recheck glucose in 15 min and update daily meal plan."
        stabilization_checklist = [
            "Consume 15–20g rapid-absorption glucose gel or fruit pouch immediately.",
            "Pause strenuous EVA/ARED exertion for 15 minutes and confirm glucose recovery > 80 mg/dL.",
            "Log a balanced meal (>= 500 kcal, complex carbs + protein) via AstraCare chat while respecting Na <= 3500 mg & Fe <= 10 mg.",
            "If shoulder pain >= 4/10 VAS persists from EVA HUT suit, apply ice and schedule portable ultrasound (OCHMO-MTB-006).",
        ]

    # Overall severity = max across all 6 anatomical systems
    overall_status: SeverityStatus = "NOMINAL"
    for st in sys_status.values():
        overall_status = _max_status(overall_status, st)

    # If an individual critical rule tripped without matching one of the 5 named syndromes
    if syndrome_code == "nominal" and overall_status != "NOMINAL":
        if overall_status == "CRITICAL":
            primary_diagnosis = "Critical Physiological Threshold Breach — Immediate Triage Required"
            notify_earth = True
            notify_crew = True
            stabilization_checklist = [
                "Stabilize crewmember on Crew Medical Restraint System (CMRS) if required.",
                "Verify abnormal sensor reading with secondary CHeCS diagnostic device (Tempus Pro / i-STAT).",
                "Transmit Priority Telemedicine Dossier to Earth Flight Surgeon.",
            ]
        else:
            primary_diagnosis = "Sub-Critical Physiological / Nutritional Drift Detected"
            stabilization_checklist = [
                "Review flagged system alerts on 3D anatomical view and perform confirmatory manual scan.",
                "Apply targeted countermeasure (hydration, meal adjustment, circadian light shift, or shoulder rest).",
            ]

    if not stabilization_checklist:
        stabilization_checklist = [
            "Continue scheduled smartwatch passive monitoring (5-min PPG/HRV, continuous BLE dosimetry).",
            "Complete 2.5h daily ARED/T2/CEVIS countermeasure workout and log meals/water in AstraCare chat.",
        ]

    # Build SystemEvaluation objects
    systems_eval: dict[str, SystemEvaluation] = {}
    for sid, alerts in sys_alerts.items():
        guide = systems_guide.get(sid, {})
        st = sys_status[sid]
        if alerts:
            summary = alerts[0]
        else:
            summary = f"All parameters within NASA-STD-3001 nominal envelope."
        systems_eval[sid] = SystemEvaluation(
            system_id=sid,
            name=guide.get("name", sid.replace("_", " ").title()),
            status=st,
            summary=summary,
            active_alerts=alerts,
            recommended_action=sys_actions[sid],
            checs_device=guide.get("checs_device", "CHeCS Biometric Telemetry"),
            reference_standard=guide.get("reference_standard", "NASA-STD-3001"),
        )

    decon_required = bool(env_info.get("decontamination_required", False))
    decon_checklist = list(env_info.get("decontamination_checklist", []))

    return ClinicalEvaluationResult(
        overall_status=overall_status,
        primary_diagnosis=primary_diagnosis,
        syndrome_code=syndrome_code,
        matched_rules=matched_rules or ["NASA-STD-3001-ALL-NOMINAL"],
        systems=systems_eval,
        stabilization_checklist=stabilization_checklist,
        notify_earth_flight_surgeon=notify_earth,
        notify_crew_onboard=notify_crew,
        environment_calibration_notes=env_notes,
        decontamination_required=decon_required,
        decontamination_checklist=decon_checklist,
    )
