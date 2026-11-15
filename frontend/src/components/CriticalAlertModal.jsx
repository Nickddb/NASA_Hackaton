import { useEffect, useState } from "react";
import { ArrowRight, BellRing, CheckCircle2, ShieldAlert, X } from "lucide-react";
import { getEnvironmentStatuses, getPsychologicalReadiness, getVitalStatuses } from "../services/api";

export default function CriticalAlertModal({
  alerts = [],
  viewMode = "control",
  busyAction = false,
  onInspectCrew,
  onAcknowledge,
  onDismiss,
  onDismissAll,
}) {
  const [selectedIdx, setSelectedIdx] = useState(0);

  useEffect(() => {
    if (selectedIdx >= alerts.length && alerts.length > 0) {
      setSelectedIdx(0);
    }
  }, [alerts.length, selectedIdx]);

  if (!alerts.length) return null;

  const current = alerts[selectedIdx] || alerts[0];
  const member = current.member;
  const vitalSt = getVitalStatuses(member.vitals, member.personal_baseline);
  const envEval = getEnvironmentStatuses(member.mission_context, member.vitals, member.personal_baseline);
  const psych = getPsychologicalReadiness(member.vitals, member.personal_baseline, {
    environmentId: member.environment_id,
    oneWayLatencySeconds: member.one_way_latency_seconds,
  });

  const alteredFlags = [];
  if (vitalSt.hr !== "NOMINAL") {
    alteredFlags.push({ label: `HR ${Math.round(member.vitals.heart_rate_bpm)}`, status: vitalSt.hr });
  }
  if (vitalSt.bp !== "NOMINAL") {
    alteredFlags.push({
      label: `BP ${Math.round(member.vitals.bp_systolic)}/${Math.round(member.vitals.bp_diastolic)}`,
      status: vitalSt.bp,
    });
  }
  if (vitalSt.temp !== "NOMINAL") {
    alteredFlags.push({ label: `${member.vitals.temperature_c.toFixed(1)}°C`, status: vitalSt.temp });
  }
  if (vitalSt.spo2 !== "NOMINAL") {
    alteredFlags.push({ label: `SpO₂ ${Math.round(member.vitals.spo2_pct)}%`, status: vitalSt.spo2 });
  }
  for (const sensor of envEval.list) {
    if (sensor.status !== "NOMINAL") {
      alteredFlags.push({ label: `${sensor.shortLabel} ${sensor.shortValue}`, status: sensor.status });
    }
  }
  if (psych.status !== "NOMINAL") {
    alteredFlags.push({ label: `Psych ${psych.score}/100`, status: psych.status });
  }

  return (
    <aside
      role="alertdialog"
      aria-live="assertive"
      aria-label="Critical Mission Medical Alert"
      className="fixed right-4 top-4 z-50 w-[min(450px,calc(100vw-2rem))] overflow-hidden rounded-2xl border-2 border-red-500/90 bg-gradient-to-br from-[#2B0814]/95 via-[#101832]/95 to-[#061428]/95 p-4 text-white shadow-[0_12px_45px_rgba(239,68,68,0.5)] backdrop-blur-xl sm:right-6 sm:top-5"
    >
      {/* Compact Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2.5">
          <div className="relative mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-red-600 text-white shadow-[0_0_16px_rgba(239,68,68,0.85)]">
            <span className="absolute -inset-1 animate-ping rounded-xl bg-red-500 opacity-35" />
            <ShieldAlert className="relative h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="inline-flex items-center gap-1 rounded-full bg-red-600 px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest text-white">
                <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
                Critical Alert
              </span>
              <span className="rounded-full border border-red-400/50 bg-red-950/75 px-2 py-0.5 font-mono text-[9px] font-bold text-red-200">
                {member.callsign} • {viewMode === "control" ? "Control" : "Crew"}
              </span>
            </div>
            <h2 className="mt-1 truncate text-sm font-bold text-white">
              {member.name}
            </h2>
            <p className="truncate text-[11px] text-slate-300">{member.location_module}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onDismiss(current.key)}
          title="Close pop-up (alert lights stay flashing until stabilized & verified)"
          className="rounded-lg border border-white/15 bg-white/5 p-1.5 text-slate-300 transition hover:bg-white/10 hover:text-white cursor-pointer"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Multi-alert tabs if needed */}
      {alerts.length > 1 && (
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-red-200">
            {alerts.length} Critical:
          </span>
          {alerts.map((item, idx) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setSelectedIdx(idx)}
              className={`rounded-full px-2 py-0.5 font-mono text-[10px] font-bold transition cursor-pointer ${
                idx === selectedIdx
                  ? "bg-red-500 text-white"
                  : "border border-red-400/40 bg-red-950/60 text-red-200 hover:bg-red-900/60"
              }`}
            >
              {item.member.callsign}
            </button>
          ))}
        </div>
      )}

      {/* Alert Message */}
      <div className="mt-2.5 rounded-xl border border-red-400/45 bg-red-950/55 px-3 py-2">
        <div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-red-200">
          <BellRing className="h-3 w-3" />
          {member.active_alert?.origin_type === "MISSION_CONTROL_DISPATCH" ||
          member.active_alert?.source === "MISSION_CONTROL"
            ? "Mission Control Alert"
            : "Auto-Triage Alert"}
        </div>
        <p className="mt-0.5 text-xs font-medium leading-snug text-white">
          {member.active_alert?.message || member.primary_diagnosis || "Critical anomaly detected"}
        </p>
      </div>

      {/* Compact Altered Indicators */}
      {alteredFlags.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {alteredFlags.map((flag, i) => (
            <span
              key={`${flag.label}-${i}`}
              className={`inline-flex items-center gap-1 rounded-lg border px-2 py-0.5 font-mono text-[10px] font-bold ${
                flag.status === "CRITICAL"
                  ? "border-red-400/80 bg-red-950/80 text-red-200"
                  : "border-amber-400/75 bg-amber-950/75 text-amber-200"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  flag.status === "CRITICAL" ? "bg-red-400 animate-ping" : "bg-amber-400 animate-pulse"
                }`}
              />
              {flag.label}
            </span>
          ))}
        </div>
      )}

      {/* Compact Action Footer */}
      <div className="mt-3 flex flex-wrap items-center justify-end gap-2 border-t border-white/10 pt-2.5">
        {alerts.length > 1 && (
          <button
            type="button"
            onClick={onDismissAll}
            className="mr-auto text-[11px] font-medium text-slate-300 underline-offset-2 hover:text-white hover:underline cursor-pointer"
          >
            Dismiss all ({alerts.length})
          </button>
        )}
        <button
          type="button"
          onClick={() => onDismiss(current.key)}
          className="min-h-[32px] rounded-lg border border-white/20 bg-slate-900/80 px-3 text-[11px] font-semibold text-slate-100 transition hover:bg-slate-800 cursor-pointer"
        >
          Dismiss
        </button>
        {!member.active_alert?.acknowledged_by_crew && (
          <button
            type="button"
            disabled={busyAction}
            onClick={() => onAcknowledge(member.crew_id, current.key)}
            className="flex min-h-[32px] items-center gap-1 rounded-lg border border-amber-400/60 bg-amber-500/20 px-3 text-[11px] font-semibold text-amber-100 transition hover:bg-amber-500/30 disabled:opacity-60 cursor-pointer"
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            Ack
          </button>
        )}
        <button
          type="button"
          onClick={() => onInspectCrew(member.crew_id, current.key)}
          className="flex min-h-[32px] items-center gap-1 rounded-lg bg-gradient-to-r from-red-600 via-rose-600 to-amber-500 px-3.5 text-[11px] font-bold text-white shadow-[0_0_16px_rgba(239,68,68,0.5)] transition hover:brightness-110 cursor-pointer"
        >
          Inspect Cockpit <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </aside>
  );
}
