import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock,
  CloudOff,
  FileCheck2,
  GitBranch,
  Link2,
  Minus,
  Satellite,
  Send,
  ShieldCheck,
  ShieldX,
  UserRoundCheck,
} from "lucide-react";
import {
  completeFollowupReassessment,
  confirmFollowupMeasurement,
  createEarthSyncPackage,
  escalateFollowupCase,
  getEarthSyncLedger,
  recordFollowupAction,
  synchronizeWithEarth,
  verifyEarthSyncLedger,
} from "../services/api";

// ---------- shared tokens (DESIGN.md traffic-light encoding) ----------
const SEVERITY_PILL = {
  NOMINAL: "bg-emerald-500/10 text-emerald-300 border-emerald-400/30",
  WARNING: "bg-amber-500/10 text-amber-200 border-amber-400/30",
  CRITICAL: "bg-red-500/10 text-red-300 border-red-400/30",
};

const CASE_STATUS = {
  OPEN_PENDING_CONFIRMATION: { label: "Awaiting confirmation", tone: "WARNING" },
  CONFIRMED_ACTIVE_MONITORING: { label: "Confirmed · monitoring", tone: "CRITICAL" },
  ACTION_EXECUTED_AWAITING_REASSESSMENT: { label: "Action logged · reassess", tone: "WARNING" },
  DOWNGRADED_CONFOUNDER_OR_ARTIFACT: { label: "Downgraded · artifact/context", tone: "NOMINAL" },
  ESCALATED_TO_EARTH: { label: "Escalated to Flight Surgeon", tone: "CRITICAL" },
  RESOLVED: { label: "Resolved", tone: "NOMINAL" },
};

const TREND = {
  SUSTAINED_DRIFT: { label: "Sustained", cls: "text-red-300 bg-red-500/10 border-red-400/30" },
  GRADUAL_DRIFT: { label: "Gradual", cls: "text-amber-200 bg-amber-500/10 border-amber-400/30" },
  STABLE: { label: "Stable", cls: "text-slate-300 bg-[#151922] border-white/10" },
};

