"""
Multi-tool monitoring agent. Four chainable tools, each with structured input/output, that only orchestrate
services that already exist (generator, measurements, cross-diagnosis tree, ML, crew alerts, Earth packages,
psychological biofeedback):

  1. schedule_smartwatch_exam          -> collects (or schedules) a smartwatch exam, returns the telemetry payload
  2. analyze_telemetry_and_diagnose    -> payload + DONKI + personal baseline -> status / category / diagnosis
  3. trigger_central_alert             -> severe diagnosis -> crew alert + Earth package + audit log
  4. activate_psychological_stimuli    -> psychological cause -> Personal Crew Vault stimuli + BHP console

run_monitoring_cycle() chains them: the output of each step decides whether the next one runs.
The agent never prescribes treatment: alerts and stimuli are protocol actions that humans confirm.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app import config
from app.engine.cross_diagnosis import evaluate_cross_diagnosis
from app.engine.smartwatch_scheduler import EXAM_SYSTEMS, SmartwatchScheduler
from app.agent.tools import tool
from app.models.schemas import DispatchAlertRequest, SpaceWeatherEvent, SpaceWeatherSummary, ToolTraceItem, VitalSigns

ML_CATEGORY = {
    "nominal": "NONE",
    "behavioral_fatigue": "PSYCHOLOGICAL",
}
ROOT_SYSTEM = {  # which organ system a central alert targets
    "EXTERNAL_SPACE_WEATHER": "radiation",
    "ONBOARD_ENVIRONMENT": "respiratory",
    "PSYCHOLOGICAL_NEUROCOGNITIVE": "nervous_sleep",
}
VITAL_FIELDS = set(VitalSigns.model_fields)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _merge_space_weather(current: SpaceWeatherSummary | None, ctx: dict[str, Any], now: datetime) -> SpaceWeatherSummary:
    """Accept DONKI context as event lists ({"SEP": [...], "FLR": [...], "RBE": [...]}, or "events") or just
    counts (active_sep_count, ...). Counts without events become active events so the cause tree can use them."""
    base = current.model_dump() if current else {
        "source": "curated_local_fallback",
        "fetched_at": now.isoformat(),
        "alert_level": "NOMINAL",
        "active_flare_count": 0,
        "active_sep_count": 0,
        "recommended_dose_limit_msv_h": 0.5,
        "alara_instruction": "Keep exposure as low as reasonably achievable.",
    }
    ctx = dict(ctx)
    events = [SpaceWeatherEvent(**e) if isinstance(e, dict) else e for e in ctx.pop("events", [])]
    for etype in ("SEP", "FLR", "RBE", "CME", "GST"):
        for item in ctx.pop(etype, ctx.pop(etype.lower(), [])) or []:
            item = item if isinstance(item, dict) else {"class_or_intensity": str(item)}
            events.append(SpaceWeatherEvent(
                event_id=item.get("event_id", f"CTX-{etype}-{len(events) + 1}"),
                event_type=etype,
                begin_time=item.get("begin_time", now.isoformat()),
                class_or_intensity=item.get("class_or_intensity", item.get("class", "S1" if etype == "SEP" else "M1.0")),
                source_location=item.get("source_location", "external context"),
                note=item.get("note", "Provided in external_space_weather_context"),
                is_active=item.get("is_active", True),
            ))
    if not events:  # counts only
        for etype, key, cls in (("SEP", "active_sep_count", "S1"), ("RBE", "active_rbe_count", "RBE"), ("FLR", "active_flare_count", "M1.0")):
            for i in range(int(ctx.get(key, 0) or 0)):
                events.append(SpaceWeatherEvent(
                    event_id=f"CTX-{etype}-{i + 1}", event_type=etype, begin_time=now.isoformat(), class_or_intensity=cls,
                    source_location="external context", note="Count from external_space_weather_context", is_active=True,
                ))
    merged = {**base, **ctx}
    if events:
        merged["events"] = events + [e for e in (current.events if current else []) if e.event_id not in {x.event_id for x in events}]
        merged["active_sep_count"] = sum(e.event_type == "SEP" and e.is_active for e in merged["events"])
        merged["active_flare_count"] = sum(e.event_type == "FLR" and e.is_active for e in merged["events"])
        merged["active_rbe_count"] = sum(e.event_type == "RBE" and e.is_active for e in merged["events"])
    return SpaceWeatherSummary(**merged)


class MissionAgentTools:
    def __init__(self, state_manager, scheduler: SmartwatchScheduler | None = None, clock=_now) -> None:
        self.sm = state_manager
        self.scheduler = scheduler or SmartwatchScheduler(state_manager)
        self._clock = clock
        self._last_alert: dict[tuple[str, str], datetime] = {}
        self.last_reports: dict[str, dict[str, Any]] = {}  # chaining: latest diagnosis per astronaut

    # ------------------------------------------------------------------ tool 1
    def schedule_smartwatch_exam(
        self,
        astronaut_id: str,
        exam_type: str = "full_panel",
        interval_minutes: float | None = None,
        trigger_now: bool = True,
    ) -> dict[str, Any]:
        """Schedule a periodic smartwatch exam (interval_minutes) and/or collect one now (trigger_now).
        exam_type: full_panel, cardio, cognitive_ctb, dosimetry, respiratory, metabolic."""
        out = self.scheduler.schedule(astronaut_id, exam_type, interval_minutes, trigger_now)
        result = out.get("result")
        return {
            "tool": "schedule_smartwatch_exam",
            "astronaut_id": astronaut_id,
            "exam_type": exam_type,
            "schedule": out.get("schedule"),
            "collected": result is not None,
            "reading_summary": result["reading_summary"] if result else None,
            "telemetry_payload": result["telemetry_payload"] if result else None,
            "next_tool": "analyze_telemetry_and_diagnose" if result else None,
        }

    # ------------------------------------------------------------------ tool 2
    def analyze_telemetry_and_diagnose(
        self,
        astronaut_id: str,
        telemetry_payload: dict[str, Any] | None = None,
        external_space_weather_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest a telemetry payload, cross it with NASA DONKI space weather and the astronaut's personal
        baseline, and classify the cause: NONE, PHYSICAL_ENVIRONMENTAL or PSYCHOLOGICAL (only when no physical
        or external cause explains a behavioural / cognitive change)."""
        sm = self.sm
        if astronaut_id not in sm.crew_records:
            raise KeyError(f"Unknown astronaut_id: {astronaut_id}")
        member = sm._member(astronaut_id)

        if telemetry_payload:  # ingestion: the reading becomes the astronaut's current vitals
            update = {k: v for k, v in telemetry_payload.items() if k in VITAL_FIELDS and k != "pain_reports"}
            if update:
                member.vitals = VitalSigns(**{**member.vitals.model_dump(), **update})

        state = sm.get_state(crew_id=astronaut_id)
        space_weather = state.space_weather
        if external_space_weather_context:
            space_weather = _merge_space_weather(space_weather, external_space_weather_context, self._clock())
        cross = state.cross_diagnosis
        if external_space_weather_context or cross is None:
            cross = evaluate_cross_diagnosis(
                state.vitals, state.mission_context, space_weather, state.contextual_intelligence, state.clinical_evaluation
            )
        ml = state.ml_prediction
        clinical = state.clinical_evaluation

        # status: rules' worst system, raised to CRITICAL when the cause tree asks for immediate escalation
        status = {"NOMINAL": "NORMAL", "ATTENTION": "WARNING"}.get(clinical.overall_status, clinical.overall_status)
        if cross.earth_priority == "IMMEDIATE":
            status = "CRITICAL"
        elif status == "NORMAL" and cross.layer > 0 and cross.root_cause != "CONTEXTUAL_BENIGN":
            status = "WARNING"

        if cross.root_cause == "PSYCHOLOGICAL_NEUROCOGNITIVE":
            category = "PSYCHOLOGICAL"
        elif status == "NORMAL" or cross.root_cause == "NOMINAL":
            category = "NONE"
        else:
            category = "PHYSICAL_ENVIRONMENTAL"

        # confidence: deterministic evidence (cause tree) + ML agreement, discounted by sensor uncertainty
        supporting = [e for e in cross.evidence if e.supports]
        rule_conf = min(0.85, 0.5 + 0.1 * len(supporting)) if category != "NONE" else ml.syndrome_probabilities.get("nominal", 50) / 100
        ml_category = ML_CATEGORY.get(ml.predicted_syndrome, "PHYSICAL_ENVIRONMENTAL")
        agrees = ml_category == category
        conf = (rule_conf + ml.confidence_pct / 100) / 2 if agrees else rule_conf * 0.8
        conf *= 1 - min(ml.uncertainty.total_uncertainty_pct, 60) / 200
        diagnosis = cross.title if category != "NONE" else "Within personal baseline and NASA in-flight limits"

        next_tools = []
        severe = status == "CRITICAL" or (status == "WARNING" and cross.earth_priority in ("PRIORITY", "IMMEDIATE"))
        if severe:
            next_tools.append("trigger_central_alert")
        if category == "PSYCHOLOGICAL":
            next_tools.append("activate_psychological_stimuli")

        report = {
            "tool": "analyze_telemetry_and_diagnose",
            "astronaut_id": astronaut_id,
            "status": status,
            "category": category,
            "probable_diagnosis": diagnosis,
            "confidence_score": round(conf, 2),
            "confidence_basis": (
                f"cause tree ({len(supporting)} supporting signals) "
                + ("agrees" if agrees else "disagrees")
                + f" with ML ({ml.predicted_syndrome}, {ml.confidence_pct:.0f}%), sensor uncertainty ±{ml.uncertainty.total_uncertainty_pct:.0f}%"
            ),
            "root_cause": cross.root_cause,
            "cause_layer": cross.layer,
            "earth_priority": cross.earth_priority,
            "evidence": [f"{e.signal}: {e.value} ({e.rule})" for e in supporting],
            "ruled_out": [f"{e.signal}: {e.value}" for e in cross.evidence if not e.supports],
            "recommended_actions": cross.recommended_actions,
            "space_weather": {
                "status": space_weather.status_label if space_weather else "unknown",
                "alert_level": space_weather.alert_level if space_weather else "NOMINAL",
                "source": space_weather.source if space_weather else "none",
            },
            "personal_baseline": {
                "within": state.within_personal_baseline,
                "deviations": list(state.baseline_deviations or []),
            },
            "ml": {
                "syndrome": ml.predicted_syndrome,
                "confidence_pct": ml.confidence_pct,
                "uncertainty_pct": ml.uncertainty.total_uncertainty_pct,
                "pain_summary": ml.pain_summary,
            },
            "psych_escalation": bool(cross.psych_protocol and cross.psych_protocol.escalate_to_earth),
            "next_tools": next_tools,
        }
        self.last_reports[astronaut_id] = report
        return report

    # ------------------------------------------------------------------ tool 3
    def trigger_central_alert(
        self,
        astronaut_id: str,
        diagnosis_report: dict[str, Any],
        severity_level: str | None = None,
        telemetry_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Notify the Earth Flight Surgeons and the crew of a severe diagnosis (CRITICAL, or WARNING with
        PRIORITY/IMMEDIATE escalation): crew alert, store-and-forward package, audit log entry."""
        severity = (severity_level or diagnosis_report.get("status") or "WARNING").upper()
        if severity == "NORMAL":
            severity = "NOMINAL"
        grave = severity == "CRITICAL" or (
            severity == "WARNING" and diagnosis_report.get("earth_priority") in ("PRIORITY", "IMMEDIATE")
        )
        diagnosis = diagnosis_report.get("probable_diagnosis", "Unspecified anomaly")
        base = {"tool": "trigger_central_alert", "astronaut_id": astronaut_id, "severity": severity, "diagnosis": diagnosis}
        if not grave:
            return {**base, "dispatched": False, "reason": "Below the central-alert threshold (CRITICAL or escalated WARNING)."}

        now = self._clock()
        key = (astronaut_id, diagnosis)
        last = self._last_alert.get(key)
        if last and now - last < timedelta(minutes=config.ALERT_COOLDOWN_MIN):
            return {**base, "dispatched": False, "reason": f"Same alert already sent {int((now - last).total_seconds() // 60)} min ago."}

        sm = self.sm
        state = sm.dispatch_alert(
            astronaut_id,
            DispatchAlertRequest(
                severity=severity if severity in ("WARNING", "CRITICAL") else "WARNING",
                syndrome_code=str(diagnosis_report.get("root_cause", "agent_alert")).lower(),
                title=diagnosis,
                summary=(
                    f"{diagnosis_report.get('category', '')} · confidence {diagnosis_report.get('confidence_score', '?')} · "
                    + "; ".join(diagnosis_report.get("evidence", [])[:3])
                ),
                target_system_id=ROOT_SYSTEM.get(diagnosis_report.get("root_cause"), "cardiovascular"),
                recommended_actions=list(diagnosis_report.get("recommended_actions", []))[:4],
                simulate_vitals_drift=False,
            ),
        )
        package = sm.create_earth_sync_package(crew_id=astronaut_id)
        synced = False
        if state.horizons_link and state.horizons_link.comms_available:
            sm.synchronize_with_earth()
            synced = True
        sm.earth_sync.record_audit_event(
            event_type="AGENT_CENTRAL_ALERT",
            astronaut_id=astronaut_id,
            summary=f"{severity}: {diagnosis}",
            metadata={"package_id": package.package_id, "snapshot": telemetry_snapshot or {}},
        )
        if diagnosis_report.get("psych_escalation"):
            sm.escalate_psych_priority(f"Agent: {diagnosis}", crew_id=astronaut_id)
        self._last_alert[key] = now
        return {
            **base,
            "dispatched": True,
            "crew_alert_id": state.active_alert.alert_id if state.active_alert else None,
            "earth_package_id": package.package_id,
            "synchronized_now": synced,
            "one_way_latency_s": state.one_way_latency_seconds,
            "recipients": ["Earth Flight Surgeon (MCC)", "Crew Medical Officer", "Crew Hub"],
        }

    # ------------------------------------------------------------------ tool 4
    def activate_psychological_stimuli(
        self, astronaut_id: str, diagnosis_report: dict[str, Any] | None = None, reason: str = "", force: bool = False
    ) -> dict[str, Any]:
        """Start the psychophysiological countermeasure (Personal Crew Vault: family video, friends audio,
        nature sounds, interest-based games) and notify the Behavioral Health console. Runs only for a
        psychological cause unless force=true (explicit crew request)."""
        category = (diagnosis_report or {}).get("category")
        base = {"tool": "activate_psychological_stimuli", "astronaut_id": astronaut_id}
        if category != "PSYCHOLOGICAL" and not force:
            return {**base, "activated": False, "reason": "Cause is not psychological; stimuli withheld to avoid masking a physical problem."}
        sm = self.sm
        previous = sm.active_crew_id
        sm.select_crew_member(astronaut_id)
        try:
            record = sm.trigger_psychological_biofeedback(
                reason or (diagnosis_report or {}).get("probable_diagnosis", "Agent: psychological cause")
            )
        finally:
            if previous != astronaut_id and previous in sm.crew_records:
                sm.select_crew_member(previous)
        return {
            **base,
            "activated": True,
            "central_alert_id": record.central_alert_id,
            "diagnosis": record.primary_psych_label,
            "score_0_100": record.weighted_score_0_100,
            "stimuli": [{"title": s.title, "category": s.category, "duration_min": s.duration_min} for s in record.dispatched_stimuli],
            "reassessment_in_min": record.reassessment_scheduled_in_minutes,
            "recipient": record.recipient_station,
        }

    # ------------------------------------------------------------------ chain
    def run_monitoring_cycle(
        self, astronaut_id: str, exam_type: str = "full_panel", collect: bool = True
    ) -> dict[str, Any]:
        """exam -> analysis -> (central alert) -> (psychological stimuli). Each step's output gates the next."""
        steps: list[dict[str, Any]] = []
        payload = None
        if collect:
            exam = self.schedule_smartwatch_exam(astronaut_id, exam_type, trigger_now=True)
            steps.append(exam)
            payload = exam["telemetry_payload"]
        report = self.analyze_telemetry_and_diagnose(astronaut_id, payload)
        steps.append(report)
        if "trigger_central_alert" in report["next_tools"]:
            steps.append(self.trigger_central_alert(astronaut_id, report, report["status"], payload))
        if "activate_psychological_stimuli" in report["next_tools"]:
            steps.append(self.activate_psychological_stimuli(astronaut_id, report))
        return {
            "astronaut_id": astronaut_id,
            "status": report["status"],
            "category": report["category"],
            "probable_diagnosis": report["probable_diagnosis"],
            "confidence_score": report["confidence_score"],
            "chain": [s["tool"] for s in steps],
            "steps": steps,
        }

    def run_due_schedules(self) -> list[dict[str, Any]]:
        """Background loop entry: run every due scheduled exam through the full chain."""
        results = []
        for sched in self.scheduler.due():
            self.scheduler.mark_ran(sched)
            results.append(self.run_monitoring_cycle(sched.astronaut_id, sched.exam_type))
        return results


TOOL_NAMES = ("schedule_smartwatch_exam", "analyze_telemetry_and_diagnose", "trigger_central_alert", "activate_psychological_stimuli")
EXAM_TYPES = tuple(EXAM_SYSTEMS)


# ---------------------------------------------------------------------- LLM / chat registration
def _parse_json(text: str) -> dict[str, Any] | None:
    if not text or not str(text).strip():
        return None
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, default=str)


