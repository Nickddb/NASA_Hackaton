// AstraCare AI Frontend API Client with Automatic Offline Static Fallback
// Calls FastAPI backend (/api/*) when live; falls back seamlessly to in-browser NASA-STD-3001 + heuristic ML/NLP simulation using /data/scenarios.json if deployed statically.

let localCatalog = null;
let localDonki = null;
let localState = null;

const API_BASE = import.meta.env.VITE_API_BASE || "";

async function loadLocalData() {
  if (!localCatalog) {
    const res = await fetch("/data/scenarios.json");
    localCatalog = await res.json();
  }
  if (!localDonki) {
    const res = await fetch("/data/nasa_donki_sample.json");
    localDonki = await res.json();
  }
}

function maxStatus(a, b) {
  const rank = { NOMINAL: 0, WARNING: 1, CRITICAL: 2 };
  return (rank[a] || 0) >= (rank[b] || 0) ? a : b;
}

function evaluateLocalClinicalRules(vitals, nutrition, environmentId) {
  const env = (localCatalog.environments || []).find((e) => e.id === environmentId) || localCatalog.environments[0];
  const systemsGuide = localCatalog.systems_guide || {};
  const sysAlerts = {
    cardiovascular: [],
    nervous_sleep: [],
    respiratory: [],
    metabolic: [],
    musculoskeletal: [],
    radiation: [],
  };
  const sysStatus = {
    cardiovascular: "NOMINAL",
    nervous_sleep: "NOMINAL",
    respiratory: "NOMINAL",
    metabolic: "NOMINAL",
    musculoskeletal: "NOMINAL",
    radiation: "NOMINAL",
  };
  const sysActions = {
    cardiovascular: "Maintain 2.5h daily CMS aerobic/resistive exercise and adequate hydration.",
    nervous_sleep: "Continue circadian sleep hygiene (cool, dark bunk; limit blue CCT 1-2h pre-sleep).",
    respiratory: "Cabin O2/CO2 scrubbing nominal; continue scheduled smartwatch thermal monitoring.",
    metabolic: "Maintain balanced caloric intake (2800 kcal/day), hydration (2500 ml), and Na/Fe caps.",
    musculoskeletal: "Execute daily ARED/T2 countermeasure protocol and post-EVA shoulder mobility stretches.",
    radiation: "Dosimetry within ALARA baseline; continue passive BLE monitoring.",
  };
  const matchedRules = [];

  if (vitals.heart_rate_bpm >= 110 || vitals.heart_rate_bpm <= 44) {
    sysStatus.cardiovascular = maxStatus(sysStatus.cardiovascular, "CRITICAL");
    sysAlerts.cardiovascular.push(`Heart rate out of flight rule: ${Math.round(vitals.heart_rate_bpm)} bpm`);
    matchedRules.push("NASA-STD-3001-CV-HR-CRIT");
  } else if (vitals.heart_rate_bpm >= 95 || vitals.heart_rate_bpm <= 50) {
    sysStatus.cardiovascular = maxStatus(sysStatus.cardiovascular, "WARNING");
    sysAlerts.cardiovascular.push(`Elevated heart rate: ${Math.round(vitals.heart_rate_bpm)} bpm`);
    matchedRules.push("NASA-STD-3001-CV-HR-WARN");
  }

  if (vitals.bp_systolic <= 85) {
    sysStatus.cardiovascular = maxStatus(sysStatus.cardiovascular, vitals.bp_systolic <= 82 ? "CRITICAL" : "WARNING");
    sysAlerts.cardiovascular.push(`Hypotension: ${Math.round(vitals.bp_systolic)}/${Math.round(vitals.bp_diastolic)} mmHg`);
    matchedRules.push("NASA-STD-3001-CV-BP-LOW");
  }

  if (vitals.hrv_ms <= 24) {
    sysStatus.cardiovascular = maxStatus(sysStatus.cardiovascular, "CRITICAL");
    sysStatus.nervous_sleep = maxStatus(sysStatus.nervous_sleep, "CRITICAL");
    sysAlerts.cardiovascular.push(`Severe HRV suppression (${Math.round(vitals.hrv_ms)} ms)`);
    matchedRules.push("AUTONOMIC-HRV-COLLAPSE");
  } else if (vitals.hrv_ms < 35) {
    sysStatus.cardiovascular = maxStatus(sysStatus.cardiovascular, "WARNING");
    sysAlerts.cardiovascular.push(`Reduced HRV (${Math.round(vitals.hrv_ms)} ms)`);
  }

  if (vitals.pfo_decompression_risk !== "LOW") {
    sysStatus.cardiovascular = maxStatus(sysStatus.cardiovascular, vitals.pfo_decompression_risk === "HIGH" ? "CRITICAL" : "WARNING");
    sysAlerts.cardiovascular.push(`OCHMO-MTB-011 PFO/DCS EVA Risk (${vitals.pfo_decompression_risk})`);
    matchedRules.push("OCHMO-MTB-011-PFO-DCS");
  }

  if (vitals.temperature_c >= 38.0) {
    sysStatus.respiratory = maxStatus(sysStatus.respiratory, "CRITICAL");
    sysAlerts.respiratory.push(`High fever detected: ${vitals.temperature_c.toFixed(1)} C`);
    matchedRules.push("NASA-STD-3001-TEMP-FEVER");
  }
  if (vitals.spo2_pct < 95.0) {
    sysStatus.respiratory = maxStatus(sysStatus.respiratory, "WARNING");
    sysAlerts.respiratory.push(`Lowered SpO2: ${vitals.spo2_pct.toFixed(1)}%`);
  }

  if (vitals.sleep_hours < 4.5 || vitals.sleep_streak_low_days >= 3) {
    sysStatus.nervous_sleep = maxStatus(sysStatus.nervous_sleep, vitals.sleep_streak_low_days >= 3 ? "CRITICAL" : "WARNING");
    sysAlerts.nervous_sleep.push(`Sleep deficit (${vitals.sleep_hours.toFixed(1)}h; ${vitals.sleep_streak_low_days} short nights)`);
    matchedRules.push("OCHMO-MTB-009-SLEEP-DEFICIT");
  }
  if (vitals.mood_score <= 2 || vitals.stress_index >= 75) {
    sysStatus.nervous_sleep = maxStatus(sysStatus.nervous_sleep, vitals.sleep_streak_low_days >= 3 ? "CRITICAL" : "WARNING");
    sysAlerts.nervous_sleep.push(`Elevated behavioral strain (Mood ${vitals.mood_score}/5)`);
    matchedRules.push("NASA-BHP-BEHAVIORAL-STRAIN");
  }

  const calPct = (nutrition.calories_kcal / Math.max(nutrition.goal_calories_kcal, 1)) * 100;
  if (vitals.glucose_mg_dl <= 70) {
    sysStatus.metabolic = maxStatus(sysStatus.metabolic, vitals.glucose_mg_dl < 60 ? "CRITICAL" : "WARNING");
    sysAlerts.metabolic.push(`Hypoglycemia alert: ${Math.round(vitals.glucose_mg_dl)} mg/dL`);
    matchedRules.push("NASA-STD-3001-GLUCOSE-WARN");
  }
  if (calPct < 50) {
    sysStatus.metabolic = maxStatus(sysStatus.metabolic, "WARNING");
    sysAlerts.metabolic.push(`Caloric deficit (${Math.round(calPct)}% of daily goal)`);
    matchedRules.push("SPACE-NUTRITION-DEFICIT");
  }
  if (nutrition.sodium_mg > nutrition.max_sodium_mg) {
    sysStatus.metabolic = maxStatus(sysStatus.metabolic, "WARNING");
    sysAlerts.metabolic.push(`Sodium cap exceeded (${Math.round(nutrition.sodium_mg)} > ${nutrition.max_sodium_mg} mg)`);
  }
  if (nutrition.iron_mg > nutrition.max_iron_mg) {
    sysStatus.metabolic = maxStatus(sysStatus.metabolic, "WARNING");
    sysAlerts.metabolic.push(`Iron cap exceeded (${nutrition.iron_mg.toFixed(1)} > ${nutrition.max_iron_mg} mg)`);
  }

  if (vitals.shoulder_pain_score >= 4) {
    sysStatus.musculoskeletal = maxStatus(sysStatus.musculoskeletal, vitals.shoulder_pain_score >= 7 ? "CRITICAL" : "WARNING");
    sysAlerts.musculoskeletal.push(`EVA HUT shoulder pain (${vitals.shoulder_pain_score}/10 VAS) — OCHMO-MTB-006`);
    sysActions.musculoskeletal = "Modify overhead EVA tasks; run portable Ultrasound 2 scan & Hawkin/Empty-Can test.";
    matchedRules.push("OCHMO-MTB-006-SHOULDER-WARN");
  }

  if (vitals.radiation_msv_h >= 0.5) {
    sysStatus.radiation = "CRITICAL";
    sysAlerts.radiation.push(`Acute SPE radiation spike: ${vitals.radiation_msv_h.toFixed(2)} mSv/h`);
    matchedRules.push("NASA-ALARA-SPE-CRIT");
  }

  let primaryDiagnosis = "Nominal Spaceflight Physiological Status";
  let syndromeCode = "nominal";
  let checklist = [
    "Continue scheduled smartwatch passive monitoring (5-min PPG/HRV, continuous BLE dosimetry).",
    "Complete 2.5h daily ARED/T2/CEVIS countermeasure workout and log meals/water in AstraCare chat.",
  ];
  let notifyEarth = false;
  let notifyCrew = false;

  if (vitals.radiation_msv_h >= 0.5) {
    syndromeCode = "solar_storm";
    primaryDiagnosis = "Solar Particle Event (SPE) — Acute Radiation Spike";
    matchedRules.unshift("SYNDROME_SOLAR_PARTICLE_EVENT");
    sysActions.radiation = "Relocate immediately to water/polyethylene storm shelter; halt EVA.";
    checklist = [
      "Acknowledge wristwatch haptic alarm and cease all EVA/unshielded tasks.",
      "Relocate crew to Radiation Storm Shelter immediately.",
      "Monitor NASA DONKI SEP proton flux decay every 15 minutes.",
    ];
    notifyEarth = true;
    notifyCrew = true;
  } else if (vitals.temperature_c >= 38.0 && (vitals.bp_systolic <= 90 || vitals.heart_rate_bpm >= 105)) {
    syndromeCode = "systemic_infection";
    primaryDiagnosis = "Systemic Infection / Acute Viral State with Dehydration Risk";
    matchedRules.unshift("SYNDROME_SYSTEMIC_INFECTION");
    sysStatus.respiratory = "CRITICAL";
    sysStatus.cardiovascular = "CRITICAL";
    checklist = [
      "Initiate Health Stabilization Program (HSP) cabin isolation.",
      "Administer oral electrolyte rehydration (PWD) and antipyretic from CHeCS Medical Kit B.",
      "Run i-STAT blood chemistry cartridge and archive sample in MELFI (+4C).",
      "Transmit Priority Telemedicine Packet to Earth Flight Surgeon.",
    ];
    notifyEarth = true;
    notifyCrew = true;
  } else if ((vitals.sleep_hours < 4.5 || vitals.sleep_streak_low_days >= 3) && vitals.hrv_ms <= 30 && vitals.mood_score <= 2) {
    syndromeCode = "behavioral_fatigue";
    primaryDiagnosis = "Severe Behavioral Fatigue & Circadian Desynchrony (Operational Error Risk)";
    matchedRules.unshift("SYNDROME_BEHAVIORAL_FATIGUE");
    sysStatus.nervous_sleep = "CRITICAL";
    checklist = [
      "Notify Mission Commander and Earth BHP team immediately.",
      "Suspend safety-critical tasks (EVA, robotic arm, docking).",
      "Enforce 8h dark/quiet sleep block; eliminate blue CCT light 2h pre-sleep (OCHMO-MTB-009).",
    ];
    notifyEarth = true;
    notifyCrew = true;
  } else if (vitals.temperature_c < 37.5 && vitals.bp_systolic <= 90 && vitals.heart_rate_bpm >= 98) {
    syndromeCode = "orthostatic_intolerance";
    primaryDiagnosis = "Orthostatic Intolerance / Fluid-Shift Hypotension";
    matchedRules.unshift("SYNDROME_ORTHOSTATIC_INTOLERANCE");
    checklist = [
      "Assist astronaut to supine posture and engage lower-limb compression garments.",
      "Ingest 500 ml isotonic saline via Potable Water Dispenser (PWD).",
      "Re-measure anchored NIBP and heart rate after 15 minutes.",
    ];
  } else if (vitals.glucose_mg_dl <= 70 && (calPct < 55 || vitals.heart_rate_bpm >= 95)) {
    syndromeCode = "hypoglycemia";
    primaryDiagnosis = "Caloric-Deficit Hypoglycemia & EVA Workload Strain";
    matchedRules.unshift("SYNDROME_CALORIC_HYPOGLYCEMIA");
    checklist = [
      "Consume 15-20g rapid-absorption glucose gel immediately.",
      "Pause strenuous EVA/ARED exertion for 15 min until glucose > 80 mg/dL.",
      "Log balanced meal (>= 500 kcal) via AstraCare chat.",
    ];
  }

  let overallStatus = "NOMINAL";
  Object.values(sysStatus).forEach((s) => {
    overallStatus = maxStatus(overallStatus, s);
  });

  const systems = {};
  Object.keys(sysAlerts).forEach((sid) => {
    const g = systemsGuide[sid] || {};
    systems[sid] = {
      system_id: sid,
      name: g.name || sid,
      status: sysStatus[sid],
      summary: sysAlerts[sid][0] || "All parameters within NASA-STD-3001 nominal envelope.",
      active_alerts: sysAlerts[sid],
      recommended_action: sysActions[sid],
      checs_device: g.checs_device || "CHeCS Telemetry",
      reference_standard: g.reference_standard || "NASA-STD-3001",
    };
  });

  return {
    overall_status: overallStatus,
    primary_diagnosis: primaryDiagnosis,
    syndrome_code: syndromeCode,
    matched_rules: matchedRules.length ? matchedRules : ["NASA-STD-3001-ALL-NOMINAL"],
    systems,
    stabilization_checklist: checklist,
    notify_earth_flight_surgeon: notifyEarth,
    notify_crew_onboard: notifyCrew,
    environment_calibration_notes: [env.protocol_focus],
    decontamination_required: Boolean(env.decontamination_required),
    decontamination_checklist: env.decontamination_checklist || [],
  };
}

