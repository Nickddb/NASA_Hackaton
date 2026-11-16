// AstraCare AI Frontend API Client with Automatic Offline Multi-Crew Fallback
// Calls FastAPI backend (/api/*) when live; falls back seamlessly to in-browser NASA-STD-3001 + personal baseline evaluation using /data/scenarios.json if offline.
import { T, bpStatus, glucoseStatus, hrStatus, radiationStatus, sleepStatus, tempStatus } from "./thresholds";

let localCatalog = null;
let localDonki = null;
let localCrewStore = null;
let localActiveCrewId = "elena_vance";
let localState = null;
let lastLiveState = null;
const crewAlertOverlay = {};

const BACKEND_ASTRONAUT_IDS = new Set([
  "elena_vance",
  "lucas_ferreira",
  "kenji_sato",
  "amara_okafor",
  "liam_soren",
]);

const API_BASE = import.meta.env?.VITE_API_BASE || "";

const LOCAL_CREW_SPECS = [
  {
    crew_id: "elena_vance",
    name: "CDR Elena Vance (EVA-1)",
    callsign: "EVA-1",
    role: "Mission Commander & Lead EVA Specialist",
    mission_group: "EVA",
    location_module: "ISS Quest Airlock (EVA)",
    environment_id: "orbital_station",
    initial_scenario_id: "nominal",
    suit_variant: "MERCURY_EVA_SILVER",
    suit_accent: "#38BDF8",
    baseline: {
      resting_hr_bpm: 61, hr_min: 48, hr_max: 76,
      resting_bp_systolic: 112, resting_bp_diastolic: 71, bp_sys_min: 96, bp_sys_max: 128,
      resting_temp_c: 36.6, temp_min: 36.0, temp_max: 37.3,
      resting_spo2_pct: 98.8, spo2_min: 95.0,
      resting_glucose_mg_dl: 90, glucose_min: 72, glucose_max: 122,
      resting_sleep_hours: 7.6, sleep_min: 6.5,
      resting_hrv_ms: 64, hrv_min: 46, radiation_max: 0.14,
    },
  },
  {
    crew_id: "lucas_ferreira",
    name: "MS-1 Lucas Ferreira (AEB/Payload)",
    callsign: "PYL-1",
    role: "Mission Specialist & Biomedical Payload Officer",
    mission_group: "ISS",
    location_module: "ISS Columbus Bio-Lab",
    environment_id: "orbital_station",
    initial_scenario_id: "hypoglycemia",
    suit_variant: "MERCURY_EVA_GOLD",
    suit_accent: "#F59E0B",
    baseline: {
      resting_hr_bpm: 74, hr_min: 59, hr_max: 89,
      resting_bp_systolic: 121, resting_bp_diastolic: 78, bp_sys_min: 104.5, bp_sys_max: 137.5,
      resting_temp_c: 36.8, temp_min: 36.2, temp_max: 37.4,
      resting_spo2_pct: 98.2, spo2_min: 95.0,
      resting_glucose_mg_dl: 96, glucose_min: 78, glucose_max: 128,
      resting_sleep_hours: 7.1, sleep_min: 6.0,
      resting_hrv_ms: 49, hrv_min: 31, radiation_max: 0.14,
    },
  },
  {
    crew_id: "kenji_sato",
    name: "PLT Kenji Sato (Flight Eng)",
    callsign: "PLT-1",
    role: "Spacecraft Pilot & Systems Engineer",
    mission_group: "DEEP_SPACE",
    location_module: "Orion Flight Deck",
    environment_id: "transit",
    initial_scenario_id: "nominal",
    suit_variant: "MERCURY_IVA_SLATE",
    suit_accent: "#34D399",
    baseline: {
      resting_hr_bpm: 66, hr_min: 52.5, hr_max: 80,
      resting_bp_systolic: 117, resting_bp_diastolic: 75, bp_sys_min: 101.4, bp_sys_max: 132.6,
      resting_temp_c: 36.6, temp_min: 36.0, temp_max: 37.3,
      resting_spo2_pct: 98.5, spo2_min: 95.0,
      resting_glucose_mg_dl: 92, glucose_min: 74, glucose_max: 124,
      resting_sleep_hours: 7.3, sleep_min: 6.2,
      resting_hrv_ms: 56, hrv_min: 38, radiation_max: 0.14,
    },
  },
  {
    crew_id: "amara_okafor",
    name: "CMO Amara Okafor",
    callsign: "MED-2",
    role: "Crew Medical Officer",
    mission_group: "ISS",
    location_module: "ISS Harmony Medical Bay",
    environment_id: "orbital_station",
    initial_scenario_id: "nominal",
    suit_variant: "MERCURY_EVA_CYAN",
    suit_accent: "#22D3EE",
    baseline: {
      resting_hr_bpm: 64, hr_min: 51, hr_max: 78,
      resting_bp_systolic: 114, resting_bp_diastolic: 72, bp_sys_min: 98, bp_sys_max: 130,
      resting_temp_c: 36.6, temp_min: 36.0, temp_max: 37.3,
      resting_spo2_pct: 98.7, spo2_min: 95.0,
      resting_glucose_mg_dl: 91, glucose_min: 73, glucose_max: 123,
      resting_sleep_hours: 7.4, sleep_min: 6.3,
      resting_hrv_ms: 61, hrv_min: 43, radiation_max: 0.14,
    },
  },
  {
    crew_id: "liam_soren",
    name: "EXP-2 Liam Soren",
    callsign: "ORB-4",
    role: "Deep Space Habitat Specialist",
    mission_group: "DEEP_SPACE",
    location_module: "Orion Habitation Ring",
    environment_id: "transit",
    initial_scenario_id: "systemic_infection",
    suit_variant: "MERCURY_TRANSIT_COBALT",
    suit_accent: "#EF4444",
    baseline: {
      resting_hr_bpm: 69, hr_min: 54.6, hr_max: 83.4,
      resting_bp_systolic: 118, resting_bp_diastolic: 76, bp_sys_min: 102, bp_sys_max: 134,
      resting_temp_c: 36.7, temp_min: 36.1, temp_max: 37.3,
      resting_spo2_pct: 98.3, spo2_min: 95.0,
      resting_glucose_mg_dl: 95, glucose_min: 77, glucose_max: 127,
      resting_sleep_hours: 7.5, sleep_min: 6.4,
      resting_hrv_ms: 54, hrv_min: 36, radiation_max: 0.14,
    },
  },
];

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

const DEFAULT_PERSONAL_BASELINE = {
  hr_min: 52,
  hr_max: 88,
  bp_sys_min: 98,
  bp_sys_max: 132,
  temp_min: 36.1,
  temp_max: 37.3,
  spo2_min: 95.0,
  glucose_min: 72,
  glucose_max: 140,
  sleep_min: T.SLEEP_WARN_H,
  hrv_min: 35,
  radiation_max: 0.25,
};

function asApiStatus(st) {
  return st === "NORMAL" ? "NOMINAL" : st;
}

