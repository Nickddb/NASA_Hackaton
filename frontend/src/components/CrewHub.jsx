import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BellRing,
  CheckCircle2,
  HeartPulse,
  Lock,
  Radio,
  Satellite,
  Scan,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Thermometer,
  Users,
  Wind,
} from "lucide-react";
import { GlassCard } from "./HomeDashboard";
import MercurySuitFigure from "./MercurySuitFigure";
import { getVitalStatuses } from "../services/api";
import {
  EnvironmentCrewChips,
  EnvironmentSectorSummary,
  METRIC_LIGHT_STYLE,
  StatusLedDot,
} from "./EnvironmentPanel";
import { PsychCrewBar } from "./PsychRankPanel";

const FILTERS = [
  { id: "ALL", label: "All Crew" },
  { id: "ISS", label: "ISS Orbital" },
  { id: "DEEP_SPACE", label: "Deep Space Mission" },
  { id: "EVA", label: "EVA Ops" },
];

const MISSION_BADGE = {
  ISS: { label: "ISS ORBITAL", cls: "border-sky-400/40 bg-sky-500/15 text-sky-200" },
  DEEP_SPACE: { label: "DEEP SPACE", cls: "border-purple-400/40 bg-purple-500/15 text-purple-200" },
  EVA: { label: "EVA ACTIVE", cls: "border-amber-400/45 bg-amber-500/15 text-amber-200" },
};

const PRESET_ALERTS = [
  { severity: "WARNING", label: "Yellow: Bio-Strain", message: "Elevated workload / heart rate drift above personal resting zone" },
  { severity: "WARNING", label: "Yellow: Cabin CO2", message: "Localized CO2 scrubber drift — verify SpO2 & respiratory baseline" },
  { severity: "CRITICAL", label: "Red: Medical Emergency", message: "Acute vital sign breach — initiate immediate CMRS triage & re-scan" },
  { severity: "CRITICAL", label: "Red: Suit / Radiation", message: "Critical EVA pressure / radiation threshold alert — shelter & scan" },
];

function StatusBadge({ status }) {
  if (status === "CRITICAL") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-red-400/70 bg-red-950/85 px-2.5 py-0.5 text-[10px] font-bold tracking-wider text-red-200 uppercase shadow-[0_0_12px_rgba(239,68,68,0.5)]">
        <span className="h-2 w-2 rounded-full bg-red-400 animate-ping" />
        CRITICAL ALERT
      </span>
    );
  }
  if (status === "WARNING") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/70 bg-amber-950/80 px-2.5 py-0.5 text-[10px] font-bold tracking-wider text-amber-200 uppercase shadow-[0_0_10px_rgba(245,158,11,0.4)]">
        <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
        WARNING ALERT
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/45 bg-emerald-950/60 px-2.5 py-0.5 text-[10px] font-bold tracking-wider text-emerald-200 uppercase">
      <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#34D399]" />
      NOMINAL
    </span>
  );
}