def build_mission_tools(agent: MissionAgentTools, trace_log: list[ToolTraceItem]) -> list[Any]:
    """Wrap the four tools (+ the full cycle) for the chat/LLM. Payloads travel as JSON strings so every
    provider's function-calling schema accepts them; the latest diagnosis per astronaut is kept server-side,
    so trigger_central_alert / activate_psychological_stimuli chain from it without re-sending it."""

    def trace(name: str, status: str, summary: str, rule: str = "") -> None:
        status = {"NORMAL": "OK", "NOMINAL": "OK"}.get(status, status)
        trace_log.append(
            ToolTraceItem(
                tool_name=name,
                status=status if status in ("OK", "WARNING", "CRITICAL") else "OK",
                summary=summary,
                rule_or_score=rule,
            )
        )

    def guard(name: str, fn):
        try:
            return fn()
        except (KeyError, ValueError) as exc:
            trace(name, "WARNING", f"Rejected: {exc}")
            return {"tool": name, "error": str(exc)}

    @tool
    def schedule_smartwatch_exam(
        astronaut_id: str, exam_type: str = "full_panel", interval_minutes: float = 0.0, trigger_now: bool = True
    ) -> str:
        """Schedule a periodic smartwatch exam and/or collect one now for one crew member.
        astronaut_id: elena_vance, lucas_ferreira, kenji_sato, amara_okafor or liam_soren.
        exam_type: full_panel, cardio, cognitive_ctb, dosimetry, respiratory or metabolic.
        interval_minutes: repeat period (0 = no schedule). trigger_now: collect a reading immediately.
        Returns the collected telemetry_payload; next call analyze_telemetry_and_diagnose."""
        out = guard(
            "schedule_smartwatch_exam",
            lambda: agent.schedule_smartwatch_exam(astronaut_id, exam_type, interval_minutes or None, trigger_now),
        )
        if "error" not in out:
            every = f" every {out['schedule']['interval_minutes']:g} min" if out.get("schedule") else ""
            trace("schedule_smartwatch_exam", "OK", f"{astronaut_id}: {exam_type}{every}" + (" · collected now" if out["collected"] else ""))
        return _dump(out)

    @tool
    def analyze_telemetry_and_diagnose(astronaut_id: str, telemetry_json: str = "", space_weather_json: str = "") -> str:
        """Diagnose one crew member: crosses telemetry with the personal baseline, NASA limits and NASA DONKI space
        weather, and classifies the cause as NONE, PHYSICAL_ENVIRONMENTAL or PSYCHOLOGICAL (psychological only when no
        physical or external cause explains a behavioural change). telemetry_json: optional JSON object with vitals
        (heart_rate_bpm, bp_systolic, temperature_c, sleep_hours, radiation_msv_h, ctb_reaction_time_ms, mood_score...);
        empty = latest reading. space_weather_json: optional JSON, e.g. {"SEP": [{"class": "S2"}], "alert_level": "WARNING"};
        empty = live DONKI. Returns status, category, probable_diagnosis, confidence_score and next_tools."""
        out = guard(
            "analyze_telemetry_and_diagnose",
            lambda: agent.analyze_telemetry_and_diagnose(astronaut_id, _parse_json(telemetry_json), _parse_json(space_weather_json)),
        )
        if "error" not in out:
            trace(
                "analyze_telemetry_and_diagnose",
                out["status"],
                f"{astronaut_id}: {out['category']} — {out['probable_diagnosis']}",
                f"confidence {out['confidence_score']}",
            )
        return _dump(out)

    @tool
    def trigger_central_alert(astronaut_id: str, severity_level: str = "") -> str:
        """Send the latest diagnosis of this crew member to the Earth Flight Surgeons and the crew (crew alert,
        store-and-forward package, mission audit log). Only dispatches CRITICAL, or WARNING with PRIORITY/IMMEDIATE
        escalation; repeated alerts are suppressed for a cooldown. Call analyze_telemetry_and_diagnose first."""

        def run():
            report = agent.last_reports.get(astronaut_id) or agent.analyze_telemetry_and_diagnose(astronaut_id)
            return agent.trigger_central_alert(astronaut_id, report, severity_level or None)

        out = guard("trigger_central_alert", run)
        if "error" not in out:
            trace(
                "trigger_central_alert",
                out["severity"] if out["dispatched"] else "OK",
                f"{astronaut_id}: " + (f"sent ({out['earth_package_id']})" if out["dispatched"] else out["reason"]),
            )
        return _dump(out)

    @tool
    def activate_psychological_stimuli(astronaut_id: str, reason: str = "", crew_requested: bool = False) -> str:
        """Start the psychological countermeasure for this crew member (Personal Crew Vault: family video, friends
        audio, nature sounds, interest-based games) and notify the Behavioral Health console. Runs only when
        the latest diagnosis is PSYCHOLOGICAL, or when the astronaut asks for it (crew_requested=true)."""
        out = guard(
            "activate_psychological_stimuli",
            lambda: agent.activate_psychological_stimuli(
                astronaut_id, agent.last_reports.get(astronaut_id), reason, force=crew_requested
            ),
        )
        if "error" not in out:
            trace(
                "activate_psychological_stimuli",
                "WARNING" if out["activated"] else "OK",
                f"{astronaut_id}: "
                + (f"{len(out['stimuli'])} stimuli ({out['central_alert_id']})" if out["activated"] else out["reason"]),
            )
        return _dump(out)

    @tool
    def run_monitoring_cycle(astronaut_id: str, exam_type: str = "full_panel") -> str:
        """Full chain for one crew member: collect a smartwatch exam -> diagnose -> central alert if severe ->
        psychological stimuli if the cause is psychological. Use it for 'check X now' style requests."""
        out = guard("run_monitoring_cycle", lambda: agent.run_monitoring_cycle(astronaut_id, exam_type))
        if "error" not in out:
            trace(
                "run_monitoring_cycle",
                out["status"],
                f"{astronaut_id}: {' -> '.join(out['chain'])}",
                f"{out['category']} · confidence {out['confidence_score']}",
            )
        return _dump(out)

    return [
        schedule_smartwatch_exam,
        analyze_telemetry_and_diagnose,
        trigger_central_alert,
        activate_psychological_stimuli,
        run_monitoring_cycle,
    ]