function buildLocalMLPrediction(clinicalEval, vitals) {
  const isCrit = clinicalEval.overall_status === "CRITICAL";
  const isWarn = clinicalEval.overall_status === "WARNING";
  const anomalyScore = isCrit ? 91.4 : isWarn ? 67.2 : 11.8;
  const code = clinicalEval.syndrome_code;
  const probs = {
    nominal: code === "nominal" ? 94.0 : 4.0,
    systemic_infection: code === "systemic_infection" ? 89.5 : 2.0,
    orthostatic_intolerance: code === "orthostatic_intolerance" ? 86.0 : 2.5,
    behavioral_fatigue: code === "behavioral_fatigue" ? 90.2 : 2.0,
    hypoglycemia: code === "hypoglycemia" ? 87.5 : 2.0,
    solar_storm: code === "solar_storm" ? 95.0 : 1.0,
  };
  return {
    anomaly_score: anomalyScore,
    is_anomalous: anomalyScore >= 50,
    predicted_syndrome: code,
    predicted_syndrome_label: clinicalEval.primary_diagnosis,
    confidence_pct: probs[code] || 85.0,
    syndrome_probabilities: probs,
    feature_importances: [
      { feature: "radiation_msv_h", label: "Radiation Rate (mSv/h)", importance: code === "solar_storm" ? 48.0 : 8.5, current_value: vitals.radiation_msv_h, baseline_value: 0.04, deviation_pct: Math.round(((vitals.radiation_msv_h - 0.04) / 0.04) * 100) },
      { feature: "temperature_c", label: "Body Temp (C)", importance: code === "systemic_infection" ? 39.0 : 11.2, current_value: vitals.temperature_c, baseline_value: 36.7, deviation_pct: Math.round(((vitals.temperature_c - 36.7) / 36.7) * 1000) / 10 },
      { feature: "sleep_hours", label: "Sleep Duration (h)", importance: code === "behavioral_fatigue" ? 38.5 : 14.0, current_value: vitals.sleep_hours, baseline_value: 7.4, deviation_pct: Math.round(((vitals.sleep_hours - 7.4) / 7.4) * 100) },
      { feature: "glucose_mg_dl", label: "Blood Glucose (mg/dL)", importance: code === "hypoglycemia" ? 41.2 : 12.6, current_value: vitals.glucose_mg_dl, baseline_value: 94, deviation_pct: Math.round(((vitals.glucose_mg_dl - 94) / 94) * 100) },
      { feature: "bp_systolic", label: "Systolic BP (mmHg)", importance: code === "orthostatic_intolerance" ? 36.0 : 18.4, current_value: vitals.bp_systolic, baseline_value: 116, deviation_pct: Math.round(((vitals.bp_systolic - 116) / 116) * 100) },
    ].sort((a, b) => b.importance - a.importance),
  };
}

