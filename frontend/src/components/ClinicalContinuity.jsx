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
  NOMINAL: "bg-[#ECFDF5] text-[#065F46] border-[#A7F3D0]",
  WARNING: "bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]",
  CRITICAL: "bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]",
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
  SUSTAINED_DRIFT: { label: "Sustained", cls: "text-[#991B1B] bg-[#FEF2F2] border-[#FECACA]" },
  GRADUAL_DRIFT: { label: "Gradual", cls: "text-[#92400E] bg-[#FFFBEB] border-[#FDE68A]" },
  STABLE: { label: "Stable", cls: "text-[#476458] bg-white border-[#D5E8DD]" },
};

const panel = "rounded-2xl border border-[#D5E8DD] bg-white p-5";
const btnPrimary =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full bg-[#113D2E] px-4 text-sm font-semibold text-white transition hover:bg-[#0B2C21] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#16A34A]";
const btnSky =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full bg-[#DFF1F8] px-4 text-sm font-semibold text-[#0C4A6E] transition hover:bg-[#CDE9F4] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0284C7]";
const btnGhost =
  "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full border border-[#D5E8DD] bg-white px-4 text-sm font-semibold text-[#113D2E] transition hover:bg-[#EFF9F2] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#16A34A]";
const field =
  "min-h-[44px] w-full rounded-xl border border-[#D5E8DD] bg-[#F7FBF9] px-3 text-sm text-[#113D2E] placeholder:text-[#6B8579] focus:border-[#16A34A] focus:outline-none focus:ring-2 focus:ring-[#16A34A]/25";

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
      <h2 className="flex items-center gap-2 text-lg font-bold text-[#113D2E]">
        <Icon className="h-5 w-5 text-[#16A34A]" strokeWidth={1.8} />
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
      tone: c.confirms_anomaly ? "text-[#B45309]" : "text-[#059669]",
      text: `Confirmation ${metricOptions.find((m) => m.key === c.metric)?.label || c.metric} = ${c.measured_value} ${c.unit} (${c.device_used}) — ${
        c.confirms_anomaly ? "anomaly confirmed" : "back within personal band"
      }`,
    })),
    ...item.actions_executed.map((a) => ({
      at: a.executed_at,
      icon: UserRoundCheck,
      tone: "text-[#0C4A6E]",
      text: `${a.performed_by}: ${a.action_description}`,
    })),
    ...item.reassessments_scheduled
      .filter((r) => r.status === "COMPLETED")
      .map((r) => ({
        at: r.completed_at,
        icon: FileCheck2,
        tone: "text-[#059669]",
        text: `Reassessment done — ${r.post_reassessment_summary || "no notes"}`,
      })),
  ].sort((a, b) => String(a.at).localeCompare(String(b.at)));

  return (
    <article className="rounded-2xl border border-[#D5E8DD] bg-[#F7FBF9]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full min-h-[44px] items-start justify-between gap-3 rounded-2xl p-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#16A34A]"
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone={item.severity}>{item.severity}</Pill>
            <Pill tone={status.tone}>{status.label}</Pill>
            {due && !closed && (
              <span
                className={`inline-flex items-center gap-1 text-xs font-semibold ${
                  due.overdue ? "text-[#991B1B]" : "text-[#476458]"
                }`}
              >
                <Clock className="h-3.5 w-3.5" /> {due.text}
              </span>
            )}
          </div>
          <h3 className="mt-2 text-[15px] font-bold leading-snug text-[#113D2E]">{item.title}</h3>
          <p className="mt-0.5 font-mono-telemetry text-[11px] text-[#6B8579]">
            {item.case_id} · day {item.mission_day} · {item.system_id}
          </p>
        </div>
        <ChevronDown className={`mt-1 h-5 w-5 shrink-0 text-[#476458] transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="space-y-4 border-t border-[#D5E8DD] px-4 pb-4 pt-3">
          {pendingItems.length > 0 && (
            <ul className="space-y-1.5">
              {pendingItems.map((p) => (
                <li key={p} className="flex items-start gap-2 text-sm text-[#113D2E]">
                  <CircleDot className="mt-0.5 h-4 w-4 shrink-0 text-[#D97706]" />
                  {p}
                </li>
              ))}
            </ul>
          )}
          {item.escalation_reason && (
            <p className="rounded-xl bg-[#FEF2F2] px-3 py-2 text-sm text-[#991B1B]">
              Escalated: {item.escalation_reason}
            </p>
          )}
          {item.resolution_notes && <p className="text-sm text-[#476458]">{item.resolution_notes}</p>}

          {timeline.length > 0 && (
            <ol className="space-y-2">
              {timeline.map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-[13px] leading-snug text-[#334E44]">
                  <t.icon className={`mt-0.5 h-4 w-4 shrink-0 ${t.tone}`} />
                  <span>
                    <span className="font-mono-telemetry text-[11px] text-[#6B8579]">
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
                <p className="text-xs font-semibold text-[#476458]">Confirmation measurement</p>
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
                <p className="text-xs font-semibold text-[#476458]">Protocol action performed by the crew</p>
                <input
                  aria-label="Action performed"
                  className={field}
                  placeholder="e.g. 500 ml oral rehydration per protocol"
                  value={actionText}
                  onChange={(e) => setActionText(e.target.value)}
                />
                <div className="flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-2 text-xs text-[#476458]">
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
                <p className="text-xs font-semibold text-[#476458]">Reassessment</p>
                <label className="flex min-h-[44px] items-center gap-2 text-sm text-[#113D2E]">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[#16A34A]"
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
                  <p className="text-xs font-semibold text-[#476458]">Escalate (crew decision)</p>
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
                    className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full border border-[#FECACA] bg-[#FEF2F2] px-4 text-sm font-semibold text-[#991B1B] transition hover:bg-[#FDE2E2] disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#DC2626]"
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
    <article className="rounded-2xl border border-[#D5E8DD] bg-white">
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={alert.severity}>{alert.severity}</Pill>
          <span className="font-mono-telemetry text-[11px] text-[#6B8579]">{alert.alert_id}</span>
          {alert.followup_case_id && (
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#0C4A6E]">
              <Link2 className="h-3.5 w-3.5" /> {alert.followup_case_id}
            </span>
          )}
        </div>
        <h3 className="mt-2 text-[15px] font-bold leading-snug text-[#113D2E]">{alert.title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-[#334E44]">{alert.explanation_summary}</p>

        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[420px] text-left text-[13px]">
            <caption className="sr-only">Signals that originated this alert</caption>
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-[#6B8579]">
                <th className="py-1.5 pr-3 font-semibold">Signal</th>
                <th className="py-1.5 pr-3 text-right font-semibold">Now</th>
                <th className="py-1.5 pr-3 text-right font-semibold">Personal</th>
                <th className="py-1.5 pr-3 text-right font-semibold">z (own)</th>
                <th className="py-1.5 text-right font-semibold">Weight</th>
              </tr>
            </thead>
            <tbody className="font-mono-telemetry text-[#113D2E]">
              {alert.originating_signals.map((s) => (
                <tr key={s.metric} className="border-t border-[#E6F1EA]">
                  <td className="py-1.5 pr-3 font-sans text-[#334E44]">{s.label}</td>
                  <td className="py-1.5 pr-3 text-right">{fmtNum(s.current_value)}</td>
                  <td className="py-1.5 pr-3 text-right text-[#476458]">{fmtNum(s.personal_ewma_baseline)}</td>
                  <td className="py-1.5 pr-3 text-right font-semibold">{fmtNum(s.individual_z_score)}σ</td>
                  <td className="py-1.5 text-right text-[#476458]">{fmtNum(s.attribution_weight_pct)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-[13px] sm:grid-cols-4">
          <div>
            <dt className="text-[11px] text-[#6B8579]">Signal quality</dt>
            <dd className="font-mono-telemetry font-semibold text-[#113D2E]">{fmtNum(q.overall_quality_pct, 0)}%</dd>
          </div>
          <div>
            <dt className="text-[11px] text-[#6B8579]">Uncertainty</dt>
            <dd className="font-mono-telemetry font-semibold text-[#113D2E]">±{fmtNum(u.total_uncertainty_pct)}%</dd>
          </div>
          <div>
            <dt className="text-[11px] text-[#6B8579]">Reliability</dt>
            <dd className="font-semibold text-[#113D2E]">{u.reliability_grade.replaceAll("_", " ").toLowerCase()}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-[#6B8579]">Re-measure</dt>
            <dd className="font-semibold text-[#113D2E]">{u.requires_confirmatory_remeasurement ? "required" : "not required"}</dd>
          </div>
        </dl>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="mt-2 inline-flex min-h-[44px] items-center gap-1 text-sm font-semibold text-[#0C4A6E] hover:underline underline-offset-4"
        >
          Sources, context and verification steps
          <ChevronDown className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} />
        </button>

        {open && (
          <div className="mt-1 space-y-3 text-[13px] leading-relaxed text-[#334E44]">
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
                <p className="font-semibold text-[#113D2E]">Verify before acting</p>
                <ul className="list-disc space-y-0.5 pl-5">
                  {alert.recommended_verification_steps.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {alert.contextual_factors?.length > 0 && (
              <div>
                <p className="font-semibold text-[#113D2E]">Context considered</p>
                <ul className="list-disc space-y-0.5 pl-5">
                  {alert.contextual_factors.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="rounded-xl bg-[#EAF6FA] px-3 py-2 text-[#0C4A6E]">{alert.causal_disclaimer}</p>
            <ul className="space-y-1">
              {alert.scientific_references.map((r) => (
                <li key={r.code}>
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-[#0C4A6E] underline decoration-[#0284C7]/40 underline-offset-4 hover:decoration-[#0284C7]"
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
      <p className="flex items-start gap-2 rounded-b-2xl border-t border-[#D5E8DD] bg-[#EFF9F2] px-4 py-2.5 text-[12px] leading-snug text-[#113D2E]">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#059669]" />
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
          <span className="font-mono-telemetry text-xs text-[#476458]">
            drift {fmtNum(baseline.personal_drift_score)}% · d<sub>M</sub> {fmtNum(baseline.multivariate_mahalanobis_distance, 2)}
          </span>
        }
      >
        <span id="baseline-title">Personal baseline</span>
      </SectionTitle>
      <p className="-mt-2 mb-3 text-[13px] leading-relaxed text-[#476458]">
        {baseline.astronaut_name} compared with their own history in {baseline.mission_phase.replaceAll("_", " ")} (
        {fmtNum(baseline.gravitational_g, 2)} g), not the population average.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[440px] text-left text-[13px]">
          <caption className="sr-only">Current value versus personal adaptive baseline per metric</caption>
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-[#6B8579]">
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
              const zCls = Math.abs(z) >= 2.5 ? "text-[#991B1B]" : Math.abs(z) >= 1.5 ? "text-[#92400E]" : "text-[#113D2E]";
              const Arrow = m.trend_slope_sigma_per_day > 0.4 ? ArrowUpRight : m.trend_slope_sigma_per_day < -0.4 ? ArrowDownRight : Minus;
              return (
                <tr key={m.metric} className="border-t border-[#E6F1EA] align-top">
                  <td className="py-2 pr-2">
                    <span className="text-[#113D2E]">{m.label}</span>
                    {m.history_points_quarantined > 0 && (
                      <span className="block whitespace-nowrap text-[11px] text-[#92400E]">
                        {m.history_points_quarantined}/{m.history_points_used + m.history_points_quarantined} days excluded
                      </span>
                    )}
                  </td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right font-mono-telemetry text-[#113D2E]">{fmtNum(m.current_value)}</td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right font-mono-telemetry text-[#476458]">
                    {fmtNum(m.rolling_ewma_baseline)}
                    <span className="text-[11px]"> ±{fmtNum(m.rolling_mad_std)}</span>
                  </td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right font-mono-telemetry">
                    <span className={`font-semibold ${zCls}`}>{fmtNum(z)}</span>
                    <span className="text-[#6B8579]"> / {fmtNum(m.population_z_score)}</span>
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
      <p className="mt-3 text-[11px] text-[#6B8579]">
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
      <p className="-mt-2 mb-3 text-[13px] leading-relaxed text-[#476458]">{report.primary_contextual_summary}</p>
      {report.associations.length === 0 ? (
        <p className="text-sm text-[#476458]">No sleep, exercise, EVA, gravity or cabin factor is active right now.</p>
      ) : (
        <ul className="space-y-3">
          {report.associations.map((a) => (
            <li key={a.factor_id} className="rounded-xl bg-[#F7FBF9] p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-semibold leading-snug text-[#113D2E]">{a.factor_name}</p>
                <span className="shrink-0 font-mono-telemetry text-xs text-[#476458]">r≈{fmtNum(a.association_strength, 2)}</span>
              </div>
              <p className="mt-0.5 font-mono-telemetry text-[11px] text-[#476458]">{a.observed_context_value}</p>
              <p className="mt-1 text-[12px] leading-relaxed text-[#334E44]">{a.rationale}</p>
              <p className="mt-1 text-[11px] text-[#6B8579]">{a.scientific_source}</p>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-[11px] leading-snug text-[#6B8579]">
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
          <dt className="text-[11px] text-[#6B8579]">Queued onboard</dt>
          <dd className="font-mono-telemetry text-lg font-bold text-[#113D2E]">{state.earth_sync_queue_count}</dd>
        </div>
        <div>
          <dt className="text-[11px] text-[#6B8579]">One-way delay</dt>
          <dd className="font-mono-telemetry text-lg font-bold text-[#113D2E]">
            {link ? formatDelay(link.one_way_light_time_seconds) : "–"}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] text-[#6B8579]">Link</dt>
          <dd className={`text-sm font-semibold ${link?.comms_available ? "text-[#065F46]" : "text-[#991B1B]"}`}>
            {link?.comms_available ? "window open" : "no window"}
          </dd>
        </div>
      </dl>
      {link && (
        <p className="mt-2 text-[11px] text-[#6B8579]" title={link.fetch_status || undefined}>
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
            verify.verified ? "bg-[#ECFDF5] text-[#065F46]" : "bg-[#FEF2F2] text-[#991B1B]"
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
        <ul className="mt-4 divide-y divide-[#E6F1EA] text-[13px]">
          {packages.map((p) => (
            <li key={p.package_id} className="py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono-telemetry text-[12px] text-[#113D2E]">{p.package_id}</span>
                <Pill tone={p.sync_status === "QUEUED_OFFLINE" ? "WARNING" : "NOMINAL"}>
                  {p.sync_status === "QUEUED_OFFLINE" ? "queued" : "delivered"}
                </Pill>
              </div>
              <p className="mt-0.5 font-mono-telemetry text-[11px] text-[#6B8579]">
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
      <h3 className="text-[15px] font-bold leading-snug text-[#113D2E]">{result.title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-[#334E44]">{result.summary}</p>

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
          <p className="text-xs font-semibold text-[#476458]">Evidence</p>
          {supports.length === 0 ? (
            <p className="mt-1 text-[13px] text-[#476458]">Nothing abnormal to attribute.</p>
          ) : (
            <ul className="mt-1 space-y-1 text-[13px] text-[#113D2E]">
              {supports.map((e, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CircleDot className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#D97706]" />
                  <span>
                    {e.signal} <span className="font-mono-telemetry">{e.value}</span>
                    <span className="text-[#6B8579]"> · {e.rule}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        {ruled.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-[#476458]">Ruled out</p>
          <ul className="mt-1 space-y-1 text-[13px] text-[#476458]">
            {ruled.map((e, i) => (
              <li key={i} className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#059669]" />
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
        <div className="mt-4 rounded-xl bg-[#EAF6FA] p-4 text-[#0C4A6E]">
          <p className="text-sm font-bold">{pp.name}</p>
          <p className="mt-1 text-[13px] leading-relaxed">{pp.reassurance}</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-[13px] leading-relaxed">
            {pp.grounding_steps.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ol>
          {pp.escalate_to_earth && (
            <p role="alert" className="mt-3 rounded-lg bg-[#FEF2F2] px-3 py-2 text-[13px] font-semibold text-[#991B1B]">
              Immediate escalation to the Earth Flight Surgeon: {pp.escalation_reason}
            </p>
          )}
        </div>
      ) : (
        result.recommended_actions.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold text-[#476458]">Protocol steps for the crew medical officer</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-[13px] text-[#334E44]">
              {result.recommended_actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </div>
        )
      )}
      <p className="mt-3 text-[11px] leading-snug text-[#6B8579]">{result.disclaimer}</p>
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
      <div className="rounded-3xl bg-[#F7FBF9] p-8 text-[#113D2E]">
        <div className="mx-auto flex max-w-xl flex-col items-center text-center">
          <CloudOff className="h-10 w-10 text-[#476458]" strokeWidth={1.6} />
          <h2 className="mt-3 text-xl font-bold">Clinical continuity needs the onboard backend</h2>
          <p className="mt-2 text-sm leading-relaxed text-[#476458]">
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
    <div className="rounded-3xl bg-[#F7FBF9] p-4 text-[#113D2E] sm:p-5">
      {error && (
        <div role="alert" className="mb-4 flex items-start justify-between gap-3 rounded-2xl border border-[#FECACA] bg-[#FEF2F2] px-4 py-3 text-sm text-[#991B1B]">
          <span>{error}</span>
          <button type="button" className="font-semibold underline underline-offset-4" onClick={() => setError("")}>
            Dismiss
          </button>
        </div>
      )}

      <div role="tablist" aria-label="Diagnosis views" className="mb-5 flex flex-wrap gap-1 rounded-xl bg-[#E6F1EA] p-1">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            type="button"
            role="tab"
            aria-selected={view === v.id}
            onClick={() => setView(v.id)}
            className={`min-h-[40px] flex-1 whitespace-nowrap rounded-lg px-3 text-sm font-semibold transition ${
              view === v.id ? "bg-white text-[#113D2E] shadow-sm" : "text-[#476458] hover:text-[#113D2E]"
            }`}
          >
            {v.label}
            {v.id === "overview" && overdue > 0 && (
              <span className="ml-1.5 rounded-full bg-[#FEE2E2] px-1.5 text-xs text-[#991B1B]">{overdue}</span>
            )}
            {v.id === "alerts" && state.explainable_alerts.length > 0 && (
              <span className="ml-1.5 rounded-full bg-[#FEF3C7] px-1.5 text-xs text-[#92400E]">{state.explainable_alerts.length}</span>
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
                    <span className="text-xs font-semibold text-[#476458]">
                      {openCases.length} open{overdue > 0 && <span className="text-[#991B1B]"> · {overdue} overdue</span>}
                    </span>
                  }
                >
                  <span id="followup-title">Follow-up</span>
                </SectionTitle>
                {openCases.length === 0 ? (
                  <p className="text-sm text-[#476458]">No open cases. Every alert so far was confirmed, acted on and closed.</p>
                ) : (
                  <div className="space-y-3">
                    {openCases.map((c) => (
                      <FollowUpCase key={c.case_id} item={c} metricOptions={metricOptions} now={now} onChanged={onChanged} onError={onError} />
                    ))}
                  </div>
                )}
                {closedCases.length > 0 && (
                  <details className="mt-4 text-sm text-[#476458]">
                    <summary className="min-h-[44px] cursor-pointer py-2 font-semibold text-[#113D2E]">
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
                  <p className="text-sm text-[#476458]">No active alerts. All readings sit within this astronaut's personal band.</p>
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
