from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.models.schemas import (
    AdaptiveBaselineProfile,
    ClinicalFollowUpCase,
    CompleteReassessmentRequest,
    ConfirmationMeasurementRecord,
    EscalateCaseRequest,
    ExecutedActionRecord,
    ExplainableAlert,
    RecordActionRequest,
    RecordConfirmationRequest,
    ScheduledReassessmentRecord,
)

logger = logging.getLogger(__name__)

CLOSED_STATUSES = {"RESOLVED"}
CONFIRMATION_SIGMA = 2.0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FollowUpCaseManager:
    """
    Pillar 3: Closed-Loop Clinical Follow-Up Cycle Manager.

    An alert never ends at emission. Each alert opens (or refreshes) a case that tracks:
      confirmation measurements -> protocol actions executed -> scheduled reassessments with deadlines
    until it is RESOLVED, DOWNGRADED (artifact / benign context) or ESCALATED_TO_EARTH.

    Every read recomputes overdue reassessments and a plain-language list of pending items, so the crew
    and ground can tell whether a situation was followed up or is still open. Cases are persisted to disk
    (offline-first) so they survive a restart of the onboard computer.

    The engine never escalates or resolves on its own: those transitions require a human request.
    """

    def __init__(
        self,
        store_path: Path | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.store_path = store_path
        self._clock = clock
        self.cases: dict[str, ClinicalFollowUpCase] = {}
        self._load()

    # ---------- persistence ----------
    def _load(self) -> None:
        if self.store_path is None or not self.store_path.exists():
            return
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
            self.cases = {c["case_id"]: ClinicalFollowUpCase(**c) for c in raw.get("cases", [])}
        except Exception:  # corrupted store must not take the medical system down
            logger.exception("Could not load follow-up store %s; starting empty", self.store_path)
            self.cases = {}

    def _persist(self) -> None:
        if self.store_path is None:
            return
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": self._clock().isoformat(),
                "cases": [c.model_dump() for c in self.cases.values()],
            }
            tmp = self.store_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self.store_path)
        except Exception:
            logger.exception("Could not persist follow-up store %s", self.store_path)

    # ---------- helpers ----------
    def _get_open_case(self, case_id: str) -> ClinicalFollowUpCase:
        if case_id not in self.cases:
            raise KeyError(f"Follow-up case not found: {case_id}")
        case = self.cases[case_id]
        if case.status in CLOSED_STATUSES:
            raise ValueError(f"Case {case_id} is already {case.status}; open a new case instead.")
        return case

    def _schedule(
        self,
        offset_minutes: int,
        target_system: str,
        target_metrics: list[str],
        reason: str,
    ) -> ScheduledReassessmentRecord:
        now = self._clock()
        return ScheduledReassessmentRecord(
            reassessment_id=f"REASSESS-{uuid4().hex[:5].upper()}",
            scheduled_for_offset_minutes=offset_minutes,
            target_system=target_system,
            target_metrics=target_metrics,
            protocol_reason=reason,
            status="PENDING",
            scheduled_at=now.isoformat(),
            due_at=(now + timedelta(minutes=offset_minutes)).isoformat(),
        )

    def refresh_case(self, case: ClinicalFollowUpCase) -> ClinicalFollowUpCase:
        """Recompute overdue reassessments and the human-readable list of what is still owed."""
        now = self._clock()
        pending_due: list[datetime] = []
        overdue = 0
        for r in case.reassessments_scheduled:
            if r.status == "COMPLETED" or r.due_at is None:
                continue
            due = datetime.fromisoformat(r.due_at)
            if due <= now:
                r.status = "OVERDUE"
                overdue += 1
            pending_due.append(due)

        case.overdue_reassessments = overdue
        case.next_due_at = min(pending_due).isoformat() if pending_due else None

        items: list[str] = []
        if case.status in CLOSED_STATUSES:
            case.pending_items = []
            return case
        if not case.confirmations_recorded:
            items.append("Confirmation measurement not yet recorded.")
        if case.status == "CONFIRMED_ACTIVE_MONITORING" and not case.actions_executed:
            items.append("Anomaly confirmed but no protocol action recorded yet.")
        if overdue:
            items.append(f"{overdue} reassessment(s) overdue.")
        elif pending_due:
            items.append(f"Reassessment due at {case.next_due_at}.")
        if case.severity == "CRITICAL" and overdue and case.status != "ESCALATED_TO_EARTH":
            items.append("CRITICAL case with overdue reassessment: crew should consider Flight Surgeon escalation.")
        case.pending_items = items
        return case

    # ---------- lifecycle ----------
    def sync_alerts(
        self,
        alerts: list[ExplainableAlert],
        astronaut_id: str,
        astronaut_name: str,
        mission_day: int,
        stabilization_checklist: list[str],
    ) -> list[ClinicalFollowUpCase]:
        now_iso = self._clock().isoformat()
        changed = False

        for alert in alerts:
            existing = next(
                (
                    c
                    for c in self.cases.values()
                    if c.astronaut_id == astronaut_id
                    and c.syndrome_code == alert.syndrome_candidate
                    and c.status not in CLOSED_STATUSES
                ),
                None,
            )

            if existing is not None:
                alert.followup_case_id = existing.case_id
                if existing.severity != alert.severity:
                    existing.severity = alert.severity
                    existing.updated_at = now_iso
                    changed = True
                continue

            case_id = f"CASE-{astronaut_id[:4].upper()}-D{mission_day}-{uuid4().hex[:4].upper()}"
            alert.followup_case_id = case_id

            req_confirmations = list(alert.recommended_verification_steps[:2]) or [
                "Perform resting confirmation measurement with CHeCS reference instrument after 15 minutes."
            ]

            first_reassessment = self._schedule(
                offset_minutes=15 if alert.severity == "CRITICAL" else 30,
                target_system=alert.system_id,
                target_metrics=[s.get("metric", "heart_rate_bpm") for s in alert.originating_signals[:3]],
                reason=f"Mandatory closed-loop reassessment for {alert.title} (OCHMO-TB-044).",
            )

            self.cases[case_id] = ClinicalFollowUpCase(
                case_id=case_id,
                alert_id=alert.alert_id,
                astronaut_id=astronaut_id,
                astronaut_name=astronaut_name,
                mission_day=mission_day,
                system_id=alert.system_id,
                syndrome_code=alert.syndrome_candidate,
                title=alert.title,
                severity=alert.severity,
                status="OPEN_PENDING_CONFIRMATION",
                created_at=now_iso,
                updated_at=now_iso,
                required_confirmations=req_confirmations,
                recommended_protocol_actions=stabilization_checklist,
                reassessments_scheduled=[first_reassessment],
            )
            changed = True

        if changed:
            self._persist()
        return self.list_cases_for_astronaut(astronaut_id)

    def list_cases_for_astronaut(self, astronaut_id: str) -> list[ClinicalFollowUpCase]:
        items = [self.refresh_case(c) for c in self.cases.values() if c.astronaut_id == astronaut_id]
        items.sort(key=lambda c: c.updated_at, reverse=True)
        return items

    def record_confirmation(
        self,
        case_id: str,
        req: RecordConfirmationRequest,
        adaptive_baseline: AdaptiveBaselineProfile,
    ) -> ClinicalFollowUpCase:
        case = self._get_open_case(case_id)
        now_iso = self._clock().isoformat()

        # A confirmation "confirms" when it is still >= 2 sigma from the astronaut's personal adaptive baseline.
        confirms = True
        unit = req.unit
        if req.metric in adaptive_baseline.metrics:
            m_base = adaptive_baseline.metrics[req.metric]
            unit = unit or m_base.unit
            ind_z = abs(req.measured_value - m_base.rolling_ewma_baseline) / max(m_base.rolling_mad_std, 1e-6)
            confirms = ind_z >= CONFIRMATION_SIGMA

        case.confirmations_recorded.append(
            ConfirmationMeasurementRecord(
                confirmation_id=f"CONF-{uuid4().hex[:5].upper()}",
                recorded_at=now_iso,
                metric=req.metric,
                measured_value=round(req.measured_value, 2),
                unit=unit or "units",
                device_used=req.device_used,
                signal_quality_pct=round(req.signal_quality_pct, 1),
                confirms_anomaly=confirms,
                notes=req.notes,
            )
        )
        case.updated_at = now_iso

        if case.status != "ESCALATED_TO_EARTH":
            if confirms:
                case.status = "CONFIRMED_ACTIVE_MONITORING"
            else:
                case.status = "DOWNGRADED_CONFOUNDER_OR_ARTIFACT"
                case.resolution_notes = (
                    f"Confirmatory measurement ({req.metric}={req.measured_value} {unit} via {req.device_used}) "
                    "returned within personal baseline band; initial alert attributed to transient context or sensor artifact."
                )

        self._persist()
        return self.refresh_case(case)

    def record_action(self, case_id: str, req: RecordActionRequest) -> ClinicalFollowUpCase:
        case = self._get_open_case(case_id)
        now_iso = self._clock().isoformat()

        case.actions_executed.append(
            ExecutedActionRecord(
                action_id=f"ACT-{uuid4().hex[:5].upper()}",
                executed_at=now_iso,
                performed_by=req.performed_by,
                protocol_reference=req.protocol_reference,
                action_description=req.action_description,
                outcome_note=req.outcome_note,
            )
        )
        if case.status != "ESCALATED_TO_EARTH":
            case.status = "ACTION_EXECUTED_AWAITING_REASSESSMENT"
        case.updated_at = now_iso
        case.reassessments_scheduled.append(
            self._schedule(
                offset_minutes=req.schedule_reassessment_in_minutes,
                target_system=case.system_id,
                target_metrics=["heart_rate_bpm", "hrv_ms", "bp_systolic", "temperature_c"],
                reason=f"Post-intervention efficacy check after: {req.action_description[:60]}",
            )
        )
        self._persist()
        return self.refresh_case(case)

    def complete_reassessment(self, case_id: str, req: CompleteReassessmentRequest) -> ClinicalFollowUpCase:
        case = self._get_open_case(case_id)
        now_iso = self._clock().isoformat()

        target = next(
            (r for r in case.reassessments_scheduled if r.reassessment_id == req.reassessment_id),
            None,
        )
        if target is None:
            # Tolerate free-text callers (chat agent) by closing the oldest still-open reassessment.
            target = next((r for r in case.reassessments_scheduled if r.status != "COMPLETED"), None)

        if target is not None:
            target.status = "COMPLETED"
            target.completed_at = now_iso
            target.post_reassessment_summary = req.summary

        case.updated_at = now_iso
        if req.resolve_case:
            case.status = "RESOLVED"
            case.resolution_notes = req.summary
        elif case.status != "ESCALATED_TO_EARTH":
            case.status = "CONFIRMED_ACTIVE_MONITORING"

        self._persist()
        return self.refresh_case(case)

    def escalate(self, case_id: str, req: EscalateCaseRequest) -> ClinicalFollowUpCase:
        """Human-requested escalation to the Earth Flight Surgeon; the case stays open until resolved."""
        case = self._get_open_case(case_id)
        case.status = "ESCALATED_TO_EARTH"
        case.escalation_reason = f"{req.reason} (requested by {req.requested_by})"
        case.updated_at = self._clock().isoformat()
        self._persist()
        return self.refresh_case(case)