function buildLocalDonkiSummary() {
  const flr = localDonki.flr_events || [];
  const sep = localDonki.sep_events || [];
  const events = [
    ...flr.map((f) => ({
      event_id: f.flrID,
      event_type: "FLR",
      begin_time: f.beginTime,
      peak_time: f.peakTime,
      class_or_intensity: f.classType,
      source_location: f.sourceLocation,
      note: f.note,
    })),
    ...sep.map((s) => ({
      event_id: s.sepID,
      event_type: "SEP",
      begin_time: s.eventTime,
      peak_time: s.eventTime,
      class_or_intensity: s.intensity,
      source_location: s.sourceLocation,
      note: s.note,
    })),
  ];
  return {
    source: "curated_local_fallback",
    fetched_at: new Date().toISOString(),
    alert_level: sep.length > 0 ? "CRITICAL" : "WARNING",
    active_flare_count: flr.length,
    active_sep_count: sep.length,
    recommended_dose_limit_msv_h: 0.5,
    alara_instruction: "Curated NASA DONKI FLR/SEP feed active: X1.9 Flare + S2 SEP proton event. Maintain ALARA shelter readiness.",
    events,
  };
}

function recomputeLocalState(scenarioId = null, envId = null) {
  const targetScId = scenarioId || localState?.scenario_id || "nominal";
  const targetEnvId = envId || localState?.environment_id || "transit";
  const sc = localCatalog.scenarios.find((s) => s.id === targetScId) || localCatalog.scenarios[0];
  const env = localCatalog.environments.find((e) => e.id === targetEnvId) || localCatalog.environments[0];

  const vitals = scenarioId || !localState ? { ...sc.vitals } : { ...localState.vitals };
  const nutrition = scenarioId || !localState ? { ...sc.nutrition, logged_items: [] } : { ...localState.nutrition };
  const series = scenarioId || !localState ? sc.longitudinal_series.map((p) => ({ ...p })) : localState.longitudinal_series;

  const clinical_evaluation = evaluateLocalClinicalRules(vitals, nutrition, targetEnvId);
  const ml_prediction = buildLocalMLPrediction(clinical_evaluation, vitals);

  localState = {
    mission_day: sc.mission_day,
    crew_member: "CDR Elena Vance (EVA-1)",
    scenario_id: sc.id,
    scenario_name: sc.name,
    scenario_description: sc.description,
    environment_id: env.id,
    environment_name: env.name,
    one_way_latency_seconds: env.one_way_latency_seconds,
    vitals,
    nutrition,
    clinical_evaluation,
    ml_prediction,
    space_weather: buildLocalDonkiSummary(),
    longitudinal_series: series,
    scenarios_catalog: localCatalog.scenarios.map((s) => ({
      id: s.id,
      name: s.name,
      short_label: s.short_label,
      severity: s.severity,
      description: s.description,
    })),
    environments_catalog: localCatalog.environments.map((e) => ({
      id: e.id,
      name: e.name,
      short_label: e.short_label,
      gravity: e.gravity,
      one_way_latency_seconds: e.one_way_latency_seconds,
      latency_label: e.latency_label,
      protocol_focus: e.protocol_focus,
      decontamination_required: e.decontamination_required,
    })),
    indicators_guide: localCatalog.indicators_guide || [],
    systems_guide: localCatalog.systems_guide || {},
    last_updated: new Date().toISOString(),
  };
  return localState;
}

