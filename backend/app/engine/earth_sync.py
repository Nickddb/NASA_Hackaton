from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
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

logger = logging.getLogger(__name__)

# Runtime (mutable) state lives apart from the static datasets so it can be pointed at persistent
# storage on the vehicle and is never committed to git.
STATE_DIR = Path(
    os.environ.get("ASTRACARE_STATE_DIR", Path(__file__).resolve().parent.parent.parent / "data")
)
LEDGER_PATH = STATE_DIR / "local_mission_ledger.json"
FOLLOWUP_STORE_PATH = STATE_DIR / "followup_cases.json"

GENESIS_HASH = "0" * 64
# Fields that legitimately change after creation (sync handshake) and are therefore not hashed.
_UNHASHED_FIELDS = {"sync_status", "synchronized_at", "sha256_integrity_hash"}
MAX_PACKAGES = 50
MAX_AUDIT_EVENTS = 200


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_package_hash(pkg: EarthSyncPackage) -> str:
    """SHA-256 over the full canonical package content (+ previous hash => chain)."""
    body = pkg.model_dump(mode="json", exclude=_UNHASHED_FIELDS)
    return _sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def compute_audit_hash(entry: dict[str, Any]) -> str:
    body = {k: v for k, v in entry.items() if k != "entry_hash"}
    return _sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")))


