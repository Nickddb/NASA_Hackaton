from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from app.models.schemas import (
    AdaptiveBaselineProfile,
    AutonomyGuardrail,
    ClinicalEvaluationResult,
    ContextualIntelligenceReport,
    ExplainableAlert,
    MeasurementQualityProfile,
    MissionContext,
    MLPredictionResult,
    NutritionHydrationState,
    SeverityStatus,
    SystemEvaluation,
    VitalSigns,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

SEVERITY_RANK: dict[SeverityStatus, int] = {
    "NOMINAL": 0,
    "WARNING": 1,
    "CRITICAL": 2,
}

SCIENTIFIC_CITATIONS: dict[str, dict[str, str]] = {
    "NASA-STD-3001": {
        "code": "NASA-STD-3001 Vol. 1 & 2",
        "title": "NASA Space Flight Human-System Standard: Crew Health & Habitability",
        "url": "https://www.nasa.gov/ochmo/health-and-medical-systems-standards/",
    },
    "OCHMO-MTB-006": {
        "code": "OCHMO-MTB-006",
        "title": "Shoulder Injury Prevention & EVA Suit Biomechanics",
        "url": "https://www.nasa.gov/wp-content/uploads/2025/09/ochmo-mtb-006-shoulder-injury.pdf",
    },
    "OCHMO-MTB-009": {
        "code": "OCHMO-MTB-009",
        "title": "Circadian Desynchrony & Fatigue Management in Spaceflight",
        "url": "https://www.nasa.gov/wp-content/uploads/2026/03/ochmo-mtb-009-circadian-desynchrony.pdf",
    },
    "OCHMO-MTB-011": {
        "code": "OCHMO-MTB-011",
        "title": "Patent Foramen Ovale (PFO) & EVA Decompression Risk",
        "url": "https://www.nasa.gov/wp-content/uploads/2026/11/ochmo-mtb-011-patent-foramen-ovale-pfo.pdf",
    },
    "OCHMO-TB-043": {
        "code": "OCHMO-TB-043",
        "title": "Longitudinal Health Surveillance (LHS) & SANS Screening",
        "url": "https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-043-longitudinal-health-surveillance.pdf",
    },
    "OCHMO-TB-044": {
        "code": "OCHMO-TB-044",
        "title": "Medical Operations Requirements Document (MORD)",
        "url": "https://www.nasa.gov/wp-content/uploads/2025/08/ochmo-tb-044-medical-operations.pdf",
    },
    "NASA-OSDR-570": {
        "code": "NASA OSDR OSD-570 / OSD-571",
        "title": "Spaceflight Standard Measures: Longitudinal Physiology & Countermeasure Kinetics",
        "url": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-570",
    },
    "CSA-RAD-ALARA": {
        "code": "CSA Bio-Monitor & NASA ALARA",
        "title": "Monitoring Radiation for Astronaut Health & SPE Storm Shelter Protocol",
        "url": "https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp",
    },
}


def _max_status(a: SeverityStatus, b: SeverityStatus) -> SeverityStatus:
    return a if SEVERITY_RANK[a] >= SEVERITY_RANK[b] else b


def load_scenarios_catalog() -> dict[str, Any]:
    with open(DATA_DIR / "scenarios.json", "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_clinical_and_explainable_rules(
    vitals: VitalSigns,
    nutrition: NutritionHydrationState,
    environment_id: str,
    context: MissionContext,
    quality: MeasurementQualityProfile,
    adaptive_baseline: AdaptiveBaselineProfile,
    contextual_report: ContextualIntelligenceReport,
    ml_prediction: MLPredictionResult,
    catalog: dict[str, Any] | None = None,
) -> ClinicalEvaluationResult:
    """
    Combines Layer 1 Deterministic NASA-STD-3001 / OCHMO rules with Layer 2 Adaptive Baseline,
    Contextual Intelligence, and Calibrated ML to produce Explainable & Auditable Clinical Alerts.
    """
    if catalog is None:
        catalog = load_scenarios_catalog()

    systems_guide = catalog.get("systems_guide", {})
    environments = {e["id"]: e for e in catalog.get("environments", [])}
    env_info = environments.get(environment_id, environments.get("transit", {}))

    matched_rules: list[str] = []
    stabilization_checklist: list[str] = []
    env_notes: list[str] = []

    if environment_id == "transit":
        env_notes.append(
            "0g Microgravity Transit Calibration: Cephalic fluid-shift correction (+6 mmHg hydrostatic compensation) applied to NIBP baseline; wireless BLE telemetry active."
        )
    elif environment_id == "orbital_station":
        env_notes.append(
            "Orbital Station (ISS/Gateway) Calibration: Cabin circadian LED CCT synchronized to sleep shift (OCHMO-MTB-009); full CHeCS rack online."
        )
    elif environment_id == "planetary_surface":
        env_notes.append(
            "Planetary Surface Calibration (1/6g Lunar / 3/8g Mars): Mandatory electrostatic/HEPA regolith & perchlorate decontamination required before active capillary puncture or NIBP cuff exams."
        )

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

    is_post_exercise_confounder = (
        contextual_report.context_explains_deviation
        and context.minutes_since_last_exercise <= 60.0
        and vitals.bp_systolic >= 100.0
        and vitals.temperature_c < 38.0
    )

    # 1. Cardiovascular (Population + Personal Adaptive Baseline + Post-Exercise Context)
    hr_ind_z = adaptive_baseline.metrics["heart_rate_bpm"].individual_z_score
    if is_post_exercise_confounder and vitals.heart_rate_bpm >= 95:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "WARNING")
        sys_alerts["cardiovascular"].append(
            f"Post-exercise physiological tachycardia ({vitals.heart_rate_bpm:.0f} bpm, {context.minutes_since_last_exercise:.0f}m after {context.exercise_modality}) — Verify return to personal baseline ({adaptive_baseline.metrics['heart_rate_bpm'].rolling_ewma_baseline:.0f} bpm) after 20m rest."
        )
        sys_actions["cardiovascular"] = (
            "Rest seated/anchored for 20 minutes, hydrate 300 ml PWD water, and execute confirmatory resting PPG/NIBP check."
        )
        matched_rules.append("CTX-OSD571-POST-EXERCISE-HR")
    elif vitals.heart_rate_bpm >= 110 or vitals.heart_rate_bpm <= 44:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "CRITICAL")
        sys_alerts["cardiovascular"].append(
            f"Heart rate out of flight rule: {vitals.heart_rate_bpm:.0f} bpm (Personal z={hr_ind_z:+.1f}σ)"
        )
        matched_rules.append("NASA-STD-3001-CV-HR-CRIT")
    elif vitals.heart_rate_bpm >= 95 or vitals.heart_rate_bpm <= 50 or abs(hr_ind_z) >= 2.8:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "WARNING")
        sys_alerts["cardiovascular"].append(
            f"Elevated/shifted heart rate vs personal baseline: {vitals.heart_rate_bpm:.0f} bpm (Personal baseline {adaptive_baseline.metrics['heart_rate_bpm'].rolling_ewma_baseline:.0f} bpm, z={hr_ind_z:+.1f}σ)"
        )
        matched_rules.append("NASA-STD-3001-CV-HR-WARN")

    if vitals.bp_systolic <= 85 or vitals.bp_systolic >= 165:
        sys_status["cardiovascular"] = _max_status(
            sys_status["cardiovascular"], "CRITICAL" if vitals.bp_systolic <= 82 else "WARNING"
        )
        sys_alerts["cardiovascular"].append(
            f"Abnormal blood pressure: {vitals.bp_systolic:.0f}/{vitals.bp_diastolic:.0f} mmHg"
        )
        matched_rules.append("NASA-STD-3001-CV-BP-ABNORMAL")
    elif vitals.bp_systolic <= 92 or (not is_post_exercise_confounder and vitals.bp_systolic >= 130):
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "WARNING")
        sys_alerts["cardiovascular"].append(
            f"Blood pressure shift vs personal baseline: {vitals.bp_systolic:.0f}/{vitals.bp_diastolic:.0f} mmHg"
        )
        matched_rules.append("NASA-STD-3001-CV-BP-SHIFT")

    if vitals.hrv_ms <= 24:
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "CRITICAL")
        sys_status["nervous_sleep"] = _max_status(sys_status["nervous_sleep"], "CRITICAL")
        sys_alerts["cardiovascular"].append(f"Severe HRV suppression ({vitals.hrv_ms:.0f} ms)")
        matched_rules.append("AUTONOMIC-HRV-COLLAPSE")
    elif vitals.hrv_ms < 35 and not is_post_exercise_confounder:
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

    # 2. Respiratory, Cabin CO2 & Thermal
    if vitals.temperature_c >= 38.0:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "CRITICAL")
        sys_alerts["respiratory"].append(f"High fever detected: {vitals.temperature_c:.1f} C")
        matched_rules.append("NASA-STD-3001-TEMP-FEVER")
    elif (vitals.temperature_c >= 37.5 or vitals.temperature_c < 35.8) and not is_post_exercise_confounder:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "WARNING")
        sys_alerts["respiratory"].append(f"Temperature outside nominal range: {vitals.temperature_c:.1f} C")
        matched_rules.append("NASA-STD-3001-TEMP-DRIFT")

    if context.cabin_co2_mmhg >= 3.5:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "WARNING")
        sys_alerts["respiratory"].append(
            f"Localized Cabin CO2 Pocket ({context.cabin_co2_mmhg:.1f} mmHg) correlated with RR {vitals.respiration_rpm:.0f} rpm & SpO2 {vitals.spo2_pct:.1f}%."
        )
        sys_actions["respiratory"] = (
            "Increase local module ventilation fan speed, inspect CDRA scrubber bed, and re-verify SpO2/capnography in 30 minutes."
        )
        matched_rules.append("NASA-STD-3001-CABIN-CO2-WARN")

    if vitals.spo2_pct < 94.0 or vitals.respiration_rpm >= 24:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "CRITICAL")
        sys_alerts["respiratory"].append(
            f"Hypoxemia / tachypnea: SpO2 {vitals.spo2_pct:.1f}%, RR {vitals.respiration_rpm:.0f} rpm"
        )
        matched_rules.append("NASA-STD-3001-RESP-CRIT")
    elif (vitals.spo2_pct < 95.5 or vitals.respiration_rpm >= 20) and not is_post_exercise_confounder:
        sys_status["respiratory"] = _max_status(sys_status["respiratory"], "WARNING")
        sys_alerts["respiratory"].append(
            f"Borderline respiratory effort: SpO2 {vitals.spo2_pct:.1f}%, RR {vitals.respiration_rpm:.0f} rpm"
        )
        matched_rules.append("NASA-STD-3001-RESP-WARN")

    # 3. Nervous, Sleep, Behavioral & SANS
    if vitals.sleep_hours < 4.5 or vitals.sleep_streak_low_days >= 3:
        sys_status["nervous_sleep"] = _max_status(
            sys_status["nervous_sleep"], "CRITICAL" if vitals.sleep_streak_low_days >= 3 else "WARNING"
        )
        sys_alerts["nervous_sleep"].append(
            f"Sleep deficit ({vitals.sleep_hours:.1f}h; {vitals.sleep_streak_low_days} consecutive short nights; REM {vitals.rem_sleep_pct:.0f}%)"
        )
        matched_rules.append("OCHMO-MTB-009-SLEEP-DEFICIT")
    elif vitals.sleep_hours < 6.5:
        sys_status["nervous_sleep"] = _max_status(sys_status["nervous_sleep"], "WARNING")
        sys_alerts["nervous_sleep"].append(f"Sub-optimal sleep duration: {vitals.sleep_hours:.1f}h")
        matched_rules.append("OCHMO-MTB-009-SLEEP-DRIFT")

    if vitals.mood_score <= 2 or vitals.stress_index >= 75:
        sys_status["nervous_sleep"] = _max_status(
            sys_status["nervous_sleep"],
            "CRITICAL" if (vitals.mood_score <= 2 and vitals.sleep_streak_low_days >= 3) else "WARNING",
        )
        sys_alerts["nervous_sleep"].append(
            f"Elevated behavioral strain (Mood {vitals.mood_score}/5, Stress {vitals.stress_index:.0f}%)"
        )
        matched_rules.append("NASA-BHP-BEHAVIORAL-STRAIN")

    if vitals.intraocular_pressure_mmhg >= 18.0:
        sys_status["nervous_sleep"] = _max_status(sys_status["nervous_sleep"], "WARNING")
        sys_alerts["nervous_sleep"].append(
            f"Elevated IOP ({vitals.intraocular_pressure_mmhg:.1f} mmHg) — Screen for SANS via OCT/Fundoscope (OCHMO-TB-043)."
        )
        matched_rules.append("OCHMO-TB-043-SANS-IOP")

    # 4. Metabolic & Nutrition
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

    # 5. Musculoskeletal
    if vitals.shoulder_pain_score >= 7:
        sys_status["musculoskeletal"] = _max_status(sys_status["musculoskeletal"], "CRITICAL")
        sys_alerts["musculoskeletal"].append(
            f"Severe EVA shoulder pain ({vitals.shoulder_pain_score}/10 VAS) — Suspect rotator cuff tear/impingement."
        )
        sys_actions["musculoskeletal"] = (
            "Suspend EVA/overhead tasks; run portable Ultrasound 2 scan, Hawkin/Empty-Can test, apply ice & analgesic."
        )
        matched_rules.append("OCHMO-MTB-006-SHOULDER-CRIT")
    elif vitals.shoulder_pain_score >= 4:
        sys_status["musculoskeletal"] = _max_status(sys_status["musculoskeletal"], "WARNING")
        sys_alerts["musculoskeletal"].append(
            f"Moderate EVA HUT shoulder pain ({vitals.shoulder_pain_score}/10 VAS) — Rotator cuff / bicipital tendonitis watch."
        )
        sys_actions["musculoskeletal"] = (
            "Modify overhead EVA tasks, run portable musculoskeletal ultrasound, apply ice + NSAID + scapular rehab."
        )
        matched_rules.append("OCHMO-MTB-006-SHOULDER-WARN")

    if vitals.urinary_calcium_mg_d > 230.0:
        sys_status["musculoskeletal"] = _max_status(sys_status["musculoskeletal"], "WARNING")
        sys_alerts["musculoskeletal"].append(
            f"Elevated Urolux urinary calcium ({vitals.urinary_calcium_mg_d:.0f} mg/day) — Accelerated bone resorption / stone risk."
        )
        matched_rules.append("OCHMO-TB-043-BONE-CALCIUM")

    # 6. Radiation
    if vitals.radiation_msv_h >= 0.50:
        sys_status["radiation"] = _max_status(sys_status["radiation"], "CRITICAL")
        sys_alerts["radiation"].append(
            f"Acute Solar Particle Event dose spike: {vitals.radiation_msv_h:.2f} mSv/h (>0.50 threshold)"
        )
        matched_rules.append("NASA-ALARA-SPE-CRIT")
    elif vitals.radiation_msv_h >= 0.15:
        sys_status["radiation"] = _max_status(sys_status["radiation"], "WARNING")
        sys_alerts["radiation"].append(f"Elevated cosmic/solar radiation rate: {vitals.radiation_msv_h:.2f} mSv/h")
        matched_rules.append("NASA-ALARA-RAD-WARN")

    # --- Determine Primary Syndrome & Protocol Checklists ---
    primary_diagnosis = "Nominal Spaceflight Physiological Status"
    syndrome_code = "nominal"
    notify_earth = False
    notify_crew = False

    if vitals.radiation_msv_h >= 0.50:
        syndrome_code = "solar_storm"
        primary_diagnosis = "Solar Particle Event (SPE) — Acute Radiation Spike"
        matched_rules.insert(0, "SYNDROME_SOLAR_PARTICLE_EVENT")
        sys_actions["radiation"] = (
            "Relocate immediately to water/polyethylene-shielded storm shelter; halt EVA; transmit ALARA telemetry."
        )
        stabilization_checklist = [
            "Acknowledge wristwatch haptic radiation alarm and cease all EVA/unshielded hull tasks immediately.",
            "Relocate all crew to the designated polyethylene/water-wall Radiation Storm Shelter.",
            "Verify personal BLE dosimeters and check NASA DONKI SEP proton flux decay trend every 15 minutes.",
            "Confirm automated Priority Telemetry Downlink receipt by Earth Radiation Health Officer (RHO).",
        ]
        notify_earth = True
        notify_crew = True
    elif vitals.temperature_c >= 38.0 and (vitals.bp_systolic <= 90 or vitals.heart_rate_bpm >= 105):
        syndrome_code = "systemic_infection"
        primary_diagnosis = "Systemic Infection / Acute Viral State with Dehydration Risk"
        matched_rules.insert(0, "SYNDROME_SYSTEMIC_INFECTION")
        sys_status["respiratory"] = "CRITICAL"
        sys_status["cardiovascular"] = "CRITICAL"
        sys_actions["respiratory"] = (
            "Confirm core temp via sublingual/tympanic IR; initiate HSP cabin isolation & monitor SpO2 via Tempus Pro."
        )
        sys_actions["cardiovascular"] = (
            "Verify hypotension via anchored NIBP cuff; initiate oral/IV electrolyte rehydration per CMO confirmation."
        )
        stabilization_checklist = [
            "CONFIRMATION STEP: Measure tympanic IR temperature and anchored brachial NIBP after 10 min rest.",
            "Initiate Health Stabilization Program (HSP) cabin isolation and verify HEPA air filtration.",
            "Administer oral electrolyte rehydration (PWD) and consult CMO for CHeCS Medical Kit B protocol.",
            "Draw capillary blood sample for i-STAT CHEM8+/lactate cartridge and store twin bio-sample in MELFI (-80 C).",
        ]
        notify_earth = True
        notify_crew = True
    elif vitals.bp_systolic <= 90 and vitals.heart_rate_bpm >= 100 and vitals.temperature_c < 37.5:
        syndrome_code = "orthostatic_intolerance"
        primary_diagnosis = "Orthostatic Intolerance / Post-EVA Fluid Shift & Hypovolemia"
        matched_rules.insert(0, "SYNDROME_ORTHOSTATIC_INTOLERANCE")
        sys_status["cardiovascular"] = _max_status(sys_status["cardiovascular"], "WARNING")
        sys_actions["cardiovascular"] = (
            "Assume supine/anchored posture, administer 500 ml isotonic fluid bolus, and re-verify NIBP cuff in 15 min."
        )
        stabilization_checklist = [
            "CONFIRMATION STEP: Perform anchored supine & seated NIBP cuff readings 5 minutes apart.",
            "Assist crew member into anchored restraint posture; elevate lower extremities if in partial gravity.",
            "Administer 500 ml isotonic oral rehydration solution (PWD + sodium electrolyte tab).",
            "If post-EVA with PFO risk flag, screen with portable Ultrasound 2 for venous gas emboli (OCHMO-MTB-011).",
        ]
        notify_earth = True
    elif vitals.sleep_hours < 4.5 and vitals.sleep_streak_low_days >= 3 and vitals.hrv_ms <= 26:
        syndrome_code = "behavioral_fatigue"
        primary_diagnosis = "Severe Behavioral Fatigue & Circadian Desynchrony (OCHMO-MTB-009)"
        matched_rules.insert(0, "SYNDROME_BEHAVIORAL_FATIGUE")
        sys_status["nervous_sleep"] = "CRITICAL"
        sys_actions["nervous_sleep"] = (
            "Recommend temporary suspension of high-risk EVA/robotics; enforce 8h protected sleep shift with blue-light block."
        )
        stabilization_checklist = [
            "CONFIRMATION STEP: Complete 3-minute Psychomotor Vigilance Task (PVT) cognitive reaction check.",
            "Recommend rescheduling non-critical EVA or robotic arm operations per OCHMO-MTB-009 fatigue flight rule.",
            "Configure crew quarters solid-state lighting to warm low-CCT (<2700K, <10 lux) 90 minutes before sleep.",
            "Schedule private behavioral health check-in and reassess HRV RMSSD after next recovery sleep cycle.",
        ]
        notify_earth = True
    elif vitals.glucose_mg_dl <= 70 and cal_pct < 50.0:
        syndrome_code = "hypoglycemia"
        primary_diagnosis = "Caloric-Deficit Hypoglycemia & EVA Musculoskeletal Strain"
        matched_rules.insert(0, "SYNDROME_CALORIC_HYPOGLYCEMIA")
        sys_status["metabolic"] = _max_status(sys_status["metabolic"], "WARNING")
        sys_actions["metabolic"] = (
            "Confirm capillary blood glucose via i-STAT/strip; ingest 15–30g rapid carbohydrate gel and recheck at T+15 min."
        )
        stabilization_checklist = [
            "CONFIRMATION STEP: Verify interstitial CGM reading with shielded capillary glucose strip / i-STAT.",
            "Pause high-exertion physical tasks and consume 20g rapid-absorption glucose pouch + 300 ml water.",
            "Repeat blood glucose measurement at T+15 minutes until >= 85 mg/dL, then follow with balanced protein/carb meal.",
            "Inspect EVA shoulder ROM and run portable Ultrasound 2 scan for HUT rotator-cuff impingement (OCHMO-MTB-006).",
        ]
        notify_earth = False
    elif is_post_exercise_confounder:
        syndrome_code = "post_exercise_physiological"
        primary_diagnosis = "Contextual Confounder: Physiological Post-Exercise Recovery (Non-Pathological)"
        matched_rules.insert(0, "CTX_PHYSIOLOGICAL_EXERCISE_RECOVERY")
        stabilization_checklist = [
            "CONFIRMATION STEP: Rest quietly for 20 minutes away from ARED/T2 rack and repeat HR & tympanic temp measurement.",
            "Hydrate with 350 ml water to replenish countermeasure sweat loss.",
            "No clinical treatment indicated unless tachycardia (>95 bpm) or thermal elevation persists after 30m recovery.",
        ]
    elif context.cabin_co2_mmhg >= 3.5:
        syndrome_code = "cabin_co2_pocket"
        primary_diagnosis = "Contextual Exposure: Localized Cabin CO2 Pocket (Hypercapnic Drift)"
        matched_rules.insert(0, "CTX_CABIN_CO2_EXPOSURE")
        stabilization_checklist = [
            "CONFIRMATION STEP: Verify module ppCO2 sensor and crew end-tidal CO2 via Tempus Pro capnography.",
            "Relocate crew member to high-ventilation node and increase inter-module fan flow.",
            "Reassess respiratory rate, SpO2, and headache/IOP status 30 minutes after ventilation adjustment.",
        ]

    # Build system evaluations
    decon_required = bool(env_info.get("decontamination_required", False))
    decon_list = list(env_info.get("decontamination_checklist", []))

    systems_out: dict[str, SystemEvaluation] = {}
    overall_status: SeverityStatus = "NOMINAL"

    for sys_id, guide in systems_guide.items():
        st = sys_status.get(sys_id, "NOMINAL")
        if is_post_exercise_confounder and st == "WARNING" and sys_id == "cardiovascular":
            # Keep overall status NOMINAL/WARNING clearly labeled as physiological exercise recovery
            pass
        else:
            overall_status = _max_status(overall_status, st)
        alerts = sys_alerts.get(sys_id, [])
        summary = (
            alerts[0]
            if alerts
            else f"All {guide.get('name', sys_id)} biomarkers within personal & NASA-STD-3001 bounds."
        )
        systems_out[sys_id] = SystemEvaluation(
            system_id=sys_id,
            name=guide.get("name", sys_id),
            status=st,
            summary=summary,
            active_alerts=alerts,
            recommended_action=sys_actions.get(sys_id, "Continue scheduled passive telemetry monitoring."),
            checs_device=guide.get("checs_device", "Biometric Smartwatch"),
            reference_standard=guide.get("reference_standard", "NASA-STD-3001"),
        )

    # --- PILLAR 4: Generate Explainable & Auditable Alerts ---
    explainable_alerts: list[ExplainableAlert] = []
    if syndrome_code != "nominal" or overall_status != "NOMINAL":
        originating_signals: list[dict[str, Any]] = []
        for feat in ml_prediction.feature_importances[:5]:
            originating_signals.append(
                {
                    "metric": feat.feature,
                    "label": feat.label,
                    "current_value": feat.current_value,
                    "personal_ewma_baseline": feat.personal_baseline_value,
                    "population_baseline": feat.baseline_value,
                    "individual_z_score": feat.individual_z_score,
                    "population_z_score": feat.population_z_score,
                    "attribution_weight_pct": feat.importance,
                    "direction": feat.direction,
                }
            )

        # Select relevant scientific citations
        refs: list[dict[str, str]] = [SCIENTIFIC_CITATIONS["NASA-STD-3001"], SCIENTIFIC_CITATIONS["NASA-OSDR-570"]]
        if syndrome_code == "solar_storm":
            refs.append(SCIENTIFIC_CITATIONS["CSA-RAD-ALARA"])
        elif syndrome_code == "behavioral_fatigue":
            refs.append(SCIENTIFIC_CITATIONS["OCHMO-MTB-009"])
        elif syndrome_code == "orthostatic_intolerance":
            refs.append(SCIENTIFIC_CITATIONS["OCHMO-MTB-011"])
        elif syndrome_code == "hypoglycemia":
            refs.append(SCIENTIFIC_CITATIONS["OCHMO-MTB-006"])
        else:
            refs.append(SCIENTIFIC_CITATIONS["OCHMO-TB-044"])

        ctx_factors = [
            f"{a.factor_name}: {a.observed_context_value} ({a.relationship_type}, strength={a.association_strength:.2f})"
            for a in contextual_report.associations
        ]
        if not ctx_factors:
            ctx_factors.append(
                f"Mission Phase: {context.mission_phase} ({context.gravitational_g:.2f}g) | Rested ({context.minutes_since_last_exercise:.0f}m post-exercise)"
            )

        primary_sys = (
            "radiation"
            if syndrome_code == "solar_storm"
            else (
                "respiratory"
                if syndrome_code in ("systemic_infection", "cabin_co2_pocket")
                else (
                    "nervous_sleep"
                    if syndrome_code == "behavioral_fatigue"
                    else ("metabolic" if syndrome_code == "hypoglycemia" else "cardiovascular")
                )
            )
        )

        alert_sev: SeverityStatus = (
            "NOMINAL"
            if syndrome_code == "post_exercise_physiological"
            else (overall_status if overall_status != "NOMINAL" else "WARNING")
        )

        explainable_alerts.append(
            ExplainableAlert(
                alert_id=f"ALT-{adaptive_baseline.astronaut_id[:5].upper()}-D{adaptive_baseline.mission_day}-{syndrome_code[:6].upper()}",
                created_at=datetime.now(timezone.utc).isoformat(),
                severity=alert_sev,
                system_id=primary_sys,
                syndrome_candidate=syndrome_code,
                title=primary_diagnosis,
                explanation_summary=(
                    f"Triggered by personal adaptive drift ({adaptive_baseline.personal_drift_score:.1f}%, "
                    f"Mahalanobis={adaptive_baseline.multivariate_mahalanobis_distance:.2f}) and calibrated ML classification "
                    f"({ml_prediction.predicted_syndrome_label}: {ml_prediction.confidence_pct:.1f}% ± "
                    f"{ml_prediction.uncertainty.total_uncertainty_pct:.1f}% uncertainty; Sensor Reliability: {quality.reliability_grade})."
                ),
                originating_signals=originating_signals,
                measurement_quality=quality,
                uncertainty=ml_prediction.uncertainty,
                contextual_factors=ctx_factors,
                causal_disclaimer=contextual_report.causal_disclaimer,
                scientific_references=refs,
                recommended_verification_steps=stabilization_checklist[:3]
                if stabilization_checklist
                else ["Repeat resting sensor measurement in 15 minutes and verify sensor placement."],
                autonomy_guardrail=AutonomyGuardrail(),
            )
        )

    return ClinicalEvaluationResult(
        overall_status=overall_status,
        primary_diagnosis=primary_diagnosis,
        syndrome_code=syndrome_code,
        matched_rules=matched_rules,
        systems=systems_out,
        stabilization_checklist=stabilization_checklist,
        notify_earth_flight_surgeon=notify_earth,
        notify_crew_onboard=notify_crew,
        environment_calibration_notes=env_notes,
        decontamination_required=decon_required,
        decontamination_checklist=decon_list,
        explainable_alerts=explainable_alerts,
        autonomy_guardrail=AutonomyGuardrail(),
    )