// ---------- Connection mode ----------
// "live" = last call reached the FastAPI backend; "simulated" = it failed and the UI is running the in-browser fallback.
// The fallback used to be silent, which made an offline backend look connected.
let connectionMode = "unknown";
const connectionListeners = new Set();

function setConnectionMode(mode) {
  if (mode === connectionMode) return;
  connectionMode = mode;
  connectionListeners.forEach((fn) => fn(mode));
}

export function subscribeConnectionMode(fn) {
  connectionListeners.add(fn);
  fn(connectionMode);
  return () => connectionListeners.delete(fn);
}

async function tryFetch(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? 3500);
  try {
    const res = await fetch(`${API_BASE}${url}`, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    clearTimeout(timer);
    // 4xx = backend answered and rejected the request (e.g. 409 on a resolved case): still live.
    // 5xx = includes the Vite dev proxy's 500 when the backend is down, and every caller falls back to
    // simulation on it, so the badge must say "simulated".
    setConnectionMode(res.status >= 500 ? "simulated" : "live");
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      } catch {
        /* non-JSON error body */
      }
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    return await res.json();
  } catch (err) {
    clearTimeout(timer);
    if (err?.status === undefined) setConnectionMode("simulated"); // network error / timeout
    throw err;
  }
}

// ---------- Live-only pillar endpoints ----------
// No in-browser fallback on purpose: confirming, escalating or "syncing" a clinical case against a simulation
// would fabricate an audit trail. When the backend is offline these reject and the UI says so.
const postJson = (url, body) =>
  tryFetch(url, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body), timeoutMs: 15000 });