function evaluateBaselineAndMetricStatuses(vitals, baseline) {
  const pb = baseline || DEFAULT_PERSONAL_BASELINE;
  const statuses = {
    hr: "NOMINAL",
    bp: "NOMINAL",
    temp: "NOMINAL",
    spo2: "NOMINAL",
    rr: "NOMINAL",
    glucose: "NOMINAL",
    sleep: "NOMINAL",
    hrv: "NOMINAL",
    radiation: "NOMINAL",
  };
  let status = "NOMINAL";
  const deviations = [];
  if (!vitals) {
    return { status, deviations, statuses };
  }

  const bump = (key, sev) => {
    statuses[key] = maxStatus(statuses[key], sev);
    status = maxStatus(status, sev);
  };

  if (vitals.heart_rate_bpm < pb.hr_min || vitals.heart_rate_bpm > pb.hr_max) {
    const severe = vitals.heart_rate_bpm >= pb.hr_max + 24 || vitals.heart_rate_bpm <= pb.hr_min - 12;
    bump("hr", severe ? "CRITICAL" : "WARNING");
    deviations.push(`HR ${Math.round(vitals.heart_rate_bpm)} bpm (personal normal ${pb.hr_min}-${pb.hr_max})`);
  }
  statuses.hr = maxStatus(statuses.hr, asApiStatus(hrStatus(vitals.heart_rate_bpm)));

  const dia = vitals.bp_diastolic ?? 75;
  if (vitals.bp_systolic < pb.bp_sys_min || vitals.bp_systolic > pb.bp_sys_max || dia >= 92 || dia <= 55) {
    const severe =
      vitals.bp_systolic <= pb.bp_sys_min - 14 ||
      vitals.bp_systolic >= pb.bp_sys_max + 20 ||
      dia >= 102 ||
      dia <= 52;
    bump("bp", severe ? "CRITICAL" : "WARNING");
    deviations.push(`BP ${Math.round(vitals.bp_systolic)}/${Math.round(dia)} mmHg (personal sys ${pb.bp_sys_min}-${pb.bp_sys_max})`);
  }
  statuses.bp = maxStatus(statuses.bp, asApiStatus(bpStatus(vitals.bp_systolic)));
  if (dia >= 105) {
    statuses.bp = maxStatus(statuses.bp, "CRITICAL");
  } else if (dia >= 90) {
    statuses.bp = maxStatus(statuses.bp, "WARNING");
  }

  if (vitals.temperature_c < pb.temp_min || vitals.temperature_c > pb.temp_max) {
    const severe = vitals.temperature_c >= pb.temp_max + 0.8 || vitals.temperature_c <= pb.temp_min - 0.8;
    bump("temp", severe ? "CRITICAL" : "WARNING");
    deviations.push(`Temp ${vitals.temperature_c.toFixed(1)}°C (personal ${pb.temp_min.toFixed(1)}-${pb.temp_max.toFixed(1)}°C)`);
  }
  statuses.temp = maxStatus(statuses.temp, asApiStatus(tempStatus(vitals.temperature_c)));

  if (vitals.spo2_pct < pb.spo2_min) {
    const severe = vitals.spo2_pct < pb.spo2_min - 2.0;
    bump("spo2", severe ? "CRITICAL" : "WARNING");
    deviations.push(`SpO2 ${vitals.spo2_pct.toFixed(1)}% (personal >= ${pb.spo2_min.toFixed(1)}%)`);
  }
  if (vitals.spo2_pct < 93.0) {
    statuses.spo2 = maxStatus(statuses.spo2, "CRITICAL");
  } else if (vitals.spo2_pct < 95.0) {
    statuses.spo2 = maxStatus(statuses.spo2, "WARNING");
  }

  const rr = vitals.respiration_rpm ?? 15;
  if (rr >= 24 || rr <= 8) {
    statuses.rr = "CRITICAL";
  } else if (rr >= 20 || rr <= 10) {
    statuses.rr = "WARNING";
  }

  if (vitals.glucose_mg_dl < pb.glucose_min || vitals.glucose_mg_dl > pb.glucose_max) {
    const severe = vitals.glucose_mg_dl < pb.glucose_min - 18 || vitals.glucose_mg_dl > pb.glucose_max + 45;
    bump("glucose", severe ? "CRITICAL" : "WARNING");
    deviations.push(`Glucose ${Math.round(vitals.glucose_mg_dl)} mg/dL (personal ${pb.glucose_min}-${pb.glucose_max})`);
  }
  statuses.glucose = maxStatus(statuses.glucose, asApiStatus(glucoseStatus(vitals.glucose_mg_dl)));

  // In-flight nominal sleep averages ~5.8-6.0 h (NASA SSM / nasa_calibration.py); warn below T.SLEEP_WARN_H (5.0 h)
  const inFlightSleepMin = Math.min(pb.sleep_min ?? T.SLEEP_WARN_H, T.SLEEP_WARN_H);
  const lowNights = vitals.sleep_streak_low_days || 0;
  if (vitals.sleep_hours < inFlightSleepMin || lowNights >= T.SLEEP_CRIT_NIGHTS) {
    const severe = vitals.sleep_hours < T.SLEEP_CRIT_H || lowNights >= T.SLEEP_CRIT_NIGHTS;
    bump("sleep", severe ? "CRITICAL" : "WARNING");
    deviations.push(`Sleep ${vitals.sleep_hours.toFixed(1)}h (in-flight >= ${inFlightSleepMin.toFixed(1)}h)`);
  }
  statuses.sleep = maxStatus(statuses.sleep, asApiStatus(sleepStatus(vitals.sleep_hours, lowNights)));

  if (vitals.hrv_ms < pb.hrv_min) {
    const severe = vitals.hrv_ms <= pb.hrv_min - 15 || vitals.hrv_ms <= 24;
    bump("hrv", severe ? "CRITICAL" : "WARNING");
    deviations.push(`HRV ${Math.round(vitals.hrv_ms)} ms (personal >= ${pb.hrv_min} ms)`);
  }

  if (vitals.radiation_msv_h > pb.radiation_max) {
    const severe = vitals.radiation_msv_h > T.RAD_CRIT_MSV_H;
    bump("radiation", severe ? "CRITICAL" : "WARNING");
    deviations.push(`Radiation ${vitals.radiation_msv_h.toFixed(2)} mSv/h (personal <= ${pb.radiation_max.toFixed(2)})`);
  }
  statuses.radiation = maxStatus(statuses.radiation, asApiStatus(radiationStatus(vitals.radiation_msv_h)));

  return { status, deviations, statuses };
}

export function getVitalStatuses(vitals, baseline) {
  return evaluateBaselineAndMetricStatuses(vitals, baseline).statuses;
}

const DEFAULT_ENV_CONTEXT = {
  cabin_co2_mmhg: 2.5,
  cabin_o2_pct: 20.9,
  cabin_pressure_psia: 14.7,
  cabin_temp_c: 22.1,
  cabin_humidity_pct: 44.0,
  gravitational_g: 0.0,
  eva_status: "none",
};

const ENV_CONTEXT_PRESETS = {
  orbital_station: {
    cabin_co2_mmhg: 2.4,
    cabin_o2_pct: 20.9,
    cabin_pressure_psia: 14.7,
    cabin_temp_c: 22.1,
    cabin_humidity_pct: 44.0,
    gravitational_g: 0.0,
    eva_status: "none",
  },
  transit: {
    cabin_co2_mmhg: 2.7,
    cabin_o2_pct: 20.8,
    cabin_pressure_psia: 14.7,
    cabin_temp_c: 21.8,
    cabin_humidity_pct: 43.0,
    gravitational_g: 0.0,
    eva_status: "none",
  },
  planetary_surface: {
    cabin_co2_mmhg: 3.1,
    cabin_o2_pct: 24.5,
    cabin_pressure_psia: 10.2,
    cabin_temp_c: 20.5,
    cabin_humidity_pct: 38.0,
    gravitational_g: 0.38,
    eva_status: "pre_eva_prebreathe",
  },
};

const SCENARIO_CONTEXT_OVERRIDES = {
  systemic_infection: { cabin_co2_mmhg: 4.1, cabin_temp_c: 24.4 },
  eva_decompression_shoulder: { cabin_pressure_psia: 10.2, cabin_o2_pct: 26.5, cabin_co2_mmhg: 2.9, eva_status: "pre_eva_prebreathe" },
  combined_co2_circadian: { cabin_co2_mmhg: 4.6, cabin_temp_c: 23.8 },
  hypoglycemia: {},
  solar_particle_event: { cabin_co2_mmhg: 3.0 },
};

function buildLocalMissionContext(envId, scenario) {
  const baseEnv = ENV_CONTEXT_PRESETS[envId] || DEFAULT_ENV_CONTEXT;
  const scCtx = scenario?.mission_context || {};
  const scOverride = SCENARIO_CONTEXT_OVERRIDES[scenario?.id] || {};
  return {
    ...DEFAULT_ENV_CONTEXT,
    ...baseEnv,
    ...scCtx,
    ...scOverride,
  };
}

