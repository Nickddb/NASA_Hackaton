"""
Smartwatch exam scheduler: periodic or on-demand biometric collection for each crew member.

It only orchestrates existing services: a new reading from the NASA-calibrated generator
(MissionStateManager.next_telemetry_reading) followed by the system measurement the exam asks for
(MissionStateManager.trigger_measurement). The background loop in main.py calls run_due().
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

ExamType = Literal["full_panel", "cardio", "cognitive_ctb", "dosimetry", "respiratory", "metabolic"]

# exam -> system measured by trigger_measurement
EXAM_SYSTEMS: dict[str, str] = {
    "full_panel": "full_body",
    "cardio": "cardiovascular",
    "cognitive_ctb": "nervous_sleep",
    "dosimetry": "radiation",
    "respiratory": "respiratory",
    "metabolic": "metabolic",
}
MIN_INTERVAL_MIN = 1.0
MAX_INTERVAL_MIN = 24 * 60.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ExamSchedule:
    astronaut_id: str
    exam_type: str
    interval_minutes: float
    next_due_at: str
    created_at: str
    last_run_at: str | None = None
    runs: int = 0
    active: bool = True


@dataclass
class ExamResult:
    astronaut_id: str
    exam_type: str
    collected_at: str
    system_id: str
    reading_summary: str
    telemetry_payload: dict[str, Any] = field(default_factory=dict)


class SmartwatchScheduler:
    def __init__(self, state_manager, clock=_now) -> None:
        self.state_manager = state_manager
        self._clock = clock
        self.schedules: dict[tuple[str, str], ExamSchedule] = {}

    # ---------- configuration ----------
    def schedule(
        self, astronaut_id: str, exam_type: str, interval_minutes: float | None = None, trigger_now: bool = False
    ) -> dict[str, Any]:
        if astronaut_id not in self.state_manager.crew_records:
            raise KeyError(f"Unknown astronaut_id: {astronaut_id}")
        if exam_type not in EXAM_SYSTEMS:
            raise ValueError(f"Unknown exam_type {exam_type!r}; use one of {sorted(EXAM_SYSTEMS)}")
        if interval_minutes is None and not trigger_now:
            raise ValueError("Give interval_minutes for a periodic exam or trigger_now=true for an immediate one")

        out: dict[str, Any] = {"schedule": None, "result": None}
        if interval_minutes is not None:
            interval = min(MAX_INTERVAL_MIN, max(MIN_INTERVAL_MIN, float(interval_minutes)))
            now = self._clock()
            sched = ExamSchedule(
                astronaut_id=astronaut_id,
                exam_type=exam_type,
                interval_minutes=interval,
                next_due_at=(now + timedelta(minutes=interval)).isoformat(),
                created_at=now.isoformat(),
            )
            self.schedules[(astronaut_id, exam_type)] = sched
            self.state_manager.earth_sync.record_audit_event(
                event_type="SMARTWATCH_EXAM_SCHEDULED",
                astronaut_id=astronaut_id,
                summary=f"{exam_type} every {interval:g} min",
                metadata={"exam_type": exam_type, "interval_minutes": interval},
            )
            out["schedule"] = asdict(sched)
        if trigger_now:
            out["result"] = asdict(self.run_exam(astronaut_id, exam_type))
        return out

    def cancel(self, astronaut_id: str, exam_type: str) -> bool:
        sched = self.schedules.pop((astronaut_id, exam_type), None)
        return sched is not None

    def list_schedules(self, astronaut_id: str | None = None) -> list[dict[str, Any]]:
        return [asdict(s) for s in self.schedules.values() if astronaut_id in (None, s.astronaut_id)]

    # ---------- collection ----------
    def run_exam(self, astronaut_id: str, exam_type: str) -> ExamResult:
        sm = self.state_manager
        state = sm.next_telemetry_reading(0.0, crew_id=astronaut_id)  # fresh sensor reading from the generator
        system_id = EXAM_SYSTEMS[exam_type]
        measurement = sm.trigger_measurement(system_id, crew_id=astronaut_id)
        state = measurement.state or state
        v = state.vitals
        payload = {
            "heart_rate_bpm": v.heart_rate_bpm,
            "bp_systolic": v.bp_systolic,
            "bp_diastolic": v.bp_diastolic,
            "temperature_c": v.temperature_c,
            "spo2_pct": v.spo2_pct,
            "sleep_hours": v.sleep_hours,
            "radiation_msv_h": v.radiation_msv_h,
            "ctb_reaction_time_ms": v.ctb_reaction_time_ms,
            "mood_score": v.mood_score,
            "pain_reports": [r.model_dump() for r in v.pain_reports],
            "reported_symptoms": list(v.reported_symptoms),
        }
        return ExamResult(
            astronaut_id=astronaut_id,
            exam_type=exam_type,
            collected_at=self._clock().isoformat(),
            system_id=system_id,
            reading_summary=measurement.reading_summary,
            telemetry_payload=payload,
        )

    def due(self) -> list[ExamSchedule]:
        now = self._clock()
        return [s for s in self.schedules.values() if s.active and datetime.fromisoformat(s.next_due_at) <= now]

    def mark_ran(self, sched: ExamSchedule) -> None:
        now = self._clock()
        sched.last_run_at = now.isoformat()
        sched.runs += 1
        sched.next_due_at = (now + timedelta(minutes=sched.interval_minutes)).isoformat()