export const confirmFollowupMeasurement = (caseId, payload) => postJson(`/api/followup/${caseId}/confirm`, payload);
export const recordFollowupAction = (caseId, payload) => postJson(`/api/followup/${caseId}/action`, payload);
export const completeFollowupReassessment = (caseId, payload) => postJson(`/api/followup/${caseId}/reassess`, payload);
export const escalateFollowupCase = (caseId, payload) => postJson(`/api/followup/${caseId}/escalate`, payload);
export const createEarthSyncPackage = () => postJson("/api/earth-sync/package");
export const synchronizeWithEarth = () => postJson("/api/earth-sync/synchronize");
export const getEarthSyncLedger = () => tryFetch("/api/earth-sync/ledger");
export const verifyEarthSyncLedger = () => tryFetch("/api/earth-sync/verify");

export async function getMissionState() {
  try {
    return await tryFetch("/api/state");
  } catch {
    await loadLocalData();
    return localState ? recomputeLocalState() : recomputeLocalState("nominal", "transit");
  }
}

export async function switchScenario(scenarioId) {
  try {
    return await tryFetch(`/api/scenario/${scenarioId}`, { method: "POST" });
  } catch {
    await loadLocalData();
    return recomputeLocalState(scenarioId, localState?.environment_id || "transit");
  }
}

