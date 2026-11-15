"""
Single source of truth for the NASA-calibrated ranges used by the telemetry generator, the clinical rules
and the cross-diagnosis tree.

Each value carries a `source` and a `verified` flag:
  verified=True  -> the number was read in the cited document while building this module.
  verified=False -> the number comes from the AstraCare engineering spec (task brief) that cites the source,
                    but it was not found verbatim in that document. Re-check before using it outside the demo.
"""

from __future__ import annotations

from dataclasses import dataclass

SRC_OCHMO_RAD = "https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"
SRC_HRR = "https://humanresearchroadmap.nasa.gov/"
SRC_HRP = "https://www.nasa.gov/hrp/hazards/"
SRC_SSM = "https://pmc.ncbi.nlm.nih.gov/articles/PMC12612093/"
SRC_SLS2 = "https://osdr.nasa.gov/bio/repo/data/payloads/SLS-2"
SRC_DSO = "https://nlsp.nasa.gov/search/data/details/e980c7a8-e26c-56ea-bb5a-66dcb8723354?dataType=EXPERIMENTS"
SRC_BHP_520 = "https://ntrs.nasa.gov/api/citations/20140012751/downloads/20140012751.pdf"
SRC_CSA_RAD = "https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp"


@dataclass(frozen=True)
class Range:
    low: float
    high: float
    source: str
    verified: bool = False
    note: str = ""

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2.0

    def clamp(self, value: float) -> float:
        return min(self.high, max(self.low, value))


# ---------------- In-flight nominal ranges (what the generator draws around) ----------------
NOMINAL = {
    # 0.6-0.9 mSv/day in transit/Mars ~= 0.025-0.038 mSv/h. OCHMO brief cites ~0.5 mSv/day for a surface mission.
    "radiation_msv_h": Range(0.025, 0.038, SRC_OCHMO_RAD, False, "spec 0.6-0.9 mSv/day; OCHMO surface ~0.5 mSv/day (verified)"),
    "heart_rate_bpm": Range(55, 85, SRC_HRR, False, "reduced diurnal variation in orbit"),
    "bp_systolic": Range(105, 125, SRC_SLS2, False),
    "bp_diastolic": Range(60, 75, SRC_SLS2, False, "diastolic falls 5-10 mmHg with cephalad fluid shift"),
    "sleep_hours": Range(5.82, 6.0, SRC_SSM, False, "5.82 h unmedicated to 6.0 h with support (spec value; not in SSM text)"),
    "ctb_reaction_time_ms": Range(250, 300, SRC_SSM, False, "CTB baseline (spec value; SSM reports slowing without magnitude)"),
    "mood_score": Range(3.5, 4.5, SRC_SSM, False, "1-5 scale"),
    "temperature_c": Range(36.3, 37.2, SRC_HRR, False),
    "glucose_mg_dl": Range(75, 115, SRC_HRR, False),
    "sleep_latency_min": Range(20, 45, SRC_SSM, False),
}

# Adaptation effects quoted in the spec (relative to the individual baseline)
ACUTE_ADAPTATION_HR_PCT = (0.10, 0.15)  # first 24 h peak
SPACE_FATIGUE_CTB_PCT = (0.15, 0.25)  # third-quarter / fatigue slowing

# ---------------- Critical triggers ("B.O.") ----------------
RADIATION_SPE_RATE_MSV_H = 0.5  # immediate shelter
RADIATION_WARN_RATE_MSV_H = 0.1  # ~3x the transit nominal ceiling
SPE_EVENT_LIMIT_MSV = 250.0  # verified: "limited to an effective dose of 250 mSv per event"
CAREER_LIMIT_MSV = 600.0  # verified: "not to exceed 600 millisieverts (mSv)"

HR_CRIT_LOW, HR_CRIT_HIGH = 45.0, 115.0
HR_WARN_LOW, HR_WARN_HIGH = 50.0, 100.0
BP_SYS_CRIT_LOW, BP_SYS_CRIT_HIGH = 90.0, 145.0
BP_SYS_WARN_LOW, BP_SYS_WARN_HIGH = 95.0, 135.0
SLEEP_CRIT_H = 4.5  # for 2 consecutive nights
SLEEP_CRIT_NIGHTS = 2
SLEEP_WARN_H = 5.0
CTB_CRIT_MS = 390.0  # > +30 % over a 300 ms baseline
CTB_WARN_MS = 345.0  # +15 %
MOOD_CRIT = 2
TEMP_CRIT_HIGH, TEMP_CRIT_LOW = 38.0, 35.5
TEMP_WARN_HIGH, TEMP_WARN_LOW = 37.5, 36.0
GLUCOSE_CRIT_LOW, GLUCOSE_CRIT_HIGH = 65.0, 180.0
GLUCOSE_WARN_LOW, GLUCOSE_WARN_HIGH = 70.0, 140.0

REFERENCES = [
    {"code": "NASA HRP Hazards", "title": "Five hazards of human spaceflight", "url": SRC_HRP},
    {"code": "NASA HRR", "title": "Human Research Roadmap evidence reports", "url": SRC_HRR},
    {"code": "OCHMO Radiation Brief", "title": "NASA-STD-3001 radiation protection technical brief", "url": SRC_OCHMO_RAD},
    {"code": "NASA SSM", "title": "Spaceflight Standard Measures", "url": SRC_SSM},
    {"code": "OSDR SLS-2", "title": "Spacelab Life Sciences 2 payload", "url": SRC_SLS2},
]