const panel = "rounded-2xl border border-white/10 bg-[#0B0E14]/80 p-5";
const btnPrimary =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full bg-sky-600 px-4 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400";
const btnSky =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full bg-sky-500/10 px-4 text-sm font-semibold text-sky-200 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400";
const btnGhost =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full border border-white/15 bg-[#151922] px-4 text-sm font-semibold text-slate-200 transition hover:border-white/35 hover:text-white disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400";
const field =
  "min-h-[44px] w-full rounded-xl border border-white/10 bg-[#151922] px-3 text-sm text-white placeholder:text-slate-500 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/25";

const HORIZONS_SOURCE = {
  live_nasa_jpl_horizons: "Live NASA JPL Horizons",
  cached_nasa_jpl_horizons: "NASA JPL Horizons (cached)",
  curated_local_fallback: "Reference value",
};

function formatDelay(seconds) {
  if (seconds < 90) return `${Math.round(seconds)} s`;
  const min = Math.floor(seconds / 60);
  const sec = Math.round(seconds % 60);
  return sec ? `${min} min ${sec} s` : `${min} min`;
}

function Pill({ tone = "NOMINAL", children, className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${SEVERITY_PILL[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

function SectionTitle({ icon: Icon, children, aside }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <h2 className="flex items-center gap-2 text-lg font-bold text-white">
        <Icon className="h-5 w-5 text-emerald-400" strokeWidth={1.8} />
        {children}
      </h2>
      {aside}
    </div>
  );
}

// Small magnitudes (dose rates ~0.03 mSv/h) need more decimals or they collapse to "0"
const fmtNum = (v, digits = 1) => {
  if (typeof v !== "number") return "–";
  const d = Math.abs(v) > 0 && Math.abs(v) < 1 ? Math.max(digits, 3) : digits;
  const txt = v.toFixed(d);
  // Trim trailing zeros only after the decimal point ("120" must stay "120")
  return txt.includes(".") ? txt.replace(/0+$/, "").replace(/\.$/, "") : txt;
};

function relativeDue(iso, now) {
  if (!iso) return null;
  const mins = Math.round((new Date(iso).getTime() - now) / 60000);
  if (mins > 0) return { text: `due in ${mins} min`, overdue: false };
  if (mins === 0) return { text: "due now", overdue: false };
  return { text: `${Math.abs(mins)} min overdue`, overdue: true };
}

function useNow(intervalMs = 30000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

// ======================================================================
// Follow-up case card (Pillar 3)
// ======================================================================
function FollowUpCase({ item, metricOptions, now, onChanged, onError }) {
  const status = CASE_STATUS[item.status] || { label: item.status, tone: "WARNING" };
  const closed = item.status === "RESOLVED";
  const [busy, setBusy] = useState("");
  const [metric, setMetric] = useState(metricOptions[0]?.key || "heart_rate_bpm");
  const [value, setValue] = useState("");
  const [actionText, setActionText] = useState("");
  const [minutes, setMinutes] = useState(30);
  const [resolve, setResolve] = useState(false);
  const [escalateReason, setEscalateReason] = useState("");
  const [open, setOpen] = useState(!closed);

  const openReassessment = item.reassessments_scheduled.find((r) => r.status !== "COMPLETED");
  const due = relativeDue(item.next_due_at, now);
  // The due-time chip already says this in relative terms; the backend sentence carries a raw ISO timestamp.
  const pendingItems = (item.pending_items || []).filter((p) => !p.startsWith("Reassessment due at"));

  const run = async (kind, fn) => {
    setBusy(kind);
    try {
      await fn();
      await onChanged();
    } catch (err) {
      onError(err?.message || "Request failed.");
    } finally {
      setBusy("");
    }
  };

  const timeline = [
    ...item.confirmations_recorded.map((c) => ({
      at: c.recorded_at,
      icon: c.confirms_anomaly ? AlertTriangle : CheckCircle2,
      tone: c.confirms_anomaly ? "text-amber-300" : "text-emerald-400",
      text: `Confirmation ${metricOptions.find((m) => m.key === c.metric)?.label || c.metric} = ${c.measured_value} ${c.unit} (${c.device_used}) — ${
        c.confirms_anomaly ? "anomaly confirmed" : "back within personal band"
      }`,
    })),
    ...item.actions_executed.map((a) => ({
      at: a.executed_at,
      icon: UserRoundCheck,
      tone: "text-sky-200",
      text: `${a.performed_by}: ${a.action_description}`,
    })),
    ...item.reassessments_scheduled
      .filter((r) => r.status === "COMPLETED")
      .map((r) => ({
        at: r.completed_at,
        icon: FileCheck2,
        tone: "text-emerald-400",
        text: `Reassessment done — ${r.post_reassessment_summary || "no notes"}`,
      })),
  ].sort((a, b) => String(a.at).localeCompare(String(b.at)));

  return (
    <article className="rounded-2xl border border-white/10 bg-[#0B0E14]/80">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full min-h-[44px] items-start justify-between gap-3 rounded-2xl p-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400"
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone={item.severity}>{item.severity}</Pill>
            <Pill tone={status.tone}>{status.label}</Pill>
            {due && !closed && (
              <span
                className={`inline-flex items-center gap-1 text-xs font-semibold ${
                  due.overdue ? "text-red-300" : "text-slate-300"
                }`}
              >
                <Clock className="h-3.5 w-3.5" /> {due.text}
              </span>
            )}
          </div>
          <h3 className="mt-2 text-[15px] font-bold leading-snug text-white">{item.title}</h3>
          <p className="mt-0.5 font-mono-telemetry text-[11px] text-slate-400">
            {item.case_id} · day {item.mission_day} · {item.system_id}
          </p>
        </div>
        <ChevronDown className={`mt-1 h-5 w-5 shrink-0 text-slate-300 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="space-y-4 border-t border-white/10 px-4 pb-4 pt-3">
          {pendingItems.length > 0 && (
            <ul className="space-y-1.5">
              {pendingItems.map((p) => (
                <li key={p} className="flex items-start gap-2 text-sm text-white">
                  <CircleDot className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                  {p}
                </li>
              ))}
            </ul>
          )}
          {item.escalation_reason && (
            <p className="rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-300">
              Escalated: {item.escalation_reason}
            </p>
          )}
          {item.resolution_notes && <p className="text-sm text-slate-300">{item.resolution_notes}</p>}

          {timeline.length > 0 && (
            <ol className="space-y-2">
              {timeline.map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-[13px] leading-snug text-slate-200">
                  <t.icon className={`mt-0.5 h-4 w-4 shrink-0 ${t.tone}`} />
                  <span>
                    <span className="font-mono-telemetry text-[11px] text-slate-400">
                      {new Date(t.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>{" "}
                    {t.text}
                  </span>
                </li>
              ))}
            </ol>
          )}

          {!closed && (
            <div className="grid gap-4 lg:grid-cols-2">
              <form
                className="space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (value === "") return;
                  run("confirm", () =>
                    confirmFollowupMeasurement(item.case_id, { metric, measured_value: Number(value) }),
                  );
                }}
              >
                <p className="text-xs font-semibold text-slate-300">Confirmation measurement</p>
                <div className="flex gap-2">
                  <select
                    aria-label="Metric"
                    className={field}
                    value={metric}
                    onChange={(e) => setMetric(e.target.value)}
                  >
                    {metricOptions.map((m) => (
                      <option key={m.key} value={m.key}>
                        {m.label} ({m.unit})
                      </option>
                    ))}
                  </select>
                  <input
                    aria-label="Measured value"
                    className={`${field} w-28 font-mono-telemetry`}
                    type="number"
                    step="any"
                    inputMode="decimal"
                    placeholder="value"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                  />
                </div>
                <button type="submit" className={btnPrimary} disabled={!!busy || value === ""}>
                  {busy === "confirm" ? "Recording…" : "Record confirmation"}
                </button>
              </form>

              <form
                className="space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!actionText.trim()) return;
                  run("action", async () => {
                    await recordFollowupAction(item.case_id, {
                      action_description: actionText.trim(),
                      schedule_reassessment_in_minutes: Number(minutes),
                    });
                    setActionText("");
                  });
                }}
              >
                <p className="text-xs font-semibold text-slate-300">Protocol action performed by the crew</p>
                <input
                  aria-label="Action performed"
                  className={field}
                  placeholder="e.g. 500 ml oral rehydration per protocol"
                  value={actionText}
                  onChange={(e) => setActionText(e.target.value)}
                />
                <div className="flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-2 text-xs text-slate-300">
                    Reassess in
                    <select
                      className={`${field} w-24`}
                      value={minutes}
                      onChange={(e) => setMinutes(e.target.value)}
                    >
                      {[15, 30, 60, 120].map((m) => (
                        <option key={m} value={m}>
                          {m} min
                        </option>
                      ))}
                    </select>
                  </label>
                  <button type="submit" className={btnSky} disabled={!!busy || !actionText.trim()}>
                    {busy === "action" ? "Logging…" : "Log action"}
                  </button>
                </div>
              </form>

              <div className="space-y-2">
                <p className="text-xs font-semibold text-slate-300">Reassessment</p>
                <label className="flex min-h-[44px] items-center gap-2 text-sm text-white">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-sky-500"
                    checked={resolve}
                    onChange={(e) => setResolve(e.target.checked)}
                  />
                  Resolve the case after this reassessment
                </label>
                <button
                  type="button"
                  className={btnGhost}
                  disabled={!!busy || !openReassessment}
                  onClick={() =>
                    run("reassess", () =>
                      completeFollowupReassessment(item.case_id, {
                        reassessment_id: openReassessment.reassessment_id,
                        resolve_case: resolve,
                        summary: resolve
                          ? "Reassessment completed; values back toward personal baseline. Case resolved by crew."
                          : "Reassessment completed; monitoring continues.",
                      }),
                    )
                  }
                >
                  {busy === "reassess" ? "Saving…" : openReassessment ? "Complete reassessment" : "No reassessment pending"}
                </button>
              </div>

              {item.status !== "ESCALATED_TO_EARTH" && (
                <form
                  className="space-y-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    run("escalate", () =>
                      escalateFollowupCase(item.case_id, {
                        reason: escalateReason.trim() || "Crew requests Flight Surgeon review.",
                      }),
                    );
                  }}
                >
                  <p className="text-xs font-semibold text-slate-300">Escalate (crew decision)</p>
                  <input
                    aria-label="Escalation reason"
                    className={field}
                    placeholder="Reason for the Flight Surgeon"
                    value={escalateReason}
                    onChange={(e) => setEscalateReason(e.target.value)}
                  />
                  <button
                    type="submit"
                    disabled={!!busy}
                    className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full border border-red-400/30 bg-red-500/10 px-4 text-sm font-semibold text-red-300 transition hover:bg-red-500/20 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-400"
                  >
                    <Send className="h-4 w-4" />
                    {busy === "escalate" ? "Escalating…" : "Escalate to Flight Surgeon"}
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

// ======================================================================
// Explainable alert (Pillar 4)
// ======================================================================
function ExplainableAlertItem({ alert }) {
  const [open, setOpen] = useState(false);
  const q = alert.measurement_quality;
  const u = alert.uncertainty;
  const g = alert.autonomy_guardrail;
  return (
    <article className="rounded-2xl border border-white/10 bg-[#0B0E14]/80">
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={alert.severity}>{alert.severity}</Pill>
          <span className="font-mono-telemetry text-[11px] text-slate-400">{alert.alert_id}</span>
          {alert.followup_case_id && (
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-sky-200">
              <Link2 className="h-3.5 w-3.5" /> {alert.followup_case_id}
            </span>
          )}
        </div>
        <h3 className="mt-2 text-[15px] font-bold leading-snug text-white">{alert.title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-slate-200">{alert.explanation_summary}</p>

        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[420px] text-left text-[13px]">
            <caption className="sr-only">Signals that originated this alert</caption>
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-slate-400">
                <th className="py-1.5 pr-3 font-semibold">Signal</th>
                <th className="py-1.5 pr-3 text-right font-semibold">Now</th>
                <th className="py-1.5 pr-3 text-right font-semibold">Personal</th>
                <th className="py-1.5 pr-3 text-right font-semibold">z (own)</th>
                <th className="py-1.5 text-right font-semibold">Weight</th>
              </tr>
            </thead>
            <tbody className="font-mono-telemetry text-white">
              {alert.originating_signals.map((s) => (
                <tr key={s.metric} className="border-t border-white/10">
                  <td className="py-1.5 pr-3 font-sans text-slate-200">{s.label}</td>
                  <td className="py-1.5 pr-3 text-right">{fmtNum(s.current_value)}</td>
                  <td className="py-1.5 pr-3 text-right text-slate-300">{fmtNum(s.personal_ewma_baseline)}</td>
                  <td className="py-1.5 pr-3 text-right font-semibold">{fmtNum(s.individual_z_score)}σ</td>
                  <td className="py-1.5 text-right text-slate-300">{fmtNum(s.attribution_weight_pct)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-[13px] sm:grid-cols-4">
          <div>
            <dt className="text-[11px] text-slate-400">Signal quality</dt>
            <dd className="font-mono-telemetry font-semibold text-white">{fmtNum(q.overall_quality_pct, 0)}%</dd>
          </div>
          <div>
            <dt className="text-[11px] text-slate-400">Uncertainty</dt>
            <dd className="font-mono-telemetry font-semibold text-white">±{fmtNum(u.total_uncertainty_pct)}%</dd>
          </div>
          <div>
            <dt className="text-[11px] text-slate-400">Reliability</dt>
            <dd className="font-semibold text-white">{u.reliability_grade.replaceAll("_", " ").toLowerCase()}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-slate-400">Re-measure</dt>
            <dd className="font-semibold text-white">{u.requires_confirmatory_remeasurement ? "required" : "not required"}</dd>
          </div>
        </dl>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="mt-2 inline-flex min-h-[44px] items-center gap-1 text-sm font-semibold text-sky-200 hover:underline underline-offset-4"
        >
          Sources, context and verification steps
          <ChevronDown className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} />
        </button>

        {open && (
          <div className="mt-1 space-y-3 text-[13px] leading-relaxed text-slate-200">
            {q.sensor_notes && <p>{q.sensor_notes}</p>}
            {u.uncertainty_factors?.length > 0 && (
              <ul className="list-disc space-y-0.5 pl-5">
                {u.uncertainty_factors.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            )}
            {alert.recommended_verification_steps?.length > 0 && (
              <div>
                <p className="font-semibold text-white">Verify before acting</p>
                <ul className="list-disc space-y-0.5 pl-5">
                  {alert.recommended_verification_steps.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {alert.contextual_factors?.length > 0 && (
              <div>
                <p className="font-semibold text-white">Context considered</p>
                <ul className="list-disc space-y-0.5 pl-5">
                  {alert.contextual_factors.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="rounded-xl bg-sky-500/10 px-3 py-2 text-sky-200">{alert.causal_disclaimer}</p>
            <ul className="space-y-1">
              {alert.scientific_references.map((r) => (
                <li key={r.code}>
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-sky-200 underline decoration-sky-400/40 underline-offset-4 hover:decoration-sky-300"
                  >
                    {r.code}
                  </a>{" "}
                  — {r.title}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <p className="flex items-start gap-2 rounded-b-2xl border-t border-white/10 bg-emerald-500/10 px-4 py-2.5 text-[12px] leading-snug text-white">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
        {g.autonomous_diagnosis_blocked && g.autonomous_treatment_blocked
          ? `Decision support only — no autonomous diagnosis or treatment. Authority: ${g.decision_authority}.`
          : g.governance_notice}
      </p>
    </article>
  );
}

// ======================================================================
// Personal baseline (Pillar 1) + context (Pillar 2)
// ======================================================================
function BaselinePanel({ baseline }) {
  const rows = useMemo(
    () =>
      Object.values(baseline.metrics)
        .filter((m) => m.history_points_used + m.history_points_quarantined > 0)
        .sort((a, b) => Math.abs(b.individual_z_score) - Math.abs(a.individual_z_score)),
    [baseline],
  );
  return (
    <section className={panel} aria-labelledby="baseline-title">
      <SectionTitle
        icon={UserRoundCheck}
        aside={
          <span className="font-mono-telemetry text-xs text-slate-300">
            drift {fmtNum(baseline.personal_drift_score)}% · d<sub>M</sub> {fmtNum(baseline.multivariate_mahalanobis_distance, 2)}
          </span>
        }
      >
        <span id="baseline-title">Personal baseline</span>
      </SectionTitle>
      <p className="-mt-2 mb-3 text-[13px] leading-relaxed text-slate-300">
        {baseline.astronaut_name} compared with their own history in {baseline.mission_phase.replaceAll("_", " ")} (
        {fmtNum(baseline.gravitational_g, 2)} g), not the population average.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[440px] text-left text-[13px]">
          <caption className="sr-only">Current value versus personal adaptive baseline per metric</caption>
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-slate-400">
              <th className="py-1.5 pr-2 font-semibold">Metric</th>
              <th className="py-1.5 pr-2 text-right font-semibold">Now</th>
              <th className="py-1.5 pr-2 text-right font-semibold">Personal</th>
              <th className="py-1.5 pr-2 text-right font-semibold">z own / pop</th>
              <th className="py-1.5 font-semibold">Trend</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => {
              const t = TREND[m.trend_status] || TREND.STABLE;
              const z = m.individual_z_score;
              const zCls = Math.abs(z) >= 2.5 ? "text-red-300" : Math.abs(z) >= 1.5 ? "text-amber-200" : "text-white";
              const Arrow = m.trend_slope_sigma_per_day > 0.4 ? ArrowUpRight : m.trend_slope_sigma_per_day < -0.4 ? ArrowDownRight : Minus;
              return (
                <tr key={m.metric} className="border-t border-white/10 align-top">
                  <td className="py-2 pr-2">
                    <span className="text-white">{m.label}</span>
                    {m.history_points_quarantined > 0 && (
                      <span className="block whitespace-nowrap text-[11px] text-amber-200">
                        {m.history_points_quarantined}/{m.history_points_used + m.history_points_quarantined} days excluded
                      </span>
                    )}
                  </td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right font-mono-telemetry text-white">{fmtNum(m.current_value)}</td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right font-mono-telemetry text-slate-300">
                    {fmtNum(m.rolling_ewma_baseline)}
                    <span className="text-[11px]"> ±{fmtNum(m.rolling_mad_std)}</span>
                  </td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right font-mono-telemetry">
                    <span className={`font-semibold ${zCls}`}>{fmtNum(z)}</span>
                    <span className="text-slate-400"> / {fmtNum(m.population_z_score)}</span>
                  </td>
                  <td className="py-2">
                    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold ${t.cls}`}>
                      <Arrow className="h-3.5 w-3.5" />
                      {t.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[11px] text-slate-400">
        Trend is the slope of past days in personal σ/day; days already anomalous are excluded so a slow decline
        cannot become the new normal. Covariance: {baseline.covariance_source.replaceAll("_", " ")} · window {baseline.history_window_days} days · {baseline.osdr_reference_study}
      </p>
    </section>
  );
}

function ContextPanel({ report }) {
  return (
    <section className={panel} aria-labelledby="context-title">
      <SectionTitle icon={CircleDot}>
        <span id="context-title">Mission context</span>
      </SectionTitle>
      <p className="-mt-2 mb-3 text-[13px] leading-relaxed text-slate-300">{report.primary_contextual_summary}</p>
      {report.associations.length === 0 ? (
        <p className="text-sm text-slate-300">No sleep, exercise, EVA, gravity or cabin factor is active right now.</p>
      ) : (
        <ul className="space-y-3">
          {report.associations.map((a) => (
            <li key={a.factor_id} className="rounded-xl bg-[#151922] p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-semibold leading-snug text-white">{a.factor_name}</p>
                <span className="shrink-0 font-mono-telemetry text-xs text-slate-300">r≈{fmtNum(a.association_strength, 2)}</span>
              </div>
              <p className="mt-0.5 font-mono-telemetry text-[11px] text-slate-300">{a.observed_context_value}</p>
              <p className="mt-1 text-[12px] leading-relaxed text-slate-200">{a.rationale}</p>
              <p className="mt-1 text-[11px] text-slate-400">{a.scientific_source}</p>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-[11px] leading-snug text-slate-400">
        Associations are observational correlations; they never establish cause on their own.
      </p>
    </section>
  );
}

// ======================================================================
// Ship <-> Earth continuity (Pillar 5)
// ======================================================================
function EarthLinkPanel({ state, onChanged, onError }) {
  const [ledger, setLedger] = useState(null);
  const [verify, setVerify] = useState(null);
  const [busy, setBusy] = useState("");
  const link = state.horizons_link;

  const refreshLedger = useCallback(async () => {
    try {
      setLedger(await getEarthSyncLedger());
    } catch (err) {
      onError(err?.message || "Could not read the onboard ledger.");
    }
  }, [onError]);

  useEffect(() => {
    refreshLedger();
  }, [refreshLedger, state.earth_sync_queue_count, state.earth_sync_last_package_id]);

  const run = async (kind, fn) => {
    setBusy(kind);
    try {
      await fn();
      await Promise.all([onChanged(), refreshLedger()]);
    } catch (err) {
      onError(err?.message || "Request failed.");
    } finally {
      setBusy("");
    }
  };

  const packages = [...(ledger?.packages || [])].reverse().slice(0, 5);

  return (
    <section className={panel} aria-labelledby="earth-title">
      <SectionTitle icon={Satellite}>
        <span id="earth-title">Ship ↔ Earth</span>
      </SectionTitle>

      <dl className="grid grid-cols-3 gap-3 text-[13px]">
        <div>
          <dt className="text-[11px] text-slate-400">Queued onboard</dt>
          <dd className="font-mono-telemetry text-lg font-bold text-white">{state.earth_sync_queue_count}</dd>
        </div>
        <div>
          <dt className="text-[11px] text-slate-400">One-way delay</dt>
          <dd className="font-mono-telemetry text-lg font-bold text-white">
            {link ? formatDelay(link.one_way_light_time_seconds) : "–"}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] text-slate-400">Link</dt>
          <dd className={`text-sm font-semibold ${link?.comms_available ? "text-emerald-300" : "text-red-300"}`}>
            {link?.comms_available ? "window open" : "no window"}
          </dd>
        </div>
      </dl>
      {link && (
        <p className="mt-2 text-[11px] text-slate-400" title={link.fetch_status || undefined}>
          {HORIZONS_SOURCE[link.source] || "JPL Horizons"} · {link.target_body} ·{" "}
          {link.distance_km >= 1e6 ? `${(link.distance_km / 1e6).toFixed(1)} million km` : `${Math.round(link.distance_km)} km`}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className={btnPrimary} disabled={!!busy} onClick={() => run("package", createEarthSyncPackage)}>
          {busy === "package" ? "Packaging…" : "Package for Flight Surgeons"}
        </button>
        <button
          type="button"
          className={btnSky}
          disabled={!!busy || state.earth_sync_queue_count === 0}
          onClick={() => run("sync", synchronizeWithEarth)}
        >
          {busy === "sync" ? "Sending…" : "Send queued"}
        </button>
        <button
          type="button"
          className={btnGhost}
          disabled={!!busy}
          onClick={async () => {
            setBusy("verify");
            try {
              setVerify(await verifyEarthSyncLedger());
            } catch (err) {
              onError(err?.message || "Verification failed.");
            } finally {
              setBusy("");
            }
          }}
        >
          {busy === "verify" ? "Checking…" : "Verify hash chain"}
        </button>
      </div>

      {verify && (
        <div
          role="status"
          className={`mt-3 flex items-start gap-2 rounded-xl px-3 py-2 text-[13px] ${
            verify.verified ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"
          }`}
        >
          {verify.verified ? <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" /> : <ShieldX className="mt-0.5 h-4 w-4 shrink-0" />}
          <span>
            {verify.verified
              ? `Chain intact: ${verify.packages_checked} packages and ${verify.audit_events_checked} audit events re-hashed.`
              : `Chain broken: ${[...verify.package_issues, ...verify.audit_issues].slice(0, 3).join("; ")}`}
          </span>
        </div>
      )}

      {packages.length > 0 && (
        <ul className="mt-4 divide-y divide-white/10 text-[13px]">
          {packages.map((p) => (
            <li key={p.package_id} className="py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono-telemetry text-[12px] text-white">{p.package_id}</span>
                <Pill tone={p.sync_status === "QUEUED_OFFLINE" ? "WARNING" : "NOMINAL"}>
                  {p.sync_status === "QUEUED_OFFLINE" ? "queued" : "delivered"}
                </Pill>
              </div>
              <p className="mt-0.5 font-mono-telemetry text-[11px] text-slate-400">
                sha256 {p.sha256_integrity_hash.slice(0, 12)}… ← {p.previous_package_hash ? `${p.previous_package_hash.slice(0, 8)}…` : "legacy"}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ======================================================================
// Cross diagnosis: physical vs. space weather (DONKI) vs. psychological
// ======================================================================
const LAYER_COPY = {
  NOMINAL: { label: "No anomaly", tone: "NOMINAL" },
  EXTERNAL_SPACE_WEATHER: { label: "Layer 1 · External: space weather", tone: "CRITICAL" },
  ONBOARD_ENVIRONMENT: { label: "Layer 2 · Onboard environment", tone: "WARNING" },
  CONTEXTUAL_BENIGN: { label: "Layer 2 · Benign context", tone: "NOMINAL" },
  INTERNAL_PHYSIOLOGICAL: { label: "Layer 2 · Internal physical", tone: "CRITICAL" },
  PSYCHOLOGICAL_NEUROCOGNITIVE: { label: "Layer 3 · Psychological / neurocognitive", tone: "WARNING" },
};

function CrossDiagnosisPanel({ result }) {
  if (!result) return null;
  const copy = LAYER_COPY[result.root_cause] || { label: result.root_cause, tone: "WARNING" };
  const supports = result.evidence.filter((e) => e.supports);
  const ruled = result.evidence.filter((e) => !e.supports);
  const pp = result.psych_protocol;
  const flags = [
    result.shelter_recommended && "Storm shelter now",
    result.eva_hold_recommended && "Hold EVA",
    result.notify_earth && `Notify Earth · ${result.earth_priority.toLowerCase()}`,
  ].filter(Boolean);

  return (
    <section className={panel} aria-labelledby="cross-title">
      <SectionTitle icon={GitBranch} aside={<Pill tone={copy.tone}>{copy.label}</Pill>}>
        <span id="cross-title">Root cause</span>
      </SectionTitle>
      <h3 className="text-[15px] font-bold leading-snug text-white">{result.title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-slate-200">{result.summary}</p>

      {flags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {flags.map((f) => (
            <Pill key={f} tone={result.earth_priority === "IMMEDIATE" ? "CRITICAL" : "WARNING"}>
              {f}
            </Pill>
          ))}
        </div>
      )}

      <div className={`mt-4 grid gap-4 ${ruled.length ? "sm:grid-cols-2" : ""}`}>
        <div>
          <p className="text-xs font-semibold text-slate-300">Evidence</p>
          {supports.length === 0 ? (
            <p className="mt-1 text-[13px] text-slate-300">Nothing abnormal to attribute.</p>
          ) : (
            <ul className="mt-1 space-y-1 text-[13px] text-white">
              {supports.map((e, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CircleDot className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />
                  <span>
                    {e.signal} <span className="font-mono-telemetry">{e.value}</span>
                    <span className="text-slate-400"> · {e.rule}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        {ruled.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-300">Ruled out</p>
          <ul className="mt-1 space-y-1 text-[13px] text-slate-300">
            {ruled.map((e, i) => (
              <li key={i} className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                <span>
                  {e.signal}: {e.value}
                </span>
              </li>
            ))}
          </ul>
        </div>
        )}
      </div>

      {pp ? (
        <div className="mt-4 rounded-xl bg-sky-500/10 p-4 text-sky-200">
          <p className="text-sm font-bold">{pp.name}</p>
          <p className="mt-1 text-[13px] leading-relaxed">{pp.reassurance}</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-[13px] leading-relaxed">
            {pp.grounding_steps.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ol>
          {pp.escalate_to_earth && (
            <p role="alert" className="mt-3 rounded-lg bg-red-500/10 px-3 py-2 text-[13px] font-semibold text-red-300">
              Immediate escalation to the Earth Flight Surgeon: {pp.escalation_reason}
            </p>
          )}
        </div>
      ) : (
        result.recommended_actions.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold text-slate-300">Protocol steps for the crew medical officer</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-[13px] text-slate-200">
              {result.recommended_actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </div>
        )
      )}
      <p className="mt-3 text-[11px] leading-snug text-slate-400">{result.disclaimer}</p>
    </section>
  );
}

// ======================================================================
// Workspace
// ======================================================================
export default function ClinicalContinuity({ state, connection, onRefresh }) {
  const [view, setView] = useState("overview");
  const now = useNow();
  const [error, setError] = useState("");
  const onError = useCallback((msg) => setError(msg), []);
  const onChanged = useCallback(async () => {
    setError("");
    await onRefresh();
  }, [onRefresh]);

  const live = connection === "live" && state?.adaptive_baseline;

  if (!live) {
    return (
      <div className="rounded-2xl border border-white/10 bg-[#0B0E14]/80 p-8 text-white">
        <div className="mx-auto flex max-w-xl flex-col items-center text-center">
          <CloudOff className="h-10 w-10 text-slate-300" strokeWidth={1.6} />
          <h2 className="mt-3 text-xl font-bold">Clinical continuity needs the onboard backend</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">
            The dashboard is running on simulated data. Personal baselines, follow-up cases and the Earth ledger are never
            simulated, because a fabricated audit trail is worse than none. Start the backend on port 8000 and reload.
          </p>
          <button type="button" className={`${btnPrimary} mt-5`} onClick={onRefresh}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  const VIEWS = [
    { id: "overview", label: "Root cause & follow-up" },
    { id: "alerts", label: "Alerts" },
    { id: "baseline", label: "Baseline & context" },
    { id: "earth", label: "Earth link" },
  ];
  const metricOptions = Object.values(state.adaptive_baseline.metrics).map((m) => ({
    key: m.metric,
    label: m.label,
    unit: m.unit,
  }));
  const cases = state.followup_cases || [];
  const openCases = cases.filter((c) => c.status !== "RESOLVED");
  const closedCases = cases.filter((c) => c.status === "RESOLVED");
  const overdue = openCases.reduce((n, c) => n + (c.overdue_reassessments || 0), 0);

  return (
    <div className="text-white">
      {error && (
        <div role="alert" className="mb-4 flex items-start justify-between gap-3 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          <span>{error}</span>
          <button type="button" className="font-semibold underline underline-offset-4" onClick={() => setError("")}>
            Dismiss
          </button>
        </div>
      )}

      <div role="tablist" aria-label="Diagnosis views" className="mb-5 flex flex-wrap gap-1 rounded-xl bg-[#151922] p-1">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            type="button"
            role="tab"
            aria-selected={view === v.id}
            onClick={() => setView(v.id)}
            className={`min-h-[40px] flex-1 whitespace-nowrap rounded-lg px-3 text-sm font-semibold transition ${
              view === v.id ? "bg-white/10 text-white" : "text-slate-300 hover:text-white"
            }`}
          >
            {v.label}
            {v.id === "overview" && overdue > 0 && (
              <span className="ml-1.5 rounded-full bg-red-500/10 px-1.5 text-xs text-red-300">{overdue}</span>
            )}
            {v.id === "alerts" && state.explainable_alerts.length > 0 && (
              <span className="ml-1.5 rounded-full bg-amber-500/10 px-1.5 text-xs text-amber-200">{state.explainable_alerts.length}</span>
            )}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="space-y-5">
        {view === "overview" && (
          <>
            <CrossDiagnosisPanel result={state.cross_diagnosis} />
              <section className={panel} aria-labelledby="followup-title">
                <SectionTitle
                  icon={FileCheck2}
                  aside={
                    <span className="text-xs font-semibold text-slate-300">
                      {openCases.length} open{overdue > 0 && <span className="text-red-300"> · {overdue} overdue</span>}
                    </span>
                  }
                >
                  <span id="followup-title">Follow-up</span>
                </SectionTitle>
                {openCases.length === 0 ? (
                  <p className="text-sm text-slate-300">No open cases. Every alert so far was confirmed, acted on and closed.</p>
                ) : (
                  <div className="space-y-3">
                    {openCases.map((c) => (
                      <FollowUpCase key={c.case_id} item={c} metricOptions={metricOptions} now={now} onChanged={onChanged} onError={onError} />
                    ))}
                  </div>
                )}
                {closedCases.length > 0 && (
                  <details className="mt-4 text-sm text-slate-300">
                    <summary className="min-h-[44px] cursor-pointer py-2 font-semibold text-white">
                      {closedCases.length} resolved case{closedCases.length > 1 ? "s" : ""}
                    </summary>
                    <div className="mt-2 space-y-3">
                      {closedCases.map((c) => (
                        <FollowUpCase key={c.case_id} item={c} metricOptions={metricOptions} now={now} onChanged={onChanged} onError={onError} />
                      ))}
                    </div>
                  </details>
                )}
              </section>
          </>
        )}
        {view === "alerts" && (
          <>
              <section className={panel} aria-labelledby="alerts-title">
                <SectionTitle icon={AlertTriangle}>
                  <span id="alerts-title">Why alerts fired</span>
                </SectionTitle>
                {state.explainable_alerts.length === 0 ? (
                  <p className="text-sm text-slate-300">No active alerts. All readings sit within this astronaut's personal band.</p>
                ) : (
                  <div className="space-y-3">
                    {state.explainable_alerts.map((a) => (
                      <ExplainableAlertItem key={a.alert_id} alert={a} />
                    ))}
                  </div>
                )}
              </section>
          </>
        )}
        {view === "baseline" && (
          <div className="grid gap-5 xl:grid-cols-5">
            <div className="xl:col-span-3">
              <BaselinePanel baseline={state.adaptive_baseline} />
            </div>
            <div className="xl:col-span-2">
              <ContextPanel report={state.contextual_intelligence} />
            </div>
          </div>
        )}
        {view === "earth" && <EarthLinkPanel state={state} onChanged={onChanged} onError={onError} />}
      </div>
    </div>
  );
}