class EarthSyncManager:
    """
    Pillar 5: Spacecraft-Earth Store-and-Forward Continuity Engine.

    Runs fully offline. Every clinical event goes into a hash-chained audit log and every telemetry/decision
    bundle for the ground Flight Surgeons is a hash-chained package, both persisted locally. Packages stay
    QUEUED_OFFLINE until a communication window is available, then are marked synchronized. Ground can
    re-verify the chain to detect any edit, deletion or reordering made after the fact.
    """

    def __init__(self, ledger_path: Path | None = LEDGER_PATH) -> None:
        self.ledger_path = ledger_path
        self.packages: list[EarthSyncPackage] = []
        self.audit_log: list[dict[str, Any]] = []
        self._load_local_ledger()

    # ---------- persistence ----------
    def _load_local_ledger(self) -> None:
        if self.ledger_path is None or not self.ledger_path.exists():
            return
        try:
            raw = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            self.audit_log = list(raw.get("audit_log", []))
            self.packages = [EarthSyncPackage(**p) for p in raw.get("packages", [])]
        except Exception:
            logger.exception("Could not load mission ledger %s; starting a new chain", self.ledger_path)
            self.packages = []
            self.audit_log = []

    def _persist_local_ledger(self) -> None:
        if self.ledger_path is None:
            return
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "audit_log": self.audit_log[-MAX_AUDIT_EVENTS:],
                "packages": [p.model_dump(mode="json") for p in self.packages[-MAX_PACKAGES:]],
            }
            tmp = self.ledger_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.ledger_path)  # atomic: a crash mid-write never corrupts the ledger
        except Exception:
            logger.exception("Could not persist mission ledger %s", self.ledger_path)

    # ---------- audit log ----------
    def record_audit_event(
        self,
        event_type: str,
        astronaut_id: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prev_hash = self.audit_log[-1].get("entry_hash", GENESIS_HASH) if self.audit_log else GENESIS_HASH
        entry: dict[str, Any] = {
            "event_id": f"AUD-{uuid4().hex[:6].upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "astronaut_id": astronaut_id,
            "summary": summary,
            "metadata": metadata or {},
            "prev_hash": prev_hash,
        }
        entry["entry_hash"] = compute_audit_hash(entry)
        self.audit_log.append(entry)
        self._persist_local_ledger()
        return entry

    # ---------- packages ----------
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
        prev_hash = self.packages[-1].sha256_integrity_hash if self.packages else GENESIS_HASH

        open_cases = [c for c in followup_cases if c.status != "RESOLVED"]
        overdue = sum(c.overdue_reassessments for c in open_cases)
        exec_summary = (
            f"[{crew_member} | Day {mission_day} | {environment_id}] "
            f"Personal Drift: {adaptive_baseline.personal_drift_score:.1f}% (Mahalanobis {adaptive_baseline.multivariate_mahalanobis_distance:.2f}) | "
            f"ML Classification: {ml_prediction.predicted_syndrome_label} ({ml_prediction.confidence_pct:.1f}% ± "
            f"{ml_prediction.uncertainty.total_uncertainty_pct:.1f}%) | "
            f"Open Follow-Up Cases: {len(open_cases)} ({overdue} overdue reassessments) | "
            f"One-Way Latency: {horizons_link.one_way_light_time_seconds:.0f}s."
        )

        pkg = EarthSyncPackage(
            package_id=pkg_id,
            created_at=now_iso,
            synchronized_at=None,
            sync_status="QUEUED_OFFLINE",
            sha256_integrity_hash="",
            previous_package_hash=prev_hash,
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
        # Freeze a snapshot: pydantic keeps references to the live case objects, which keep changing.
        pkg = pkg.model_copy(deep=True)
        pkg.sha256_integrity_hash = compute_package_hash(pkg)

        if (
            auto_sync_if_low_latency
            and horizons_link.comms_available
            and horizons_link.one_way_light_time_seconds <= 10.0
        ):
            pkg.sync_status = "SYNCHRONIZED_WITH_MCC_HOUSTON"
            pkg.synchronized_at = now_iso

        self.packages.append(pkg)
        self.record_audit_event(
            event_type="EARTH_SYNC_PACKAGE_CREATED",
            astronaut_id=astronaut_id,
            summary=f"Created telemetry & decision bundle {pkg_id} ({pkg.sync_status}, SHA256={pkg.sha256_integrity_hash[:12]}...).",
            metadata={"package_id": pkg_id, "status": pkg.sync_status},
        )
        return pkg

    def synchronize_queued_packages(self, comms_available: bool = True) -> list[EarthSyncPackage]:
        """Flush the store-and-forward queue. Without a link window, nothing leaves the vehicle."""
        if not comms_available:
            self.record_audit_event(
                event_type="MCC_SYNC_DEFERRED_NO_LINK",
                astronaut_id=self.packages[-1].astronaut_id if self.packages else "crew",
                summary=f"No communication window; {self.pending_count()} package(s) remain queued onboard.",
            )
            return self.packages[-10:]

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
        return self.packages[-10:]

    def pending_count(self) -> int:
        return sum(1 for p in self.packages if p.sync_status == "QUEUED_OFFLINE")

    # ---------- verification ----------
    def verify_integrity(self) -> dict[str, Any]:
        """Recompute both hash chains. Any edited, removed or reordered record breaks verification."""
        package_issues: list[str] = []
        expected_prev: str | None = None
        for pkg in self.packages:
            if pkg.previous_package_hash is None:
                package_issues.append(f"{pkg.package_id}: legacy package without chain link")
                expected_prev = pkg.sha256_integrity_hash
                continue
            if expected_prev is not None and pkg.previous_package_hash != expected_prev:
                package_issues.append(f"{pkg.package_id}: chain link does not match previous package")
            if compute_package_hash(pkg) != pkg.sha256_integrity_hash:
                package_issues.append(f"{pkg.package_id}: content hash mismatch (modified after creation)")
            expected_prev = pkg.sha256_integrity_hash

        audit_issues: list[str] = []
        prev: str | None = None
        for entry in self.audit_log:
            if "entry_hash" not in entry:
                continue  # legacy, unchained entry
            if prev is not None and entry.get("prev_hash") != prev:
                audit_issues.append(f"{entry['event_id']}: chain link does not match previous event")
            if compute_audit_hash(entry) != entry["entry_hash"]:
                audit_issues.append(f"{entry['event_id']}: content hash mismatch")
            prev = entry["entry_hash"]

        return {
            "verified": not package_issues and not audit_issues,
            "packages_checked": len(self.packages),
            "audit_events_checked": len(self.audit_log),
            "package_issues": package_issues,
            "audit_issues": audit_issues,
        }