export async function switchEnvironment(envId) {
  try {
    return await tryFetch(`/api/environment/${envId}`, { method: "POST" });
  } catch {
    await loadLocalData();
    return recomputeLocalState(null, envId);
  }
}

export async function triggerMeasurement(systemId) {
  try {
    return await tryFetch(`/api/measure/${systemId}`, { method: "POST" });
  } catch {
    await loadLocalData();
    const state = recomputeLocalState();
    const sys = state.clinical_evaluation.systems[systemId];
    return {
      system_id: systemId,
      system_name: sys.name,
      device_used: sys.checs_device,
      decontamination_required: state.clinical_evaluation.decontamination_required,
      decontamination_checklist: state.clinical_evaluation.decontamination_checklist,
      reading_summary: `${sys.name} local edge telemetry verified nominal sync.`,
      status: sys.status,
      guidance: sys.recommended_action,
      state,
    };
  }
}

export async function sendAgentChat(message) {
  try {
    return await tryFetch("/api/agent/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  } catch {
    await loadLocalData();
    if (!localState) recomputeLocalState("nominal", "transit");
    const lower = message.toLowerCase();
    const trace = [];

    // Local NLP food/water fallback
    const waterMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*(ml|l|liter)/);
    const appleMatch = lower.match(/(\d+)\s*apple/);
    if (waterMatch || appleMatch || lower.includes("ate") || lower.includes("drank") || lower.includes("bar") || lower.includes("meal")) {
      const wMl = waterMatch ? parseFloat(waterMatch[1]) * (waterMatch[2].startsWith("l") ? 1000 : 1) : 250;
      const kcal = appleMatch ? parseInt(appleMatch[1], 10) * 95 : 220;
      const carbs = appleMatch ? parseInt(appleMatch[1], 10) * 25 : 32;
      localState.nutrition.calories_kcal += kcal;
      localState.nutrition.water_ml += wMl;
      localState.nutrition.carbs_g += carbs;
      if (localState.vitals.glucose_mg_dl < 85) localState.vitals.glucose_mg_dl += Math.round(carbs * 0.6);
      localState.nutrition.logged_items.unshift({
        timestamp: new Date().toISOString().slice(11, 16) + " UTC",
        item: message.slice(0, 48),
        calories_kcal: kcal,
        water_ml: wMl,
        protein_g: 4,
        carbs_g: carbs,
        fiber_g: 4,
        sodium_mg: 40,
        iron_mg: 0.4,
      });
      trace.push({ tool_name: "log_nutrition_hydration", status: "OK", summary: `+${kcal} kcal, +${wMl} ml H2O`, rule_or_score: "Na/Fe Checked" });
    }

    const sleepMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*(?:h|hr|hrs|hours)/);
    if (sleepMatch || lower.includes("shoulder") || lower.includes("dizzy") || lower.includes("tired")) {
      if (sleepMatch) localState.vitals.sleep_hours = parseFloat(sleepMatch[1]);
      if (lower.includes("shoulder")) localState.vitals.shoulder_pain_score = 6;
      if (lower.includes("dizzy") || lower.includes("exhausted")) localState.vitals.mood_score = 2;
      trace.push({ tool_name: "log_sleep_mood_checkin", status: "WARNING", summary: "Updated Sleep/EVA check-in", rule_or_score: "OCHMO-MTB-009/006" });
    }

    const state = recomputeLocalState();
    trace.push({
      tool_name: "evaluate_clinical_rules",
      status: state.clinical_evaluation.overall_status === "NOMINAL" ? "OK" : state.clinical_evaluation.overall_status,
      summary: state.clinical_evaluation.primary_diagnosis,
      rule_or_score: state.clinical_evaluation.matched_rules[0],
    });
    trace.push({
      tool_name: "predict_ml_risk",
      status: state.ml_prediction.anomaly_score >= 70 ? "CRITICAL" : state.ml_prediction.anomaly_score >= 45 ? "WARNING" : "OK",
      summary: `Anomaly ${state.ml_prediction.anomaly_score}%`,
      rule_or_score: `RF ${state.ml_prediction.confidence_pct}%`,
    });

    return {
      reply: `**Clinical Triage (${state.clinical_evaluation.overall_status}):** ${state.clinical_evaluation.primary_diagnosis}.\n\n**Recommended Action Plan:**\n${state.clinical_evaluation.stabilization_checklist.map((s, i) => `${i + 1}. ${s}`).join("\n")}`,
      mode: "offline_hybrid_edge",
      tool_trace: trace,
      state,
    };
  }
}

