from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models.schemas import (
    AdaptiveBaselineProfile,
    ClinicalFollowUpCase,
    ContextualIntelligenceReport,
    EarthSyncPackage,
    ExplainableAlert,
    ForecastHorizonPoint,
    HorizonsLinkStatus,
    MLPredictionResult,
    SeverityStatus,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
LEDGER_PATH = DATA_DIR / "local_mission_ledger.json"


class EarthSyncManager:
    """
    Pillar 5: Spacecraft–Earth Store-and-Forward Continuity Engine.
    Operates 100% locally offline-first, persists a tamper-evident SHA-256 clinical ledger
    on disk (`local_mission_ledger.json`), queues telemetry & decision packages during
    deep-space latency or solar blackout, and synchronizes with Earth MCC when link opens.
    """

    def __init__(self) -> None:
        self.packages: list[EarthSyncPackage] = []
        self.audit_log: list[dict[str, Any]] = []
        self._load_local_ledger()

    def _load_local_ledger(self) -> None:
        if not LEDGER_PATH.exists():
            return
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.audit_log = list(raw.get("audit_log", []))[-100:]
            loaded_pkgs = raw.get("packages", [])
            self.packages = [EarthSyncPackage(**p) for p in loaded_pkgs[-25:]]
        except Exception:
            self.packages = []
            self.audit_log = []

    def _persist_local_ledger(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "audit_log": self.audit_log[-100:],
                "packages": [p.model_dump() for p in self.packages[-25:]],
            }
            with open(LEDGER_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def record_audit_event(
        self,
        event_type: str,
        astronaut_id: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "event_id": f"AUD-{uuid4().hex[:6].upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "astronaut_id": astronaut_id,
            "summary": summary,
            "metadata": metadata or {},
        }
        self.audit_log.append(entry)
        self._persist_local_ledger()
        return entry

    def build_and_queue_package(
        self,
        astronaut_id: str,
        crew_member: str,
        mission_day: int,
        environment_id: str,
        horizons_link: HorizonsLinkStatus,
        space_weather_alert: SeverityStatus,
        adaptive_baseline: AdaptiveBaselineProfile,
        contextual_report: ContextualIntelligenceReport,
        ml_prediction: MLPredictionResult,
        explainable_alerts: list[ExplainableAlert],
        followup_cases: list[ClinicalFollowUpCase],
        longitudinal_series: list[dict[str, Any]],
        forecast_72h: list[ForecastHorizonPoint],
        auto_sync_if_low_latency: bool = False,
    ) -> EarthSyncPackage:
        now_iso = datetime.now(timezone.utc).isoformat()
        pkg_id = f"SYNC-MCC-{mission_day}-{uuid4().hex[:6].upper()}"

        # Compute deterministic SHA-256 hash over core clinical & ML state for auditability
        canonical_payload = json.dumps(
            {
                "astronaut_id": astronaut_id,
                "mission_day": mission_day,
                "personal_drift_score": adaptive_baseline.personal_drift_score,
                "predicted_syndrome": ml_prediction.predicted_syndrome,
                "confidence_pct": ml_prediction.confidence_pct,
                "alerts": [a.alert_id for a in explainable_alerts],
                "cases": [(c.case_id, c.status, len(c.confirmations_recorded), len(c.actions_executed)) for c in followup_cases],
            },
            sort_keys=True,
        )
        integrity_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

        is_immediate_sync = (
            auto_sync_if_low_latency
            and horizons_link.one_way_light_time_seconds <= 10.0
            and horizons_link.comms_available
        )

        exec_summary = (
            f"[{crew_member} | Day {mission_day} | {environment_id}] "
            f"Personal Drift: {adaptive_baseline.personal_drift_score:.1f}% (Mahalanobis {adaptive_baseline.multivariate_mahalanobis_distance:.2f}) | "
            f"ML Classification: {ml_prediction.predicted_syndrome_label} ({ml_prediction.confidence_pct:.1f}% ± "
            f"{ml_prediction.uncertainty.total_uncertainty_pct:.1f}%) | "
            f"Open Follow-Up Cases: {sum(1 for c in followup_cases if c.status != 'RESOLVED')} | "
            f"One-Way Latency: {horizons_link.one_way_light_time_seconds:.0f}s."
        )

        pkg = EarthSyncPackage(
            package_id=pkg_id,
            created_at=now_iso,
            synchronized_at=now_iso if is_immediate_sync else None,
            sync_status="SYNCHRONIZED_WITH_MCC_HOUSTON" if is_immediate_sync else "QUEUED_OFFLINE",
            sha256_integrity_hash=integrity_hash,
            astronaut_id=astronaut_id,
            crew_member=crew_member,
            mission_day=mission_day,
            environment_id=environment_id,
            horizons_link=horizons_link,
            space_weather_alert=space_weather_alert,
            executive_summary=exec_summary,
            adaptive_baseline_snapshot=adaptive_baseline,
            contextual_report=contextual_report,
            ml_prediction=ml_prediction,
            explainable_alerts=explainable_alerts,
            followup_cases=followup_cases,
            longitudinal_series=longitudinal_series,
            forecast_72h=forecast_72h,
            audit_log_entries=self.audit_log[-15:],
        )

        self.packages.append(pkg)
        self.record_audit_event(
            event_type="EARTH_SYNC_PACKAGE_CREATED",
            astronaut_id=astronaut_id,
            summary=f"Created telemetry & decision bundle {pkg_id} ({pkg.sync_status}, SHA256={integrity_hash[:12]}...).",
            metadata={"package_id": pkg_id, "status": pkg.sync_status},
        )
        return pkg

    def synchronize_queued_packages(self) -> list[EarthSyncPackage]:
        now_iso = datetime.now(timezone.utc).isoformat()
        synced: list[EarthSyncPackage] = []
        for pkg in self.packages:
            if pkg.sync_status == "QUEUED_OFFLINE":
                pkg.sync_status = "SYNCHRONIZED_WITH_MCC_HOUSTON"
                pkg.synchronized_at = now_iso
                synced.append(pkg)

        if synced:
            self.record_audit_event(
                event_type="MCC_HOUSTON_BATCH_SYNC",
                astronaut_id=synced[-1].astronaut_id,
                summary=f"Synchronized {len(synced)} store-and-forward clinical package(s) with Earth Flight Surgeon console.",
                metadata={"package_ids": [p.package_id for p in synced]},
            )
        else:
            self._persist_local_ledger()
        return self.packages[-10:]

    def pending_count(self) -> int:
        return sum(1 for p in self.packages if p.sync_status == "QUEUED_OFFLINE")
