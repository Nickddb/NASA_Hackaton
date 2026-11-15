from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.schemas import (
    AdaptiveBaselineProfile,
    ClinicalFollowUpCase,
    CompleteReassessmentRequest,
    ConfirmationMeasurementRecord,
    ExecutedActionRecord,
    ExplainableAlert,
    RecordActionRequest,
    RecordConfirmationRequest,
    ScheduledReassessmentRecord,
)


class FollowUpCaseManager:
    """
    Pillar 3: Closed-Loop Clinical Follow-Up Cycle Manager.
    Ensures alerts never end at emission: tracks confirmation measurements,
    executed protocol actions, and scheduled reassessments until resolution or Earth escalation.
    """

    def __init__(self) -> None:
        self.cases: dict[str, ClinicalFollowUpCase] = {}

    def sync_alerts(
        self,
        alerts: list[ExplainableAlert],
        astronaut_id: str,
        astronaut_name: str,
        mission_day: int,
        stabilization_checklist: list[str],
    ) -> list[ClinicalFollowUpCase]:
        now_iso = datetime.now(timezone.utc).isoformat()

        for alert in alerts:
            # Find existing open case for same astronaut & syndrome
            existing = next(
                (
                    c
                    for c in self.cases.values()
                    if c.astronaut_id == astronaut_id
                    and c.syndrome_code == alert.syndrome_candidate
                    and c.status != "RESOLVED"
                ),
                None,
            )

            if existing is not None:
                existing.updated_at = now_iso
                existing.severity = alert.severity
                alert.followup_case_id = existing.case_id
                continue

            case_id = f"CASE-{astronaut_id[:4].upper()}-D{mission_day}-{uuid4().hex[:4].upper()}"
            alert.followup_case_id = case_id

            req_confirmations = list(alert.recommended_verification_steps[:2])
            if not req_confirmations:
                req_confirmations = [
                    "Perform resting confirmation measurement with CHeCS reference instrument after 15 minutes."
                ]

            default_reassessment = ScheduledReassessmentRecord(
                reassessment_id=f"REASSESS-{uuid4().hex[:5].upper()}",
                scheduled_for_offset_minutes=15 if alert.severity == "CRITICAL" else 30,
                target_system=alert.system_id,
                target_metrics=[s.get("metric", "heart_rate_bpm") for s in alert.originating_signals[:3]],
                protocol_reason=f"Mandatory closed-loop reassessment for {alert.title} (OCHMO-TB-044).",
                status="PENDING",
            )

            new_case = ClinicalFollowUpCase(
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
                reassessments_scheduled=[default_reassessment],
            )
            self.cases[case_id] = new_case

        return self.list_cases_for_astronaut(astronaut_id)

    def list_cases_for_astronaut(self, astronaut_id: str) -> list[ClinicalFollowUpCase]:
        items = [c for c in self.cases.values() if c.astronaut_id == astronaut_id]
        items.sort(key=lambda c: c.updated_at, reverse=True)
        return items

    def record_confirmation(
        self,
        case_id: str,
        req: RecordConfirmationRequest,
        adaptive_baseline: AdaptiveBaselineProfile,
    ) -> ClinicalFollowUpCase:
        if case_id not in self.cases:
            raise KeyError(f"Follow-up case not found: {case_id}")

        case = self.cases[case_id]
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check if measured value is still anomalous vs personal adaptive baseline (> 2.0 sigma)
        confirms = True
        unit = req.unit
        if req.metric in adaptive_baseline.metrics:
            m_base = adaptive_baseline.metrics[req.metric]
            unit = unit or m_base.unit
            ind_z = abs(req.measured_value - m_base.rolling_ewma_baseline) / max(m_base.rolling_mad_std, 1e-6)
            confirms = ind_z >= 2.0

        rec = ConfirmationMeasurementRecord(
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
        case.confirmations_recorded.append(rec)
        case.updated_at = now_iso

        if confirms:
            case.status = "CONFIRMED_ACTIVE_MONITORING"
        else:
            case.status = "DOWNGRADED_CONFOUNDER_OR_ARTIFACT"
            case.resolution_notes = (
                f"Confirmatory measurement ({req.metric}={req.measured_value} {unit} via {req.device_used}) "
                "returned within personal baseline band; initial alert attributed to transient context or sensor artifact."
            )

        return case

    def record_action(self, case_id: str, req: RecordActionRequest) -> ClinicalFollowUpCase:
        if case_id not in self.cases:
            raise KeyError(f"Follow-up case not found: {case_id}")

        case = self.cases[case_id]
        now_iso = datetime.now(timezone.utc).isoformat()

        act = ExecutedActionRecord(
            action_id=f"ACT-{uuid4().hex[:5].upper()}",
            executed_at=now_iso,
            performed_by=req.performed_by,
            protocol_reference=req.protocol_reference,
            action_description=req.action_description,
            outcome_note=req.outcome_note,
        )
        case.actions_executed.append(act)
        case.status = "ACTION_EXECUTED_AWAITING_REASSESSMENT"
        case.updated_at = now_iso

        reassess = ScheduledReassessmentRecord(
            reassessment_id=f"REASSESS-{uuid4().hex[:5].upper()}",
            scheduled_for_offset_minutes=req.schedule_reassessment_in_minutes,
            target_system=case.system_id,
            target_metrics=["heart_rate_bpm", "hrv_ms", "bp_systolic", "temperature_c"],
            protocol_reason=f"Post-intervention efficacy check after: {req.action_description[:60]}",
            status="PENDING",
        )
        case.reassessments_scheduled.append(reassess)
        return case

    def complete_reassessment(self, case_id: str, req: CompleteReassessmentRequest) -> ClinicalFollowUpCase:
        if case_id not in self.cases:
            raise KeyError(f"Follow-up case not found: {case_id}")

        case = self.cases[case_id]
        now_iso = datetime.now(timezone.utc).isoformat()

        target = next(
            (r for r in case.reassessments_scheduled if r.reassessment_id == req.reassessment_id),
            None,
        )
        if target is None and case.reassessments_scheduled:
            target = case.reassessments_scheduled[-1]

        if target is not None:
            target.status = "COMPLETED"
            target.completed_at = now_iso
            target.post_reassessment_summary = req.summary

        case.updated_at = now_iso
        if req.resolve_case:
            case.status = "RESOLVED"
            case.resolution_notes = req.summary
        else:
            case.status = "CONFIRMED_ACTIVE_MONITORING"

        return case