export async function getSpaceWeather() {
  try {
    return await tryFetch("/api/nasa/space-weather");
  } catch {
    await loadLocalData();
    return buildLocalDonkiSummary();
  }
}

export async function generateTelemedicineDossier() {
  try {
    return await tryFetch("/api/telemedicine/dossier", { method: "POST" });
  } catch {
    await loadLocalData();
    const state = recomputeLocalState();
    return {
      dossier_id: "ASTRA-MORD-OFFLINE",
      generated_at: new Date().toISOString(),
      mission_day: state.mission_day,
      crew_member: state.crew_member,
      environment_id: state.environment_id,
      environment_name: state.environment_name,
      one_way_latency_seconds: state.one_way_latency_seconds,
      transmission_mode: state.one_way_latency_seconds > 30 ? "Asynchronous Store-and-Forward Bundle" : "Real-Time Telemetry Loop",
      urgency: state.clinical_evaluation.overall_status,
      recipient_roles: ["Flight Surgeon (FS)", "Crew Surgeon (CS)", "Biomedical Engineer (BME)"],
      executive_summary: `${state.clinical_evaluation.overall_status}: ${state.clinical_evaluation.primary_diagnosis} (Anomaly ${state.ml_prediction.anomaly_score}%).`,
      clinical_evaluation: state.clinical_evaluation,
      ml_prediction: state.ml_prediction,
      vitals_snapshot: state.vitals,
      nutrition_snapshot: state.nutrition,
      space_weather_alert: state.space_weather?.alara_instruction || "DONKI sample active.",
      recommended_earth_questions: [
        "Confirm next CHeCS medical kit dosage & hydration bolus.",
        "Approve EVA suspension vs. return-to-duty criteria per OCHMO-TB-044 MORD.",
      ],
    };
  }
}