export default function CrewHub({
  roster,
  viewMode,
  busyAction,
  onSelectAstronaut,
  onDispatchAlert,
  onAcknowledgeAlert,
  onStabilizeCrew,
  onMeasureCrew,
}) {
  const [filter, setFilter] = useState("ALL");
  const [zoomingCrewId, setZoomingCrewId] = useState(null);
  const [alertDrawerCrewId, setAlertDrawerCrewId] = useState(null);
  const [alertSeverity, setAlertSeverity] = useState("WARNING");
  const [alertMessage, setAlertMessage] = useState("");
  const [feedbackToast, setFeedbackToast] = useState("");

  const crew = roster?.crew || [];
  const counts = roster?.summary_counts || { total: crew.length, nominal: 0, warning: 0, critical: 0, iss: 0, deep_space: 0, eva: 0 };

  const filteredCrew = useMemo(() => {
    if (filter === "ALL") return crew;
    return crew.filter((m) => m.mission_group === filter);
  }, [crew, filter]);

  const handleCardZoomAndEnter = (crewId) => {
    if (zoomingCrewId) return;
    setZoomingCrewId(crewId);
    setTimeout(() => {
      setZoomingCrewId(null);
      onSelectAstronaut(crewId);
    }, 480);
  };

  const handleSubmitAlert = async (crewId) => {
    const msg =
      alertMessage.trim() ||
      (alertSeverity === "CRITICAL"
        ? "Mission Control Critical Triage Alert — immediate stabilization & re-measurement required"
        : "Mission Control Caution Alert — monitor vitals & verify personal baseline");
    await onDispatchAlert(crewId, {
      severity: alertSeverity,
      message: msg,
      issued_by: "Mission Control (Houston)",
      simulate_vitals_drift: true,
    });
    setAlertDrawerCrewId(null);
    setAlertMessage("");
    setFeedbackToast(`Dispatched ${alertSeverity} alert to ${crewId.replace("_", " ").toUpperCase()}. Suit alert active until stabilized & verified.`);
  };

  const handleQuickMeasure = async (crewId) => {
    const res = await onMeasureCrew(crewId, "full_body");
    if (res?.reading_summary) {
      setFeedbackToast(res.reading_summary);
    }
  };

  const handleQuickStabilize = async (crewId) => {
    await onStabilizeCrew(crewId, "CHeCS protocol applied — awaiting confirmatory scan");
    setFeedbackToast("Stabilization protocol applied. Run a confirmatory measurement to verify vitals are within personal baseline.");
  };

  return (
    <div className="space-y-6">
      {/* Mode & Telemetry Banner */}
      <GlassCard className="p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300/35 bg-emerald-500/15 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-emerald-200">
                {viewMode === "control" ? <Satellite className="h-3.5 w-3.5" /> : <Users className="h-3.5 w-3.5" />}
                {viewMode === "control" ? "Mission Control Console (Earth)" : "Crew Onboard Shared Monitor (ISS / Ship)"}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-400/30 bg-sky-500/10 px-3 py-1 font-mono text-[11px] text-sky-200">
                <Radio className="h-3.5 w-3.5 text-sky-300" />
                Live Sync • SOL {roster?.mission_day ?? 142}
              </span>
            </div>
            <p className="text-xs leading-relaxed text-[#CBD5E1]">
              {viewMode === "control"
                ? "Click any astronaut spacesuit to zoom into their individual biometric & 3D anatomical cockpit, or dispatch Yellow/Red operational alerts directly."
                : "Shared live crew status across ISS and Deep Space Mission. Active alerts cannot be silenced — they only clear after stabilization and a new measurement within personal baseline."}
            </p>
          </div>

          {/* Summary KPI Pills */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="rounded-xl border border-white/15 bg-[#151922] px-3.5 py-2 text-center">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Total Crew</div>
              <div className="font-mono text-lg font-bold text-white">{counts.total}</div>
            </div>
            <div className="rounded-xl border border-emerald-400/45 bg-emerald-950/70 px-3.5 py-2 text-center">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-emerald-300">Nominal</div>
              <div className="font-mono text-lg font-bold text-emerald-200">{counts.nominal}</div>
            </div>
            <div className="rounded-xl border border-amber-400/55 bg-amber-950/75 px-3.5 py-2 text-center">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-amber-300">Warning</div>
              <div className="font-mono text-lg font-bold text-amber-200">{counts.warning}</div>
            </div>
            <div className="rounded-xl border border-red-400/65 bg-red-950/80 px-3.5 py-2 text-center">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-red-300">Critical</div>
              <div className="font-mono text-lg font-bold text-red-200">{counts.critical}</div>
            </div>
          </div>
        </div>

        {/* Location Filter Strip + Safety Lock Notice */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3.5">
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => {
              const active = filter === f.id;
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setFilter(f.id)}
                  className={`min-h-[38px] rounded-full px-4 text-xs font-semibold transition cursor-pointer ${
                    active
                      ? "bg-white text-slate-950 font-bold shadow-sm"
                      : "border border-white/15 bg-[#151922] text-slate-200 hover:border-white/35 hover:text-white"
                  }`}
                >
                  {f.label}
                </button>
              );
            })}
          </div>

          <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/40 bg-[#171209] px-3 py-1.5 text-[11px] text-amber-200">
            <Lock className="h-3.5 w-3.5 text-amber-300" />
            <span>Alert Lock: No manual silence — re-measure within personal baseline required</span>
          </div>
        </div>

        {feedbackToast && (
          <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-sky-400/40 bg-[#131924] px-3.5 py-2 font-mono text-xs text-slate-100">
            <span>{feedbackToast}</span>
            <button
              type="button"
              onClick={() => setFeedbackToast("")}
              className="text-slate-300 hover:text-white cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}
      </GlassCard>

      {/* Unified Habitat & Cabin Environmental Telemetry by Sector */}
      <EnvironmentSectorSummary crew={filteredCrew} />

      {/* Astronauts Full-Body Pedestal Grid */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {filteredCrew.map((member) => {
          const isZooming = zoomingCrewId === member.crew_id;
          const isDimmed = zoomingCrewId && !isZooming;
          const badge = MISSION_BADGE[member.mission_group] || MISSION_BADGE.ISS;
          const drawerOpen = alertDrawerCrewId === member.crew_id;

          const cardAlertClass =
            member.status === "CRITICAL"
              ? "suit-card-critical border-red-500/85 bg-gradient-to-b from-[#23090E] via-[#130C10] to-[#0E1218] shadow-[0_0_24px_rgba(239,68,68,0.28)]"
              : member.status === "WARNING"
              ? "suit-card-warning border-amber-400/80 bg-gradient-to-b from-[#221707] via-[#14110B] to-[#0E1218] shadow-[0_0_20px_rgba(245,158,11,0.24)]"
              : "border-white/15 bg-[#0E1218] hover:border-white/35";

          return (
            <div
              key={member.crew_id}
              className={`group relative flex flex-col justify-between overflow-hidden rounded-3xl border p-5 backdrop-blur-md transition-all duration-500 ${cardAlertClass} ${
                isZooming ? "scale-[1.06] z-30 shadow-[0_0_60px_rgba(56,189,248,0.6)]" : ""
              } ${isDimmed ? "opacity-35 scale-[0.98]" : ""}`}
            >
              {/* Zoom Target Reticle Overlay when Clicked */}
              {isZooming && (
                <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center bg-sky-500/10 backdrop-blur-[1px]">
                  <div className="rounded-full border-2 border-emerald-300 bg-[#041022]/90 px-4 py-1.5 font-mono text-xs font-bold tracking-widest text-emerald-200 uppercase shadow-[0_0_24px_rgba(52,211,153,0.75)]">
                    LOCKING TELEMETRY → {member.callsign}
                  </div>
                </div>
              )}

              {/* Top Meta Strip */}
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wider ${badge.cls}`}>
                    {badge.label}
                  </span>
                  <StatusBadge status={member.status} />
                </div>

                <div className="mt-2.5 flex items-baseline justify-between gap-2">
                  <div>
                    <h3 className="text-lg font-bold tracking-tight text-white">{member.name}</h3>
                    <div className="text-xs text-[#94A3B8]">
                      {member.role} • <span className="text-sky-200">{member.location_module}</span>
                    </div>
                  </div>
                </div>

                {/* Clickable Full-Body Mercury Spacesuit Pedestal */}
                <button
                  type="button"
                  onClick={() => handleCardZoomAndEnter(member.crew_id)}
                  className="relative mt-3 flex w-full flex-col items-center justify-center rounded-2xl border border-white/12 bg-[#07090D] py-3 transition hover:border-white/30 hover:bg-[#0B0E14] cursor-pointer"
                  title={`Zoom in and open ${member.name}'s telemetry dashboard`}
                >
                  <MercurySuitFigure
                    status={member.status}
                    accentColor={member.suit_accent}
                    callsign={member.callsign}
                    zooming={isZooming}
                  />
                  <span className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-slate-300 opacity-90 transition group-hover:text-white group-hover:opacity-100">
                    Click suit to zoom &amp; inspect vitals <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </button>

                {/* Quick Vitals Snapshot with Per-Metric Red/Yellow Light Indicators */}
                {(() => {
                  const metricSt = getVitalStatuses(member.vitals, member.personal_baseline);
                  const quickMetrics = [
                    {
                      key: "hr",
                      label: "HR",
                      Icon: HeartPulse,
                      defaultIcon: "text-rose-300",
                      value: Math.round(member.vitals.heart_rate_bpm),
                      valClass: "text-sm",
                      range: `${member.personal_baseline.hr_min}-${member.personal_baseline.hr_max}`,
                      status: metricSt.hr,
                    },
                    {
                      key: "spo2",
                      label: "SpO₂",
                      Icon: Wind,
                      defaultIcon: "text-sky-300",
                      value: `${Math.round(member.vitals.spo2_pct)}%`,
                      valClass: "text-sm",
                      range: `≥${member.personal_baseline.spo2_min}%`,
                      status: metricSt.spo2,
                    },
                    {
                      key: "temp",
                      label: "Temp",
                      Icon: Thermometer,
                      defaultIcon: "text-amber-300",
                      value: `${member.vitals.temperature_c.toFixed(1)}°`,
                      valClass: "text-sm",
                      range: `${member.personal_baseline.temp_min}-${member.personal_baseline.temp_max}`,
                      status: metricSt.temp,
                    },
                    {
                      key: "bp",
                      label: "BP",
                      Icon: Activity,
                      defaultIcon: "text-emerald-300",
                      value: `${Math.round(member.vitals.bp_systolic)}/${Math.round(member.vitals.bp_diastolic)}`,
                      valClass: "text-xs",
                      range: `${member.personal_baseline.bp_sys_min}-${member.personal_baseline.bp_sys_max}`,
                      status: metricSt.bp,
                    },
                  ];
                  return (
                    <div className="mt-3.5 grid grid-cols-4 gap-2 text-center">
                      {quickMetrics.map((m) => {
                        const st = METRIC_LIGHT_STYLE[m.status] || METRIC_LIGHT_STYLE.NOMINAL;
                        const MetricIcon = m.Icon;
                        return (
                          <div
                            key={m.key}
                            className={`relative rounded-xl border px-2 py-2 transition-colors ${st.card}`}
                          >
                            <span className="absolute right-1.5 top-1.5">
                              <StatusLedDot status={m.status} />
                            </span>
                            <div className={`flex items-center justify-center gap-1 text-[10px] ${st.label}`}>
                              <MetricIcon className={`h-3 w-3 ${st.iconColor || m.defaultIcon}`} /> {m.label}
                            </div>
                            <div className={`mt-0.5 font-mono font-bold ${m.valClass} ${st.value}`}>
                              {m.value}
                            </div>
                            <div className={`text-[9px] ${st.sub}`}>{m.range}</div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}

                {/* Per-Astronaut Cabin & Suit Environmental Sensors */}
                <EnvironmentCrewChips member={member} />

                {/* Psychological Readiness Rank & Tier */}
                <PsychCrewBar member={member} />

                {/* Personal Normality & Active Alert Status */}
                <div className="mt-3 space-y-2">
                  {member.within_personal_baseline ? (
                    <div className="flex items-center gap-2 rounded-xl border border-emerald-400/30 bg-emerald-950/40 px-3 py-1.5 text-[11px] text-emerald-200">
                      <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-emerald-300" />
                      <span>All vitals within personal normality</span>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-amber-400/40 bg-amber-950/35 px-3 py-2 text-[11px] text-amber-100">
                      <div className="flex items-center gap-1.5 font-semibold text-amber-200">
                        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                        Outside Personal Baseline ({member.baseline_deviations.length})
                      </div>
                      <div className="mt-0.5 text-[10px] text-amber-100/85">
                        {member.baseline_deviations.slice(0, 2).join(" • ")}
                      </div>
                    </div>
                  )}

                  {member.active_alert && (
                    <div
                      className={`rounded-xl border px-3 py-2 text-[11px] ${
                        member.active_alert.severity === "CRITICAL"
                          ? "border-red-400/60 bg-red-950/55 text-red-100"
                          : "border-amber-400/60 bg-amber-950/50 text-amber-100"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 font-bold uppercase tracking-wider text-[10px]">
                        <span className="flex items-center gap-1">
                          <BellRing className="h-3 w-3" />
                          {member.active_alert.origin_type === "MISSION_CONTROL_DISPATCH" ||
                          member.active_alert.source === "MISSION_CONTROL"
                            ? "Mission Control Alert"
                            : "Auto-Triage Alert"}
                        </span>
                        {member.active_alert.acknowledged_by_crew && (
                          <span className="rounded-full bg-white/15 px-2 py-0.5 text-[9px] text-white">
                            Crew Ack
                          </span>
                        )}
                      </div>
                      <p className="mt-1 leading-snug">{member.active_alert.message}</p>
                      {member.pending_verification_measurement && (
                        <div className="mt-1.5 flex items-center gap-1 text-[10px] font-semibold text-sky-200">
                          <Sparkles className="h-3 w-3" />
                          Stabilized — Run confirmatory scan to verify &amp; clear alert
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Role-Aware Action Footer */}
              <div className="mt-4 space-y-2.5 border-t border-white/10 pt-3.5">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleCardZoomAndEnter(member.crew_id)}
                    className="flex min-h-[38px] flex-1 items-center justify-center gap-1.5 rounded-xl bg-sky-600 px-3 text-xs font-semibold text-white shadow-sm transition hover:bg-sky-500 cursor-pointer"
                  >
                    Open Cockpit <ArrowRight className="h-3.5 w-3.5" />
                  </button>

                  {viewMode === "control" ? (
                    <button
                      type="button"
                      disabled={busyAction}
                      onClick={() => {
                        setAlertDrawerCrewId(drawerOpen ? null : member.crew_id);
                        setAlertSeverity("WARNING");
                        setAlertMessage("");
                      }}
                      className={`flex min-h-[38px] items-center gap-1.5 rounded-xl border px-3 text-xs font-semibold transition cursor-pointer ${
                        drawerOpen
                          ? "border-amber-300 bg-amber-500/25 text-amber-100"
                          : "border-white/20 bg-[#151922] text-slate-200 hover:border-amber-300/60 hover:text-white"
                      }`}
                    >
                      <ShieldAlert className="h-3.5 w-3.5 text-amber-300" />
                      Emit Alert
                    </button>
                  ) : (
                    member.active_alert && (
                      <button
                        type="button"
                        disabled={busyAction || member.active_alert.acknowledged_by_crew}
                        onClick={() => onAcknowledgeAlert(member.crew_id)}
                        className={`flex min-h-[38px] items-center gap-1.5 rounded-xl border px-3 text-xs font-semibold transition ${
                          member.active_alert.acknowledged_by_crew
                            ? "border-white/15 bg-white/5 text-slate-300 cursor-default"
                            : "border-amber-300/50 bg-amber-500/20 text-amber-100 hover:bg-amber-500/30 cursor-pointer"
                        }`}
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        {member.active_alert.acknowledged_by_crew ? "Acknowledged" : "Acknowledge"}
                      </button>
                    )
                  )}
                </div>

                {/* Quick Stabilization + Confirmatory Measurement Strip when Alert Active */}
                {viewMode === "control" && member.active_alert && (
                  <div className="flex flex-wrap gap-2">
                    {!member.within_personal_baseline && (
                      <button
                        type="button"
                        disabled={busyAction}
                        onClick={() => handleQuickStabilize(member.crew_id)}
                        className="flex min-h-[34px] flex-1 items-center justify-center gap-1 rounded-lg border border-emerald-400/45 bg-emerald-500/15 px-2.5 text-[11px] font-semibold text-emerald-200 transition hover:bg-emerald-500/25 cursor-pointer"
                      >
                        <Sparkles className="h-3 w-3" /> Apply Stabilization
                      </button>
                    )}
                    <button
                      type="button"
                      disabled={busyAction}
                      onClick={() => handleQuickMeasure(member.crew_id)}
                      className="flex min-h-[34px] flex-1 items-center justify-center gap-1 rounded-lg border border-sky-400/45 bg-sky-500/15 px-2.5 text-[11px] font-semibold text-sky-200 transition hover:bg-sky-500/25 cursor-pointer"
                    >
                      <Scan className="h-3 w-3" /> Re-Measure
                    </button>
                  </div>
                )}

                {/* Mission Control Inline Alert Dispatcher */}
                {viewMode === "control" && drawerOpen && (
                  <div className="rounded-2xl border border-amber-400/45 bg-[#090C11] p-3 space-y-2.5">
                    <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-amber-200">
                      <span>Dispatch Alert to {member.callsign}</span>
                      <button
                        type="button"
                        onClick={() => setAlertDrawerCrewId(null)}
                        className="text-slate-400 hover:text-white cursor-pointer"
                      >
                        ✕
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setAlertSeverity("WARNING")}
                        className={`rounded-lg border py-1.5 text-xs font-bold transition cursor-pointer ${
                          alertSeverity === "WARNING"
                            ? "border-amber-400 bg-amber-500/25 text-amber-100"
                            : "border-white/10 bg-white/5 text-slate-300"
                        }`}
                      >
                        Yellow (Warning)
                      </button>
                      <button
                        type="button"
                        onClick={() => setAlertSeverity("CRITICAL")}
                        className={`rounded-lg border py-1.5 text-xs font-bold transition cursor-pointer ${
                          alertSeverity === "CRITICAL"
                            ? "border-red-400 bg-red-500/30 text-red-100"
                            : "border-white/10 bg-white/5 text-slate-300"
                        }`}
                      >
                        Red (Critical)
                      </button>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {PRESET_ALERTS.map((preset) => (
                        <button
                          key={preset.label}
                          type="button"
                          onClick={() => {
                            setAlertSeverity(preset.severity);
                            setAlertMessage(preset.message);
                          }}
                          className="rounded-full border border-white/15 bg-white/5 px-2.5 py-0.5 text-[10px] text-slate-200 hover:border-sky-300/50 cursor-pointer"
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>

                    <input
                      type="text"
                      value={alertMessage}
                      onChange={(e) => setAlertMessage(e.target.value)}
                      placeholder="Alert reason (optional)..."
                      className="w-full rounded-xl border border-white/15 bg-[#151922] px-3 py-1.5 text-xs text-white placeholder-slate-400 focus:border-sky-400 focus:outline-none"
                    />

                    <button
                      type="button"
                      disabled={busyAction}
                      onClick={() => handleSubmitAlert(member.crew_id)}
                      className={`w-full rounded-xl py-2 text-xs font-bold text-white transition cursor-pointer ${
                        alertSeverity === "CRITICAL"
                          ? "bg-red-600 hover:bg-red-500"
                          : "bg-amber-600 hover:bg-amber-500"
                      }`}
                    >
                      Trigger {alertSeverity} Suit Alert
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
