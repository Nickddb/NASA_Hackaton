// Mirror of backend/app/engine/nasa_calibration.py so tiles and the backend rules agree on what is abnormal.
// Keep both files in sync when a threshold changes.
export const T = {
  HR_CRIT_LOW: 45,
  HR_CRIT_HIGH: 115,
  HR_WARN_LOW: 50,
  HR_WARN_HIGH: 100,
  BP_SYS_CRIT_LOW: 90,
  BP_SYS_CRIT_HIGH: 145,
  BP_SYS_WARN_LOW: 95,
  BP_SYS_WARN_HIGH: 135,
  TEMP_CRIT_HIGH: 38.0,
  TEMP_CRIT_LOW: 35.5,
  TEMP_WARN_HIGH: 37.5,
  TEMP_WARN_LOW: 36.0,
  GLUCOSE_CRIT_LOW: 65,
  GLUCOSE_CRIT_HIGH: 180,
  GLUCOSE_WARN_LOW: 70,
  GLUCOSE_WARN_HIGH: 140,
  SLEEP_CRIT_H: 4.5,
  SLEEP_CRIT_NIGHTS: 2,
  SLEEP_WARN_H: 5.0, // in-flight average is ~5.8-6.0 h, so 6.5 h is not a useful warning in orbit
  CTB_CRIT_MS: 390,
  CTB_WARN_MS: 345,
  RAD_CRIT_MSV_H: 0.5,
  RAD_WARN_MSV_H: 0.1,
};

export const hrStatus = (hr) =>
  hr > T.HR_CRIT_HIGH || hr < T.HR_CRIT_LOW ? "CRITICAL" : hr > T.HR_WARN_HIGH || hr < T.HR_WARN_LOW ? "WARNING" : "NORMAL";

export const bpStatus = (sys) =>
  sys < T.BP_SYS_CRIT_LOW || sys > T.BP_SYS_CRIT_HIGH
    ? "CRITICAL"
    : sys < T.BP_SYS_WARN_LOW || sys > T.BP_SYS_WARN_HIGH
      ? "WARNING"
      : "NORMAL";

export const tempStatus = (t) =>
  t >= T.TEMP_CRIT_HIGH || t < T.TEMP_CRIT_LOW ? "CRITICAL" : t >= T.TEMP_WARN_HIGH || t < T.TEMP_WARN_LOW ? "WARNING" : "NORMAL";

export const glucoseStatus = (g) =>
  g < T.GLUCOSE_CRIT_LOW || g > T.GLUCOSE_CRIT_HIGH
    ? "CRITICAL"
    : g <= T.GLUCOSE_WARN_LOW || g >= T.GLUCOSE_WARN_HIGH
      ? "WARNING"
      : "NORMAL";

export const sleepStatus = (hours, lowNights = 0) =>
  lowNights >= T.SLEEP_CRIT_NIGHTS ? "CRITICAL" : hours < T.SLEEP_CRIT_H || hours < T.SLEEP_WARN_H ? "WARNING" : "NORMAL";

export const radiationStatus = (r) => (r > T.RAD_CRIT_MSV_H ? "CRITICAL" : r >= T.RAD_WARN_MSV_H ? "WARNING" : "NORMAL");