export function getEnvironmentStatuses(missionContext, vitals, baseline) {
  const ctx = missionContext || DEFAULT_ENV_CONTEXT;
  const co2 = ctx.cabin_co2_mmhg ?? 2.5;
  const o2 = ctx.cabin_o2_pct ?? 20.9;
  const press = ctx.cabin_pressure_psia ?? 14.7;
  const temp = ctx.cabin_temp_c ?? 22.1;
  const hum = ctx.cabin_humidity_pct ?? 44.0;
  const rad = vitals?.radiation_msv_h ?? 0.04;
  const radMax = baseline?.radiation_max ?? 0.14;

  const co2Status = co2 >= 5.0 ? "CRITICAL" : co2 >= 3.8 ? "WARNING" : "NOMINAL";
  const o2Status = o2 < 18.0 || o2 > 28.0 ? "CRITICAL" : o2 < 19.5 || o2 > 23.5 ? "WARNING" : "NOMINAL";
  const pressStatus = press < 8.5 || press > 16.0 ? "CRITICAL" : press < 13.5 || press > 15.2 ? "WARNING" : "NOMINAL";
  const radStatus = rad >= T.RAD_CRIT_MSV_H ? "CRITICAL" : rad > radMax ? "WARNING" : "NOMINAL";
  const climateStatus =
    temp < 15.0 || temp > 30.0 || hum < 20.0 || hum > 75.0
      ? "CRITICAL"
      : temp < 18.0 || temp > 26.0 || hum < 30.0 || hum > 65.0
        ? "WARNING"
        : "NOMINAL";

  const sensors = {
    co2: {
      key: "co2",
      label: "Cabin CO₂",
      shortLabel: "CO₂",
      value: Number(co2.toFixed(1)),
      unit: "mmHg",
      display: `${co2.toFixed(1)}`,
      shortValue: `${co2.toFixed(1)}`,
      range: "≤ 3.8 mmHg",
      status: co2Status,
    },
    o2: {
      key: "o2",
      label: "Cabin O₂",
      shortLabel: "O₂",
      value: Number(o2.toFixed(1)),
      unit: "%",
      display: `${o2.toFixed(1)}`,
      shortValue: `${o2.toFixed(1)}%`,
      range: "19.5–23.5%",
      status: o2Status,
    },
    pressure: {
      key: "pressure",
      label: "Cabin Pressure",
      shortLabel: "Press",
      value: Number(press.toFixed(1)),
      unit: "psia",
      display: `${press.toFixed(1)}`,
      shortValue: `${press.toFixed(1)}p`,
      range: "13.5–15.2 psia",
      status: pressStatus,
    },
    radiation: {
      key: "radiation",
      label: "Radiation Dose",
      shortLabel: "Rad",
      value: Number(rad.toFixed(2)),
      unit: "mSv/h",
      display: `${rad.toFixed(2)}`,
      shortValue: `${rad.toFixed(2)}`,
      range: `≤ ${radMax.toFixed(2)} mSv/h`,
      status: radStatus,
    },
    climate: {
      key: "climate",
      label: "Cabin Temp / RH",
      shortLabel: "Temp/RH",
      value: Number(temp.toFixed(1)),
      unit: "°C",
      display: `${temp.toFixed(1)}° • ${Math.round(hum)}%`,
      shortValue: `${temp.toFixed(0)}°/${Math.round(hum)}%`,
      range: "18–26°C • 30–65%",
      status: climateStatus,
    },
  };

  const list = [sensors.co2, sensors.o2, sensors.pressure, sensors.radiation, sensors.climate];
  const overall = list.reduce((acc, s) => maxStatus(acc, s.status), "NOMINAL");
  return { overall, sensors, list };
}

const ENV_LATENCY_DEFAULTS = {
  orbital_station: 2,
  transit: 720,
  planetary_surface: 380,
};

export function getPsychologicalReadiness(vitals, baseline, opts = {}) {
  const pb = baseline || DEFAULT_PERSONAL_BASELINE;
  const v = vitals || {};
  const mood = v.mood_score ?? 5;
  const stress = v.stress_index ?? 22;
  const hrv = v.hrv_ms ?? pb.resting_hrv_ms ?? 55;
  const hrvMin = pb.hrv_min ?? 35;
  const sleep = v.sleep_hours ?? 7.2;
  const sleepMin = Math.min(pb.sleep_min ?? T.SLEEP_WARN_H, T.SLEEP_WARN_H);
  const sleepStreak = v.sleep_streak_low_days ?? 0;
  const latencySec =
    opts.oneWayLatencySeconds ??
    ENV_LATENCY_DEFAULTS[opts.environmentId] ??
    2;

  const moodPenaltyMap = { 5: 0, 4: 8, 3: 22, 2: 40, 1: 55 };
  const moodPts = moodPenaltyMap[Math.min(5, Math.max(1, Math.round(mood)))] ?? 22;
  const stressPts = Math.max(0, (stress - 25) * 0.44);
  const hrvPts = hrv < hrvMin ? Math.min(24, (hrvMin - hrv) * 0.95) : 0;
  const sleepPts =
    (sleep < sleepMin ? Math.min(20, (sleepMin - sleep) * 7.5) : 0) +
    Math.min(24, sleepStreak * 7.5);
  const latencyPts = latencySec >= 180 ? Math.min(10, (latencySec / 720) * 8) : 0;
  const somaticPts =
    ((v.temperature_c ?? 36.6) >= 38.0 ? 10 : 0) +
    ((v.shoulder_pain_score ?? 0) >= 4 ? 8 : 0);

  const computedStrain = Math.min(99, Math.max(0, Math.round(moodPts + stressPts + hrvPts + sleepPts + latencyPts + somaticPts)));
  const apiStrain = opts.psychEvaluation?.primary_score_0_100;
  const strainScore = apiStrain != null ? Math.round(Math.max(computedStrain, Math.min(99, apiStrain))) : computedStrain;
  const score = Math.max(0, Math.min(100, 100 - strainScore));

  let tier = "OPTIMAL";
  let label = "Optimal";
  let status = "NOMINAL";
  if (score <= 34) {
    tier = "CRITICAL_STRAIN";
    label = "Critical Strain";
    status = "CRITICAL";
  } else if (score <= 54) {
    tier = "HIGH_STRAIN";
    label = "High Strain";
    status = "WARNING";
  } else if (score <= 74) {
    tier = "CAUTION";
    label = "Caution";
    status = "WARNING";
  }

  const moodStatus = mood <= 2 ? "CRITICAL" : mood <= 3 ? "WARNING" : "NOMINAL";
  const stressStatus = stress >= 75 ? "CRITICAL" : stress >= 55 ? "WARNING" : "NOMINAL";
  const hrvStatus = hrv <= Math.max(24, hrvMin - 15) ? "CRITICAL" : hrv < hrvMin ? "WARNING" : "NOMINAL";
  const sleepStatus =
    sleepStreak >= T.SLEEP_CRIT_NIGHTS || sleep < T.SLEEP_CRIT_H
      ? "CRITICAL"
      : sleep < sleepMin
        ? "WARNING"
        : "NOMINAL";
  const delayStatus = latencySec >= 300 ? "WARNING" : "NOMINAL";

  const summary =
    opts.psychEvaluation?.primary_diagnosis_label ||
    (tier === "CRITICAL_STRAIN"
      ? "Acute psychophysiological overload — biofeedback decompression & CMO support recommended"
      : tier === "HIGH_STRAIN"
        ? "Elevated behavioral strain & autonomic load — schedule decompression protocol"
        : tier === "CAUTION"
          ? "Mild circadian or stress drift above personal baseline"
          : "Cognitive, affective, and autonomic markers stable within personal baseline");

  const factors = [
    { key: "mood", label: "Mood Index", display: `${Math.round(mood)}/5`, status: moodStatus },
    { key: "stress", label: "Autonomic Stress", display: `${Math.round(stress)}%`, status: stressStatus },
    { key: "hrv", label: "HRV Resilience", display: `${Math.round(hrv)} ms`, status: hrvStatus },
    { key: "sleep", label: "Sleep Reserve", display: `${sleep.toFixed(1)}h`, status: sleepStatus },
    {
      key: "latency",
      label: "Earth Delay",
      display: latencySec >= 60 ? `${Math.round(latencySec / 60)}m` : `${latencySec}s`,
      status: delayStatus,
    },
  ];

  return { score, strainScore, tier, label, status, summary, factors };
}
function evaluateLocalPersonalBaseline(vitals, baseline) {
  const { status, deviations } = evaluateBaselineAndMetricStatuses(vitals, baseline);
  return { status, deviations };
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
    sysStatus.respiratory = maxStatus(sysStatus.respiratory, vitals.spo2_pct < 94.0 ? "CRITICAL" : "WARNING");
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

// Offline fallback: same DONKI response schema as the backend sample (arrays per endpoint).
// Events count as active only inside the last 72 h, so the curated past-dated sample reads as nominal.
function buildLocalDonkiSummary() {
  const activeSince = Date.now() - 72 * 3600 * 1000;
  const pick = (kind, timeField, idField, intensity) =>
    (localDonki?.[kind] || []).map((e) => {
      const t = Date.parse(e[timeField]);
      return {
        event_id: e[idField],
        event_type: kind,
        begin_time: e[timeField],
        peak_time: e.peakTime || null,
        class_or_intensity: intensity(e),
        source_location: e.sourceLocation || "",
        note: e.note || `NASA DONKI ${kind} notification`,
        is_active: Number.isFinite(t) && t >= activeSince,
        origin: "nasa_donki",
      };
    });
  const inst = (e) => (e.instruments || []).map((i) => i.displayName).join(", ");
  const events = [
    ...pick("SEP", "eventTime", "sepID", (e) => inst(e) || "SEP"),
    ...pick("FLR", "beginTime", "flrID", (e) => e.classType || "Flare"),
    ...pick("RBE", "eventTime", "rbeID", (e) => inst(e) || "RBE"),
  ];
  const active = events.filter((e) => e.is_active);
  const sep = active.filter((e) => e.event_type === "SEP");
  const flr = active.filter((e) => e.event_type === "FLR");
  const rbe = active.filter((e) => e.event_type === "RBE");
  const mx = flr.filter((e) => /^[MX]/i.test(e.class_or_intensity));
  const alert = sep.length || flr.some((e) => /^X/i.test(e.class_or_intensity)) ? "CRITICAL" : mx.length || rbe.length ? "WARNING" : "NOMINAL";
  return {
    source: "curated_local_fallback",
    fetched_at: new Date().toISOString(),
    alert_level: alert,
    status_label: sep.length ? "SEP alert active" : mx.length ? `Class ${mx[0].class_or_intensity} flare detected` : rbe.length ? "Radiation belt enhancement active" : "Nominal",
    fetch_status: "backend offline -> browser copy of the curated DONKI sample",
    active_flare_count: flr.length,
    active_sep_count: sep.length,
    active_rbe_count: rbe.length,
    active_window_hours: 72,
    uses_demo_key: true,
    recommended_dose_limit_msv_h: 0.5,
    alara_instruction: "Offline: NASA DONKI unreachable from the browser fallback. Continue onboard dosimetry (ALARA).",
    events,
  };
}

function applyBaselineToVitals(vitals, baseline) {
  return {
    ...vitals,
    heart_rate_bpm: baseline.resting_hr_bpm,
    hrv_ms: baseline.resting_hrv_ms,
    bp_systolic: baseline.resting_bp_systolic,
    bp_diastolic: baseline.resting_bp_diastolic,
    temperature_c: baseline.resting_temp_c,
    spo2_pct: baseline.resting_spo2_pct,
    glucose_mg_dl: baseline.resting_glucose_mg_dl,
    sleep_hours: baseline.resting_sleep_hours,
  };
}

function syncLocalAlertFromTelemetry(rec) {
  const clinical = evaluateLocalClinicalRules(rec.vitals, rec.nutrition, rec.environment_id);
  const base = evaluateLocalPersonalBaseline(rec.vitals, rec.baseline);
  const computed = maxStatus(clinical.overall_status, base.status);
  if (computed === "NOMINAL") return;

  const msg =
    clinical.overall_status !== "NOMINAL"
      ? clinical.primary_diagnosis
      : `Personal baseline deviation: ${base.deviations.slice(0, 2).join("; ")}`;

  if (!rec.active_alert) {
    rec.active_alert = {
      alert_id: `ALT-${Math.random().toString(16).slice(2, 8).toUpperCase()}`,
      severity: computed,
      source: "CLINICAL_TELEMETRY",
      message: msg,
      issued_at: new Date().toISOString(),
      issued_by: "AstraCare Auto-Triage",
      acknowledged_by_crew: false,
      requires_recheck: true,
    };
  } else {
    rec.active_alert.severity = maxStatus(rec.active_alert.severity, computed);
    if (rec.active_alert.source === "CLINICAL_TELEMETRY") {
      rec.active_alert.message = msg;
    }
  }
}

function ensureLocalCrewStore() {
  if (localCrewStore) return;
  localCrewStore = {};
  const now = new Date().toISOString();
  for (const spec of LOCAL_CREW_SPECS) {
    const sc = localCatalog.scenarios.find((s) => s.id === spec.initial_scenario_id) || localCatalog.scenarios[0];
    let vitals = { ...sc.vitals };
    if (spec.initial_scenario_id === "nominal") {
      vitals = applyBaselineToVitals(vitals, spec.baseline);
    }
    const rec = {
      ...spec,
      scenario_id: sc.id,
      mission_day: sc.mission_day,
      vitals,
      mission_context: buildLocalMissionContext(spec.environment_id, sc),
      nutrition: { ...sc.nutrition, logged_items: [] },
      longitudinal_series: sc.longitudinal_series.map((p) => ({ ...p })),
      active_alert: null,
      pending_verification_measurement: false,
      last_measured_at: now,
      measure_tick: 0,
    };
    syncLocalAlertFromTelemetry(rec);
    localCrewStore[spec.crew_id] = rec;
  }
}

function buildLocalCrewRoster() {
  ensureLocalCrewStore();
  const counts = { total: 0, nominal: 0, warning: 0, critical: 0, iss: 0, deep_space: 0, eva: 0 };
  const crew = LOCAL_CREW_SPECS.map((spec) => {
    const rec = localCrewStore[spec.crew_id];
    const clinical = evaluateLocalClinicalRules(rec.vitals, rec.nutrition, rec.environment_id);
    const base = evaluateLocalPersonalBaseline(rec.vitals, rec.baseline);
    const ml = buildLocalMLPrediction(clinical, rec.vitals);
    const computed = maxStatus(clinical.overall_status, base.status);
    const effective = rec.active_alert ? maxStatus(computed, rec.active_alert.severity) : computed;

    counts.total += 1;
    counts[effective.toLowerCase()] += 1;
    if (rec.mission_group === "ISS") counts.iss += 1;
    else if (rec.mission_group === "DEEP_SPACE") counts.deep_space += 1;
    else counts.eva += 1;

    return {
      crew_id: rec.crew_id,
      name: rec.name,
      callsign: rec.callsign,
      role: rec.role,
      mission_group: rec.mission_group,
      location_module: rec.location_module,
      environment_id: rec.environment_id,
      scenario_id: rec.scenario_id,
      suit_variant: rec.suit_variant,
      suit_accent: rec.suit_accent,
      status: effective,
      clinical_status: clinical.overall_status,
      within_personal_baseline: base.deviations.length === 0,
      baseline_deviations: base.deviations,
      active_alert: rec.active_alert ? { ...rec.active_alert } : null,
      pending_verification_measurement: rec.pending_verification_measurement,
      vitals: { ...rec.vitals },
      mission_context: { ...(rec.mission_context || buildLocalMissionContext(rec.environment_id, null)) },
      personal_baseline: { ...rec.baseline },
      primary_diagnosis: clinical.primary_diagnosis,
      anomaly_score: ml.anomaly_score,
      last_measured_at: rec.last_measured_at,
    };
  });

  return {
    mission_day: localCrewStore[localActiveCrewId]?.mission_day || 142,
    active_crew_id: localActiveCrewId,
    summary_counts: counts,
    space_weather: buildLocalDonkiSummary(),
    crew,
    last_updated: new Date().toISOString(),
  };
}

function recomputeLocalState(scenarioId = null, envId = null, crewId = null) {
  ensureLocalCrewStore();
  if (crewId && localCrewStore[crewId]) {
    localActiveCrewId = crewId;
  }
  const rec = localCrewStore[localActiveCrewId];

  if (scenarioId) {
    const sc = localCatalog.scenarios.find((s) => s.id === scenarioId) || localCatalog.scenarios[0];
    rec.scenario_id = sc.id;
    rec.mission_day = sc.mission_day;
    rec.vitals = sc.id === "nominal" ? applyBaselineToVitals({ ...sc.vitals }, rec.baseline) : { ...sc.vitals };
    rec.mission_context = buildLocalMissionContext(rec.environment_id, sc);
    rec.nutrition = { ...sc.nutrition, logged_items: [] };
    rec.longitudinal_series = sc.longitudinal_series.map((p) => ({ ...p }));
    if (sc.id === "nominal") {
      if (rec.active_alert) {
        rec.pending_verification_measurement = true;
        rec.active_alert.requires_recheck = true;
      }
    } else {
      rec.pending_verification_measurement = false;
      rec.active_alert = null;
      syncLocalAlertFromTelemetry(rec);
    }
  }
  if (envId) {
    rec.environment_id = envId;
    const preset = ENV_CONTEXT_PRESETS[envId] || DEFAULT_ENV_CONTEXT;
    rec.mission_context = {
      ...(rec.mission_context || DEFAULT_ENV_CONTEXT),
      ...preset,
    };
  }

  const sc = localCatalog.scenarios.find((s) => s.id === rec.scenario_id) || localCatalog.scenarios[0];
  const env = localCatalog.environments.find((e) => e.id === rec.environment_id) || localCatalog.environments[0];
  const clinical_evaluation = evaluateLocalClinicalRules(rec.vitals, rec.nutrition, rec.environment_id);
  const base = evaluateLocalPersonalBaseline(rec.vitals, rec.baseline);
  const computed = maxStatus(clinical_evaluation.overall_status, base.status);
  const effective = rec.active_alert ? maxStatus(computed, rec.active_alert.severity) : computed;

  if (effective !== clinical_evaluation.overall_status) {
    clinical_evaluation.overall_status = effective;
    clinical_evaluation.notify_earth_flight_surgeon = effective === "CRITICAL";
    clinical_evaluation.notify_crew_onboard = true;
    if (rec.active_alert && clinical_evaluation.syndrome_code === "nominal") {
      clinical_evaluation.primary_diagnosis = rec.active_alert.message;
      clinical_evaluation.matched_rules.unshift(`ALERT-${rec.active_alert.source}`);
      if (rec.pending_verification_measurement) {
        clinical_evaluation.stabilization_checklist.unshift(
          "Stabilization protocol completed. Run a confirmatory sensor measurement to verify all vitals are within personal baseline."
        );
      }
    } else if (base.status !== "NOMINAL" && clinical_evaluation.syndrome_code === "nominal") {
      clinical_evaluation.primary_diagnosis = `Personal Baseline Deviation (${base.deviations.slice(0, 2).join("; ")})`;
      clinical_evaluation.matched_rules.unshift("PERSONAL-BASELINE-DRIFT");
    }
  }

  const ml_prediction = buildLocalMLPrediction(clinical_evaluation, rec.vitals);

  localState = {
    mission_day: rec.mission_day,
    crew_id: rec.crew_id,
    crew_member: `${rec.name} (${rec.callsign})`,
    crew_role: rec.role,
    mission_group: rec.mission_group,
    location_module: rec.location_module,
    suit_variant: rec.suit_variant,
    scenario_id: sc.id,
    scenario_name: sc.name,
    scenario_description: sc.description,
    environment_id: env.id,
    environment_name: env.name,
    one_way_latency_seconds: env.one_way_latency_seconds,
    vitals: { ...rec.vitals },
    mission_context: { ...(rec.mission_context || buildLocalMissionContext(rec.environment_id, sc)) },
    personal_baseline: { ...rec.baseline },
    within_personal_baseline: base.deviations.length === 0,
    baseline_deviations: base.deviations,
    active_alert: rec.active_alert ? { ...rec.active_alert } : null,
    pending_verification_measurement: rec.pending_verification_measurement,
    last_measured_at: rec.last_measured_at,
    nutrition: { ...rec.nutrition },
    clinical_evaluation,
    ml_prediction,
    space_weather: buildLocalDonkiSummary(),
    longitudinal_series: rec.longitudinal_series,
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
// Pain marked on the 3D body. Backend only: a fabricated pain history would mislead the ML and the ground team.
export const reportPain = (crewId, payload) => postJson(`/api/crew/${encodeURIComponent(crewId)}/pain`, payload);
export const resolvePain = (crewId, region) =>
  tryFetch(`/api/crew/${encodeURIComponent(crewId)}/pain/${encodeURIComponent(region)}`, { method: "DELETE", timeoutMs: 15000 });

function buildPersonalBaselineFromState(rawState, spec) {
  if (spec?.baseline) return { ...spec.baseline };
  const metrics = rawState?.adaptive_baseline?.metrics;
  if (!metrics) return { ...DEFAULT_PERSONAL_BASELINE };
  const val = (k, fallback) => metrics[k]?.phase_adapted_baseline ?? metrics[k]?.pre_flight_baseline ?? fallback;
  const hr = val("heart_rate_bpm", 68);
  const sys = val("bp_systolic", 116);
  const temp = val("temperature_c", 36.7);
  const glu = val("glucose_mg_dl", 93);
  const hrv = val("hrv_ms", 56);
  return {
    resting_hr_bpm: Math.round(hr),
    hr_min: Math.round((hr - 14) * 10) / 10,
    hr_max: Math.round((hr + 15) * 10) / 10,
    resting_bp_systolic: Math.round(sys),
    resting_bp_diastolic: Math.round(val("bp_diastolic", 74)),
    bp_sys_min: Math.round((sys - 16) * 10) / 10,
    bp_sys_max: Math.round((sys + 16) * 10) / 10,
    resting_temp_c: Math.round(temp * 10) / 10,
    temp_min: Math.round((temp - 0.6) * 10) / 10,
    temp_max: Math.round((temp + 0.6) * 10) / 10,
    resting_spo2_pct: val("spo2_pct", 98.4),
    spo2_min: 95.0,
    resting_glucose_mg_dl: Math.round(glu),
    glucose_min: Math.round(glu - 18),
    glucose_max: Math.round(glu + 32),
    resting_sleep_hours: val("sleep_hours", 7.3),
    sleep_min: T.SLEEP_WARN_H,
    resting_hrv_ms: Math.round(hrv),
    hrv_min: Math.round(hrv - 18),
    radiation_max: 0.14,
  };
}

function buildEffectiveMissionContext(rawState, overlay) {
  const envId = rawState?.environment_id || "transit_hab";
  const scId = rawState?.scenario_id || "nominal";
  const sc = localCatalog?.scenarios?.find((s) => s.id === scId) || { id: scId };
  return {
    ...buildLocalMissionContext(envId, sc),
    ...(rawState?.mission_context || {}),
    ...(overlay?.missionContextOverride || {}),
  };
}

function syncLocalRecordFromBackendState(rawState) {
  if (!rawState?.astronaut_id || !localCrewStore) return;
  const rec = localCrewStore[rawState.astronaut_id];
  if (!rec) return;
  const overlay = crewAlertOverlay[rawState.astronaut_id];
  rec.scenario_id = rawState.scenario_id || rec.scenario_id;
  rec.environment_id = rawState.environment_id || rec.environment_id;
  rec.mission_day = rawState.mission_day ?? rec.mission_day;
  rec.vitals = overlay?.vitalsOverride ? { ...rawState.vitals, ...overlay.vitalsOverride } : { ...rawState.vitals };
  rec.mission_context = buildEffectiveMissionContext(rawState, overlay);
  if (rawState.nutrition) rec.nutrition = { ...rawState.nutrition };
  if (Array.isArray(rawState.longitudinal_series) && rawState.longitudinal_series.length) {
    rec.longitudinal_series = rawState.longitudinal_series.map((p) => ({ ...p }));
  }
  rec.last_measured_at = rawState.last_updated || new Date().toISOString();
  if (overlay?.active_alert) {
    rec.active_alert = { ...overlay.active_alert };
    rec.pending_verification_measurement = Boolean(overlay.pending_verification_measurement);
  } else {
    rec.pending_verification_measurement = false;
    if (rawState.clinical_evaluation?.overall_status && rawState.clinical_evaluation.overall_status !== "NOMINAL") {
      rec.active_alert = {
        alert_id: rawState.explainable_alerts?.[0]?.alert_id || `ALT-${rec.crew_id.toUpperCase()}`,
        severity: rawState.clinical_evaluation.overall_status,
        source: "CLINICAL_TELEMETRY",
        message: rawState.explainable_alerts?.[0]?.title || rawState.clinical_evaluation.primary_diagnosis,
        issued_at: rawState.last_updated || new Date().toISOString(),
        issued_by: "AstraCare Auto-Triage",
        acknowledged_by_crew: false,
        requires_recheck: true,
      };
    } else {
      rec.active_alert = null;
    }
  }
}

function enrichBackendState(rawState) {
  if (!rawState) return rawState;
  const crewId = rawState.astronaut_id || rawState.crew_id || localActiveCrewId;
  const spec = LOCAL_CREW_SPECS.find((c) => c.crew_id === crewId);
  const personal_baseline = buildPersonalBaselineFromState(rawState, spec);
  const overlay = crewAlertOverlay[crewId];

  const vitals = overlay?.vitalsOverride ? { ...rawState.vitals, ...overlay.vitalsOverride } : rawState.vitals;
  const mission_context = buildEffectiveMissionContext(rawState, overlay);
  const base = evaluateBaselineAndMetricStatuses(vitals, personal_baseline);

  let clinical_evaluation = rawState.clinical_evaluation;
  let active_alert = overlay?.active_alert ? { ...overlay.active_alert } : null;

  if (!active_alert && clinical_evaluation?.overall_status && clinical_evaluation.overall_status !== "NOMINAL") {
    active_alert = {
      alert_id: rawState.explainable_alerts?.[0]?.alert_id || `ALT-${crewId.toUpperCase()}`,
      severity: clinical_evaluation.overall_status,
      source: "CLINICAL_TELEMETRY",
      message: rawState.explainable_alerts?.[0]?.title || clinical_evaluation.primary_diagnosis,
      issued_at: rawState.last_updated || new Date().toISOString(),
      issued_by: "AstraCare Auto-Triage",
      acknowledged_by_crew: false,
      requires_recheck: true,
    };
  }

  if (active_alert && clinical_evaluation) {
    const effectiveOverall = maxStatus(clinical_evaluation.overall_status, active_alert.severity);
    if (effectiveOverall !== clinical_evaluation.overall_status || overlay?.active_alert) {
      clinical_evaluation = {
        ...clinical_evaluation,
        overall_status: effectiveOverall,
        primary_diagnosis:
          clinical_evaluation.syndrome_code === "nominal" ? active_alert.message : clinical_evaluation.primary_diagnosis,
      };
    }
  }

  syncLocalRecordFromBackendState(rawState);

  return {
    ...rawState,
    crew_id: crewId,
    crew_role: spec?.role || "Flight Crew",
    mission_group: spec?.mission_group || "DEEP_SPACE",
    location_module: spec?.location_module || rawState.environment_name,
    suit_variant: spec?.suit_variant || "MERCURY_EVA_SILVER",
    vitals,
    mission_context,
    personal_baseline,
    within_personal_baseline: base.deviations.length === 0,
    baseline_deviations: base.deviations,
    active_alert,
    pending_verification_measurement: Boolean(overlay?.pending_verification_measurement),
    clinical_evaluation,
  };
}

// New reading from the NASA-calibrated stochastic generator (backend only; no browser equivalent).
export async function nextTelemetryReading(crisisProbability = 0) {
  if (!BACKEND_ASTRONAUT_IDS.has(localActiveCrewId)) {
    throw new Error("Live stochastic telemetry stream is available for backend crew profiles (Elena, Lucas, Kenji, Amara, Liam).");
  }
  const raw = await postJson(`/api/telemetry/next?crisis_probability=${crisisProbability}`);
  delete crewAlertOverlay[raw.astronaut_id];
  lastLiveState = raw;
  return enrichBackendState(raw);
}

export async function getCrewRoster(liveState = null) {
  let stateToSync = liveState || lastLiveState;
  if (!stateToSync && connectionMode !== "simulated") {
    try {
      stateToSync = await tryFetch("/api/state");
      lastLiveState = stateToSync;
    } catch {
      /* backend offline -> use local roster */
    }
  }
  await loadLocalData();
  ensureLocalCrewStore();
  if (stateToSync) {
    syncLocalRecordFromBackendState(stateToSync);
  }
  const roster = buildLocalCrewRoster();
  if (stateToSync?.space_weather) {
    roster.space_weather = stateToSync.space_weather;
  }
  roster.active_crew_id = localActiveCrewId;
  return roster;
}

export async function selectCrewMember(crewId) {
  localActiveCrewId = crewId;
  if (BACKEND_ASTRONAUT_IDS.has(crewId)) {
    try {
      const raw = await tryFetch(`/api/astronaut/${encodeURIComponent(crewId)}`, { method: "POST" });
      lastLiveState = raw;
      return enrichBackendState(raw);
    } catch {
      /* fall through to offline store */
    }
  }
  await loadLocalData();
  return recomputeLocalState(null, null, crewId);
}

export async function dispatchCrewAlert(crewId, payload) {
  await loadLocalData();
  ensureLocalCrewStore();
  const rec = localCrewStore[crewId];
  const vitalsOverride = {};
  const missionContextOverride = {};
  if (rec) {
    const b = rec.baseline;
    if (payload.simulate_vitals_drift !== false) {
      const msgLower = String(payload.message || "").toLowerCase();
      if (msgLower.includes("co2")) {
        missionContextOverride.cabin_co2_mmhg = payload.severity === "CRITICAL" ? 5.8 : 4.5;
      }
      if (msgLower.includes("pressure") || msgLower.includes("suit")) {
        missionContextOverride.cabin_pressure_psia = payload.severity === "CRITICAL" ? 7.8 : 10.2;
      }
      if (msgLower.includes("radiation")) {
        vitalsOverride.radiation_msv_h = payload.severity === "CRITICAL" ? 0.68 : 0.28;
      }
      if (payload.severity === "WARNING") {
        vitalsOverride.heart_rate_bpm = Math.round(Math.max(rec.vitals.heart_rate_bpm, b.hr_max + 10) * 10) / 10;
        vitalsOverride.bp_systolic = Math.round(Math.min(rec.vitals.bp_systolic, b.bp_sys_min - 7) * 10) / 10;
        vitalsOverride.stress_index = Math.max(rec.vitals.stress_index, 64);
        vitalsOverride.mood_score = Math.min(rec.vitals.mood_score ?? 5, 3);
        vitalsOverride.hrv_ms = Math.min(rec.vitals.hrv_ms, b.hrv_min - 6);
      } else {
        vitalsOverride.heart_rate_bpm = Math.round(Math.max(rec.vitals.heart_rate_bpm, b.hr_max + 26) * 10) / 10;
        vitalsOverride.temperature_c = Math.round(Math.max(rec.vitals.temperature_c, b.temp_max + 1.0) * 10) / 10;
        vitalsOverride.bp_systolic = Math.round(Math.min(rec.vitals.bp_systolic, Math.max(80, b.bp_sys_min - 18)) * 10) / 10;
        vitalsOverride.spo2_pct = Math.round(Math.min(rec.vitals.spo2_pct, Math.max(89.5, b.spo2_min - 3.2)) * 10) / 10;
        vitalsOverride.stress_index = Math.max(rec.vitals.stress_index, 85);
        vitalsOverride.mood_score = Math.min(rec.vitals.mood_score ?? 5, 2);
        vitalsOverride.hrv_ms = Math.min(rec.vitals.hrv_ms, Math.max(18, b.hrv_min - 18));
      }
      Object.assign(rec.vitals, vitalsOverride);
      if (Object.keys(missionContextOverride).length) {
        rec.mission_context = {
          ...(rec.mission_context || buildLocalMissionContext(rec.environment_id, null)),
          ...missionContextOverride,
        };
      }
    }
    const alertObj = {
      alert_id: `MC-${Math.random().toString(16).slice(2, 8).toUpperCase()}`,
      severity: payload.severity,
      source: "MISSION_CONTROL",
      origin_type: "MISSION_CONTROL_DISPATCH",
      message: payload.message,
      issued_at: new Date().toISOString(),
      issued_by: payload.issued_by || "Mission Control (Houston)",
      acknowledged_by_crew: false,
      requires_recheck: true,
    };
    rec.active_alert = alertObj;
    rec.pending_verification_measurement = false;
    crewAlertOverlay[crewId] = {
      active_alert: { ...alertObj },
      pending_verification_measurement: false,
      vitalsOverride: Object.keys(vitalsOverride).length ? vitalsOverride : null,
      missionContextOverride: Object.keys(missionContextOverride).length ? missionContextOverride : null,
    };
  }
  return buildLocalCrewRoster();
}

export async function acknowledgeCrewAlert(crewId) {
  await loadLocalData();
  ensureLocalCrewStore();
  const rec = localCrewStore[crewId];
  if (rec?.active_alert) {
    rec.active_alert.acknowledged_by_crew = true;
  }
  if (crewAlertOverlay[crewId]?.active_alert) {
    crewAlertOverlay[crewId].active_alert.acknowledged_by_crew = true;
  }
  return buildLocalCrewRoster();
}

export async function stabilizeCrewMember(crewId, note = "CHeCS countermeasure & stabilization protocol applied") {
  await loadLocalData();
  ensureLocalCrewStore();
  const rec = localCrewStore[crewId];
  const overlay = crewAlertOverlay[crewId];

  if (rec) {
    const b = rec.baseline;
    rec.scenario_id = "nominal";
    rec.vitals = {
      ...rec.vitals,
      heart_rate_bpm: b.resting_hr_bpm,
      hrv_ms: b.resting_hrv_ms,
      bp_systolic: b.resting_bp_systolic,
      bp_diastolic: b.resting_bp_diastolic,
      temperature_c: b.resting_temp_c,
      spo2_pct: b.resting_spo2_pct,
      respiration_rpm: 14,
      glucose_mg_dl: b.resting_glucose_mg_dl,
      sleep_hours: b.resting_sleep_hours,
      sleep_streak_low_days: 0,
      rem_sleep_pct: 22.0,
      mood_score: 5,
      stress_index: 22,
      radiation_msv_h: 0.04,
      shoulder_pain_score: 0,
      pfo_decompression_risk: "LOW",
      urinary_calcium_mg_d: 185,
      intraocular_pressure_mmhg: 15.2,
    };
    rec.nutrition.calories_kcal = Math.max(rec.nutrition.calories_kcal, 2400);
    rec.nutrition.water_ml = Math.max(rec.nutrition.water_ml, 2250);
    rec.mission_context = {
      ...DEFAULT_ENV_CONTEXT,
      ...(ENV_CONTEXT_PRESETS[rec.environment_id] || {}),
    };
    if (rec.active_alert) {
      rec.pending_verification_measurement = true;
      rec.active_alert.requires_recheck = true;
      if (note) rec.active_alert.message = `${note} — Awaiting confirmatory sensor measurement.`;
    }
  }

  if (overlay) {
    overlay.vitalsOverride = null;
    overlay.missionContextOverride = null;
    overlay.pending_verification_measurement = Boolean(overlay.active_alert);
    if (overlay.active_alert && note) {
      overlay.active_alert.requires_recheck = true;
      overlay.active_alert.message = `${note} — Awaiting confirmatory sensor measurement.`;
    }
  }

  if (BACKEND_ASTRONAUT_IDS.has(crewId) && connectionMode === "live" && lastLiveState?.astronaut_id === crewId) {
    try {
      const raw = await tryFetch("/api/scenario/nominal", { method: "POST" });
      lastLiveState = raw;
      return enrichBackendState(raw);
    } catch {
      /* fall back to local update */
    }
  }

  return recomputeLocalState(null, null, crewId);
}

export async function measureCrewMember(crewId, systemId = "full_body") {
  return triggerMeasurement(systemId, crewId);
}

export async function getMissionState(crewId = null) {
  const targetId = crewId || localActiveCrewId;
  if (targetId && !BACKEND_ASTRONAUT_IDS.has(targetId)) {
    await loadLocalData();
    return recomputeLocalState(null, null, targetId);
  }
  try {
    let raw = await tryFetch("/api/state");
    if (targetId && BACKEND_ASTRONAUT_IDS.has(targetId) && raw.astronaut_id !== targetId) {
      raw = await tryFetch(`/api/astronaut/${encodeURIComponent(targetId)}`, { method: "POST" });
    }
    localActiveCrewId = raw.astronaut_id || targetId || "elena_vance";
    lastLiveState = raw;
    return enrichBackendState(raw);
  } catch (err) {
    // A bug in the enrichment below used to look exactly like "backend offline"; say why we fell back.
    console.warn("[AstraCare] using browser simulation for mission state:", err);
    await loadLocalData();
    return recomputeLocalState(null, null, targetId);
  }
}

export async function switchScenario(scenarioId, crewId = null) {
  const targetId = crewId || localActiveCrewId;
  if (BACKEND_ASTRONAUT_IDS.has(targetId)) {
    try {
      if (lastLiveState?.astronaut_id !== targetId) {
        await tryFetch(`/api/astronaut/${encodeURIComponent(targetId)}`, { method: "POST" });
      }
      const raw = await tryFetch(`/api/scenario/${encodeURIComponent(scenarioId)}`, { method: "POST" });
      delete crewAlertOverlay[targetId];
      lastLiveState = raw;
      return enrichBackendState(raw);
    } catch {
      /* fall through to local simulation */
    }
  }
  await loadLocalData();
  delete crewAlertOverlay[targetId];
  return recomputeLocalState(scenarioId, null, targetId);
}

export async function switchEnvironment(envId, crewId = null) {
  const targetId = crewId || localActiveCrewId;
  if (BACKEND_ASTRONAUT_IDS.has(targetId)) {
    try {
      if (lastLiveState?.astronaut_id !== targetId) {
        await tryFetch(`/api/astronaut/${encodeURIComponent(targetId)}`, { method: "POST" });
      }
      const raw = await tryFetch(`/api/environment/${encodeURIComponent(envId)}`, { method: "POST" });
      lastLiveState = raw;
      return enrichBackendState(raw);
    } catch {
      /* fall through to local simulation */
    }
  }
  await loadLocalData();
  return recomputeLocalState(null, envId, targetId);
}

export async function triggerMeasurement(systemId, crewId = null) {
  const targetId = crewId || localActiveCrewId;
  const isFull = systemId === "full_body";
  const backendSystemId = isFull ? "cardiovascular" : systemId;

  if (BACKEND_ASTRONAUT_IDS.has(targetId) && connectionMode !== "simulated") {
    try {
      if (lastLiveState?.astronaut_id !== targetId) {
        await tryFetch(`/api/astronaut/${encodeURIComponent(targetId)}`, { method: "POST" });
      }
      const res = await tryFetch(`/api/measure/${encodeURIComponent(backendSystemId)}`, { method: "POST" });
      if (res?.state) {
        lastLiveState = res.state;
        const spec = LOCAL_CREW_SPECS.find((c) => c.crew_id === targetId);
        const pb = buildPersonalBaselineFromState(res.state, spec);
        const overlay = crewAlertOverlay[targetId];
        const effectiveVitals = overlay?.vitalsOverride
          ? { ...res.state.vitals, ...overlay.vitalsOverride }
          : res.state.vitals;
        const base = evaluateBaselineAndMetricStatuses(effectiveVitals, pb);

        let noteSuffix = "";
        if (res.state.clinical_evaluation?.overall_status === "NOMINAL" && base.status === "NOMINAL") {
          if (crewAlertOverlay[targetId]) {
            delete crewAlertOverlay[targetId];
            noteSuffix = " | VERIFIED WITHIN PERSONAL BASELINE (Alert Normalized)";
          }
          if (localCrewStore?.[targetId]) {
            localCrewStore[targetId].active_alert = null;
            localCrewStore[targetId].pending_verification_measurement = false;
          }
        }

        const enriched = enrichBackendState(res.state);
        return {
          ...res,
          system_name: isFull ? "Full-Body Personal Baseline Scan" : res.system_name,
          reading_summary: `${res.reading_summary}${noteSuffix}`,
          state: enriched,
        };
      }
      return res;
    } catch {
      /* fall through to local simulation */
    }
  }

  await loadLocalData();
  ensureLocalCrewStore();
  if (targetId && localCrewStore[targetId]) localActiveCrewId = targetId;
  const rec = localCrewStore[localActiveCrewId];

  rec.measure_tick += 1;
  const delta = rec.measure_tick % 2 === 1 ? 0.4 : -0.4;
  if (systemId === "cardiovascular" || isFull) {
    rec.vitals.heart_rate_bpm = Math.round((rec.vitals.heart_rate_bpm + delta) * 10) / 10;
  }
  rec.last_measured_at = new Date().toISOString();

  const clinical = evaluateLocalClinicalRules(rec.vitals, rec.nutrition, rec.environment_id);
  const base = evaluateLocalPersonalBaseline(rec.vitals, rec.baseline);
  let note;
  if (clinical.overall_status === "NOMINAL" && base.status === "NOMINAL") {
    rec.active_alert = null;
    rec.pending_verification_measurement = false;
    delete crewAlertOverlay[rec.crew_id];
    note = "VERIFIED WITHIN PERSONAL BASELINE (Alert Normalized)";
  } else {
    syncLocalAlertFromTelemetry(rec);
    note = `OUTSIDE PERSONAL BASELINE (${base.deviations.slice(0, 2).join("; ") || clinical.primary_diagnosis}) — Alert Active`;
  }

  const state = recomputeLocalState(null, null, rec.crew_id);
  const sys = state.clinical_evaluation.systems[isFull ? "cardiovascular" : systemId];
  return {
    system_id: isFull ? "cardiovascular" : systemId,
    system_name: isFull ? "Full-Body Personal Baseline Scan" : sys.name,
    device_used: sys.checs_device,
    decontamination_required: state.clinical_evaluation.decontamination_required,
    decontamination_checklist: state.clinical_evaluation.decontamination_checklist,
    reading_summary: `${isFull ? "Full-Body Sync" : sys.name}: HR ${Math.round(rec.vitals.heart_rate_bpm)} bpm | ${note}`,
    status: isFull ? state.clinical_evaluation.overall_status : sys.status,
    guidance: sys.recommended_action,
    state,
  };
}

export async function sendAgentChat(message, crewId = null) {
  const targetId = crewId || localActiveCrewId;
  if (BACKEND_ASTRONAUT_IDS.has(targetId) && connectionMode !== "simulated") {
    try {
      if (lastLiveState?.astronaut_id !== targetId) {
        await tryFetch(`/api/astronaut/${encodeURIComponent(targetId)}`, { method: "POST" });
      }
      const res = await tryFetch("/api/agent/chat", {
        method: "POST",
        body: JSON.stringify({ message }),
        timeoutMs: 15000,
      });
      if (res?.state) {
        lastLiveState = res.state;
        return { ...res, state: enrichBackendState(res.state) };
      }
      return res;
    } catch {
      /* fall through to local simulation */
    }
  }

  await loadLocalData();
  ensureLocalCrewStore();
  if (targetId && localCrewStore[targetId]) localActiveCrewId = targetId;
  const rec = localCrewStore[localActiveCrewId];
  const lower = message.toLowerCase();
  const trace = [];

  const waterMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*(ml|l|liter)/);
  const appleMatch = lower.match(/(\d+)\s*apple/);
  if (waterMatch || appleMatch || lower.includes("ate") || lower.includes("drank") || lower.includes("bar") || lower.includes("meal")) {
    const wMl = waterMatch ? parseFloat(waterMatch[1]) * (waterMatch[2].startsWith("l") ? 1000 : 1) : 250;
    const kcal = appleMatch ? parseInt(appleMatch[1], 10) * 95 : 220;
    const carbs = appleMatch ? parseInt(appleMatch[1], 10) * 25 : 32;
    rec.nutrition.calories_kcal += kcal;
    rec.nutrition.water_ml += wMl;
    rec.nutrition.carbs_g += carbs;
    if (rec.vitals.glucose_mg_dl < 85) rec.vitals.glucose_mg_dl += Math.round(carbs * 0.6);
    rec.nutrition.logged_items.unshift({
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
    if (rec.active_alert) rec.pending_verification_measurement = true;
    trace.push({ tool_name: "log_nutrition_hydration", status: "OK", summary: `+${kcal} kcal, +${wMl} ml H2O`, rule_or_score: "Na/Fe Checked" });
  }

  const sleepMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*(?:h|hr|hrs|hours)/);
  if (sleepMatch || lower.includes("shoulder") || lower.includes("dizzy") || lower.includes("tired")) {
    if (sleepMatch) rec.vitals.sleep_hours = parseFloat(sleepMatch[1]);
    if (lower.includes("shoulder")) rec.vitals.shoulder_pain_score = 6;
    if (lower.includes("dizzy") || lower.includes("exhausted")) rec.vitals.mood_score = 2;
    if (rec.active_alert) rec.pending_verification_measurement = true;
    trace.push({ tool_name: "log_sleep_mood_checkin", status: "WARNING", summary: "Updated Sleep/EVA check-in", rule_or_score: "OCHMO-MTB-009/006" });
  }

  const state = recomputeLocalState(null, null, rec.crew_id);
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

export async function getSpaceWeather(force = false) {
  try {
    return await tryFetch(`/api/nasa/space-weather${force ? "?force=true" : ""}`, { timeoutMs: 12000 });
  } catch {
    await loadLocalData();
    return buildLocalDonkiSummary();
  }
}

export async function generateTelemedicineDossier(crewId = null) {
  const targetId = crewId || localActiveCrewId;
  if (BACKEND_ASTRONAUT_IDS.has(targetId) && connectionMode !== "simulated") {
    try {
      if (lastLiveState?.astronaut_id !== targetId) {
        await tryFetch(`/api/astronaut/${encodeURIComponent(targetId)}`, { method: "POST" });
      }
      return await tryFetch("/api/telemedicine/dossier", { method: "POST" });
    } catch {
      /* fall through to offline dossier */
    }
  }
  await loadLocalData();
  const state = recomputeLocalState(null, null, targetId);
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
