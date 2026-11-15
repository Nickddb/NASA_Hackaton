import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  Droplet,
  Footprints,
  HeartPulse,
  Heart,
  MapPin,
  Moon,
  PersonStanding,
  Scan,
  ShieldCheck,
  Shirt,
  Sparkles,
  Stethoscope,
  Thermometer,
  Wind,
  Hand,
  Pause,
  Play,
  RefreshCw,
  Sun,
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ANATOMICAL_PARTS_META, HoloBodyCanvas } from "./BodyModel3D";
import { getVitalStatuses } from "../services/api";
import { EnvironmentCockpitPanel } from "./EnvironmentPanel";
import { PsychCockpitCard } from "./PsychRankPanel";

/* ---------- status helpers ---------- */

const STATUS_STYLE = {
  NORMAL: { dot: "bg-[#22C55E]", text: "text-[#4ADE80]", label: "Normal" },
  EXCELLENT: { dot: "bg-[#22C55E]", text: "text-[#4ADE80]", label: "Excellent" },
  WARNING: { dot: "bg-[#F59E0B] animate-pulse", text: "text-[#FBBF24]", label: "Attention" },
  CRITICAL: { dot: "bg-[#EF4444] animate-pulse", text: "text-[#F87171]", label: "Critical" },
};

const CARD_LIGHT_SURFACE = {
  CRITICAL: {
    card: "!border-red-500/85 !bg-[#1A090C] !shadow-[0_0_20px_rgba(239,68,68,0.42)] hover:!border-red-400",
    led: "bg-red-500 shadow-[0_0_10px_3px_rgba(239,68,68,0.95)]",
    ping: true,
    icon: "text-red-400",
    value: "text-red-200",
    chartStroke: "#EF4444",
    badge: "border-red-400/75 bg-red-950/90 text-red-100",
  },
  WARNING: {
    card: "!border-amber-400/85 !bg-[#191206] !shadow-[0_0_18px_rgba(245,158,11,0.34)] hover:!border-amber-300",
    led: "bg-amber-400 shadow-[0_0_10px_2px_rgba(245,158,11,0.9)] animate-pulse",
    ping: false,
    icon: "text-amber-300",
    value: "text-amber-200",
    chartStroke: "#F59E0B",
    badge: "border-amber-400/75 bg-amber-950/90 text-amber-100",
  },
};

function toDashStatus(status) {
  if (status === "CRITICAL") return "CRITICAL";
  if (status === "WARNING") return "WARNING";
  return "NORMAL";
}

function sleepQuality(v) {
  const hoursScore = Math.min(1, v.sleep_hours / 7.5);
  const remScore = Math.min(1, (v.rem_sleep_pct ?? 20) / 20);
  return Math.round((hoursScore * 0.75 + remScore * 0.25) * 100);
}

function buildVitals(v, pb) {
  const sq = sleepQuality(v);
  const ms = getVitalStatuses(v, pb);
  const sleepStatus =
    ms.sleep !== "NOMINAL" ? ms.sleep : sq >= 90 ? "EXCELLENT" : sq >= 70 ? "NORMAL" : sq >= 55 ? "WARNING" : "CRITICAL";
  return [
    {
      id: "hr",
      label: "Heart Rate",
      icon: HeartPulse,
      value: Math.round(v.heart_rate_bpm),
      unit: "bpm",
      status: toDashStatus(ms.hr),
      system: "cardiovascular",
    },
    {
      id: "bp",
      label: "Blood Pressure",
      icon: Droplet,
      value: `${Math.round(v.bp_systolic)} / ${Math.round(v.bp_diastolic)}`,
      unit: "mmHg",
      status: toDashStatus(ms.bp),
      system: "cardiovascular",
    },
    {
      id: "temp",
      label: "Body Temperature",
      icon: Thermometer,
      value: v.temperature_c.toFixed(1),
      unit: "°C",
      status: toDashStatus(ms.temp),
      system: "respiratory",
    },
    {
      id: "spo2",
      label: "Oxygenation (SpO₂)",
      icon: Activity,
      value: Math.round(v.spo2_pct ?? 98),
      unit: "%",
      status: toDashStatus(ms.spo2),
      system: "respiratory",
    },
    {
      id: "rr",
      label: "Respiratory Rate",
      icon: Wind,
      value: Math.round(v.respiration_rpm ?? 14),
      unit: "rpm",
      status: toDashStatus(ms.rr),
      system: "respiratory",
    },
    {
      id: "sleep",
      label: "Sleep Quality",
      icon: Moon,
      value: sq,
      unit: "%",
      status: sleepStatus,
      system: "nervous_sleep",
    },
  ];
}

/* ---------- body regions (right column) ---------- */

export function buildRegions(v, pb) {
  const ms = getVitalStatuses(v, pb);
  return [
    {
      id: "head",
      label: "Head",
      icon: Brain,
      system: "nervous_sleep",
      exam: "Sleep & Cognition",
      location: "Head (EEG headband)",
      reading: `${v.sleep_hours.toFixed(1)} h sleep`,
      status: toDashStatus(ms.sleep),
    },
    {
      id: "chest",
      label: "Chest",
      icon: Shirt,
      system: "cardiovascular",
      exam: "Heart Rate",
      location: "Chest (ECG patch)",
      reading: `${Math.round(v.heart_rate_bpm)} bpm`,
      status: toDashStatus(ms.hr),
    },
    {
      id: "arm",
      label: "Arm",
      icon: Hand,
      system: "cardiovascular",
      exam: "Blood Pressure",
      location: "Left Arm",
      reading: `${Math.round(v.bp_systolic)} / ${Math.round(v.bp_diastolic)} mmHg`,
      status: toDashStatus(ms.bp),
    },
    {
      id: "leg",
      label: "Leg",
      icon: Footprints,
      system: "musculoskeletal",
      exam: "Bone & Muscle Load",
      location: "Leg (urinary Ca proxy)",
      reading: `${Math.round(v.urinary_calcium_mg_d ?? 185)} mg/d Ca`,
      status: (v.urinary_calcium_mg_d ?? 185) > 250 ? "WARNING" : "NORMAL",
    },
    {
      id: "full",
      label: "Full Body",
      icon: PersonStanding,
      system: "radiation",
      exam: "Radiation Dose",
      location: "Full Body (dosimeter)",
      reading: `${v.radiation_msv_h.toFixed(2)} mSv/h`,
      status: toDashStatus(ms.radiation),
    },
  ];
}

/* ---------- small building blocks ---------- */

export function GlassCard({ className = "", children }) {
  return (
    <div
      className={`rounded-2xl border border-white/15 bg-[#0E1218] shadow-[0_12px_32px_rgba(0,0,0,0.65)] ${className}`}
    >
      {children}
    </div>
  );
}

function StatusLine({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.NORMAL;
  return (
    <div className={`mt-2 flex items-center gap-1.5 text-[11px] font-medium ${s.text}`}>
      <span className={`h-2 w-2 rounded-full ${s.dot}`} />
      {s.label}
    </div>
  );
}

function VitalCard({ item, onClick }) {
  const Icon = item.icon;
  const alertSurface = CARD_LIGHT_SURFACE[item.status];
  return (
    <button type="button" onClick={onClick} className="text-left">
      <GlassCard
        className={`relative h-full p-4 transition ${
          alertSurface ? alertSurface.card : "hover:border-white/35 hover:bg-[#141922]"
        }`}
      >
        {alertSurface && (
          <span className="absolute right-3 top-3 flex h-2.5 w-2.5 items-center justify-center">
            {alertSurface.ping && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-85" />
            )}
            <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${alertSurface.led}`} />
          </span>
        )}
        <Icon className={`h-7 w-7 ${alertSurface ? alertSurface.icon : "text-sky-300"}`} strokeWidth={1.4} />
        <div className="mt-3 text-[11px] text-slate-300">{item.label}</div>
        <div className={`mt-1 font-sans text-2xl font-semibold ${alertSurface ? alertSurface.value : "text-white"}`}>
          {item.value}
          <span className="ml-1 text-sm font-normal text-slate-400">{item.unit}</span>
        </div>
        <StatusLine status={item.status} />
      </GlassCard>
    </button>
  );
}

const RANGES = ["Live", "7 days"];

// Real data only: "Live" = readings received from the backend generator this session,
// "7 days" = the generator's daily longitudinal series (state.longitudinal_series).
function TrendChart({
  title,
  icon: Icon,
  unit,
  live = [],
  daily = [],
  domain,
  ticks,
  color = "#60A5FA",
  label,
  status = "NORMAL",
}) {
  const [range, setRange] = useState("7 days");
  const data = range === "Live" ? live : daily;
  const last = data[data.length - 1];
  const gid = `grad-${title.replace(/\s/g, "")}`;
  const alertSurface = CARD_LIGHT_SURFACE[status];
  const strokeColor = alertSurface ? alertSurface.chartStroke : color;

  return (
    <GlassCard className={`p-4 transition ${alertSurface ? alertSurface.card : ""}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Icon className={`h-5 w-5 ${alertSurface ? alertSurface.icon : "text-sky-300"}`} strokeWidth={1.6} />
          <h3 className="text-base font-medium text-white">{title}</h3>
          {alertSurface && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-black/50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white">
              <span className="relative flex h-2 w-2 items-center justify-center">
                {alertSurface.ping && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-85" />
                )}
                <span className={`relative inline-flex h-2 w-2 rounded-full ${alertSurface.led}`} />
              </span>
              {status === "CRITICAL" ? "Critical" : "Alert"}
            </span>
          )}
        </div>
        <div className="flex gap-1" role="group" aria-label={`${title} range`}>
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              aria-pressed={range === r}
              onClick={() => setRange(r)}
              className={`min-h-[32px] rounded-lg px-3 py-1 text-xs font-medium transition cursor-pointer ${
                range === r
                  ? "bg-white text-slate-950 font-bold shadow-sm"
                  : "border border-white/10 bg-[#151922] text-slate-300 hover:border-white/30 hover:text-white"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="relative mt-2 h-[130px]">
        {data.length < 2 ? (
          <p className="flex h-full items-center justify-center px-6 text-center text-xs text-slate-400">
            {range === "Live"
              ? "No live readings yet. Start the sensor stream or take a new reading."
              : "No daily history for this astronaut yet."}
          </p>
        ) : (
          <>
            <span
              className={`absolute right-2 top-1 z-10 rounded-lg border px-2 py-0.5 text-[11px] font-semibold ${
                alertSurface ? alertSurface.badge : "border-white/20 bg-[#151922] text-white"
              }`}
            >
              {label ?? `${last.value} ${unit}`}
            </span>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={strokeColor} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#252A36" strokeOpacity={0.85} />
                <XAxis dataKey="t" stroke="#94A3B8" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis domain={domain} ticks={ticks} stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: "#0A0D12", border: "1px solid rgba(255,255,255,0.22)", borderRadius: 10, color: "#fff", fontSize: 12 }}
                  formatter={(val) => [`${val} ${unit}`, title]}
                  labelStyle={{ color: "#94A3B8" }}
                />
                <Area type="monotone" dataKey="value" stroke={strokeColor} strokeWidth={2.2} fill={`url(#${gid})`} isAnimationActive={false} />
                <ReferenceDot x={last.t} y={last.value} r={4} fill="#fff" stroke={strokeColor} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </>
        )}
      </div>
    </GlassCard>
  );
}

const DONKI_TONE = {
  NOMINAL: "border-[#34D399]/40 text-[#A7F3D0]",
  WARNING: "border-[#FBBF24]/60 text-[#FDE68A]",
  CRITICAL: "border-[#F87171]/70 text-[#FECACA]",
};
const SOURCE_LABEL = {
  live_nasa_donki: "Live NASA DONKI",
  cached_nasa_donki: "Cached NASA DONKI",
  curated_local_fallback: "Offline sample (DONKI format)",
};

// Secondary strip: external space weather (DONKI SEP / FLR / RBE) + sensor stream controls.
function MissionTelemetryBar({ sw, refreshing, onRefresh, streaming, onToggleStream, onNextReading, live }) {
  const level = sw?.alert_level || "NOMINAL";
  const simulated = sw?.events?.some((e) => e.is_active && e.origin === "scenario_simulation");
  const ctl =
    "inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-white/15 bg-[#151922] px-3 text-xs text-slate-200 hover:border-white/35 hover:text-white disabled:opacity-50 cursor-pointer";
  return (
    <GlassCard className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-3">
      <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
        <Sun className="h-5 w-5 shrink-0 text-[#FDE68A]" strokeWidth={1.6} />
        <span className="text-sm text-slate-300">Space weather</span>
        <span className={`inline-flex items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${DONKI_TONE[level]}`}>
          {sw?.status_label || "Unknown"}
        </span>
        {sw && (
          <span className="font-mono text-[11px] text-slate-400">
            SEP {sw.active_sep_count} · FLR {sw.active_flare_count} · RBE {sw.active_rbe_count ?? 0} in {sw.active_window_hours ?? 72} h
          </span>
        )}
        {simulated && <span className="text-[11px] text-[#FDE68A]">includes a scenario drill event</span>}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] text-slate-400" title={sw?.fetch_status}>
          {SOURCE_LABEL[sw?.source] || "DONKI"}
          {sw?.uses_demo_key ? " · DEMO_KEY" : ""}
        </span>
        <button type="button" onClick={onRefresh} disabled={refreshing || !live} className={ctl}>
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} /> {refreshing ? "Querying" : "Refresh DONKI"}
        </button>
        <span className="mx-1 hidden h-5 w-px bg-white/15 sm:block" />
        <button type="button" onClick={onNextReading} disabled={!live || streaming} className={ctl}>
          New reading
        </button>
        <button
          type="button"
          onClick={onToggleStream}
          disabled={!live}
          aria-pressed={streaming}
          className={`inline-flex min-h-[36px] items-center gap-1.5 rounded-full px-3 text-xs font-semibold disabled:opacity-50 cursor-pointer ${
            streaming ? "bg-[#10B981] text-[#04231F]" : "bg-sky-600 text-white hover:bg-sky-500"
          }`}
        >
          {streaming ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          {streaming ? "Streaming every 5 s" : "Start sensor stream"}
        </button>
      </div>
    </GlassCard>
  );
}

/* ---------- main home dashboard ---------- */

function buildPartDetails(v, pb) {
  const ms = getVitalStatuses(v, pb);
  const bpSt = toDashStatus(ms.bp);
  const hrSt = toDashStatus(ms.hr);
  const sleepSt = toDashStatus(ms.sleep);
  const shStatus = (v.shoulder_pain_score ?? 0) >= 4 ? "WARNING" : "NORMAL";
  const caStatus = (v.urinary_calcium_mg_d ?? 185) > 250 ? "WARNING" : "NORMAL";
  const gluStatus = toDashStatus(ms.glucose);
  const spo2Status = toDashStatus(ms.spo2);

  return {
    head: { exam: "Neuro & Intraocular Pressure (SANS)", location: "Cabeça & Crânio (EEG / Tonometria)", reading: `${v.sleep_hours.toFixed(1)}h sono | PIO ${(v.intraocular_pressure_mmhg ?? 15.2).toFixed(1)} mmHg`, status: sleepSt },
    neck: { exam: "Fluxo Carotídeo & Termografia", location: "Pescoço & Cervical", reading: `${v.temperature_c.toFixed(1)} °C | ${Math.round(v.respiration_rpm ?? 14)} rpm`, status: "NORMAL" },
    chest: { exam: "Cardiopulmonar (ECG & Respiração)", location: "Tórax & Peitoral", reading: `${Math.round(v.heart_rate_bpm)} bpm | HRV ${Math.round(v.hrv_ms)} ms`, status: hrSt },
    abdomen: { exam: "Metabólico & Glicemia Capilar", location: "Abdômen & Core", reading: `${Math.round(v.glucose_mg_dl)} mg/dL`, status: gluStatus },
    pelvis: { exam: "Densidade Óssea & Cálcio Renal", location: "Pelve & Quadril", reading: `${Math.round(v.urinary_calcium_mg_d ?? 185)} mg/d Ca`, status: caStatus },
    left_shoulder: { exam: "Biomecânica EVA (OCHMO-MTB-006)", location: "Ombro / Deltoide Esquerdo", reading: `Dor EVA ${v.shoulder_pain_score ?? 0}/10`, status: shStatus },
    right_shoulder: { exam: "Biomecânica EVA (OCHMO-MTB-006)", location: "Ombro / Deltoide Direito", reading: `Dor EVA ${v.shoulder_pain_score ?? 0}/10`, status: shStatus },
    left_upper_arm: { exam: "Pressão Arterial (Manguito NIBP)", location: "Braço Esquerdo (Bíceps)", reading: `${Math.round(v.bp_systolic)} / ${Math.round(v.bp_diastolic)} mmHg`, status: bpSt },
    right_upper_arm: { exam: "Pressão Arterial (Manguito NIBP)", location: "Braço Direito (Bíceps)", reading: `${Math.round(v.bp_systolic)} / ${Math.round(v.bp_diastolic)} mmHg`, status: bpSt },
    left_forearm: { exam: "Pulso Radial & Smartwatch PPG", location: "Antebraço Esquerdo", reading: `${Math.round(v.heart_rate_bpm)} bpm | ${Math.round(v.hrv_ms)} ms`, status: hrSt },
    right_forearm: { exam: "Pulso Radial & Periférico", location: "Antebraço Direito", reading: `${Math.round(v.heart_rate_bpm)} bpm`, status: hrSt },
    left_hand: { exam: "Oximetria de Pulso Capilar (SpO₂)", location: "Mão Esquerda", reading: `${Math.round(v.spo2_pct ?? 98)}% SpO₂`, status: spo2Status },
    right_hand: { exam: "Oximetria de Pulso Capilar (SpO₂)", location: "Mão Direita", reading: `${Math.round(v.spo2_pct ?? 98)}% SpO₂`, status: spo2Status },
    left_thigh: { exam: "Carga Muscular (ARED Quadríceps)", location: "Coxa Esquerda", reading: `${Math.round(v.urinary_calcium_mg_d ?? 185)} mg/d Ca`, status: caStatus },
    right_thigh: { exam: "Carga Muscular (ARED Quadríceps)", location: "Coxa Direita", reading: `${Math.round(v.urinary_calcium_mg_d ?? 185)} mg/d Ca`, status: caStatus },
    left_calf: { exam: "Retorno Venoso & Fluid Shift", location: "Panturrilha Esquerda", reading: `${Math.round(v.bp_systolic)} / ${Math.round(v.bp_diastolic)} mmHg`, status: bpSt },
    right_calf: { exam: "Retorno Venoso & Fluid Shift", location: "Panturrilha Direita", reading: `${Math.round(v.bp_systolic)} / ${Math.round(v.bp_diastolic)} mmHg`, status: bpSt },
    left_foot: { exam: "Perfusão Distal & Sensibilidade", location: "Pé Esquerdo", reading: `${v.temperature_c.toFixed(1)} °C | ${Math.round(v.spo2_pct ?? 98)}%`, status: spo2Status },
    right_foot: { exam: "Perfusão Distal & Sensibilidade", location: "Pé Direito", reading: `${v.temperature_c.toFixed(1)} °C | ${Math.round(v.spo2_pct ?? 98)}%`, status: spo2Status },
  };
}

export default function HomeDashboard({
  state,
  busyAction = false,
  onTriggerMeasurement,
  onSelectSystem,
  onStabilizeCrew,
  onSwitchEnvironment,
  liveReadings = [],
  streaming = false,
  onToggleStream,
  onNextReading,
  onRefreshDonki,
  donkiRefreshing = false,
  live = false,
}) {
  const [regionId, setRegionId] = useState("arm");
  const [selectedPartId, setSelectedPartId] = useState("left_upper_arm");
  const [measuring, setMeasuring] = useState(false);
  const [stabilizing, setStabilizing] = useState(false);
  const [lastReading, setLastReading] = useState(null);

  const v = state?.vitals;
  if (!v) return null;

  const pb = state?.personal_baseline;
  const metricStatuses = getVitalStatuses(v, pb);
  const vitals = buildVitals(v, pb);
  const regions = buildRegions(v, pb);
  const region = regions.find((r) => r.id === regionId) || regions[2];
  const partDetailsMap = buildPartDetails(v, pb);
  const activePartDetail = selectedPartId ? partDetailsMap[selectedPartId] : null;
  const activePartMeta = selectedPartId ? ANATOMICAL_PARTS_META[selectedPartId] : null;

  const displayExam = activePartDetail?.exam || region.exam;
  const displayLocation = activePartDetail?.location || region.location;
  const displayReading = activePartDetail?.reading || region.reading;
  const displayStatus = activePartDetail?.status || region.status;
  const activeSystemId = activePartMeta?.systemId || region.system;

  const selectRegion = (r) => {
    setRegionId(r.id);
    setSelectedPartId(null);
    setLastReading(null);
    onSelectSystem?.(r.system);
  };

  const handleSelectPart3D = (partId, meta) => {
    setSelectedPartId(partId);
    if (meta?.regionId) setRegionId(meta.regionId);
    setLastReading(null);
    if (meta?.systemId) onSelectSystem?.(meta.systemId);
  };

  const runScan = async (overrideSystemId = null) => {
    const targetSystem = typeof overrideSystemId === "string" ? overrideSystemId : activeSystemId;
    setMeasuring(true);
    try {
      const res = await onTriggerMeasurement(targetSystem);
      setLastReading(res);
    } finally {
      setMeasuring(false);
    }
  };

  const dailySeries = (key) =>
    (state.longitudinal_series || [])
      .filter((r) => typeof r[key] === "number")
      .map((r) => ({ t: r.day, value: Math.round(r[key] * 10) / 10 }));

  const runStabilization = async () => {
    if (!onStabilizeCrew) return;
    setStabilizing(true);
    try {
      await onStabilizeCrew(state.crew_id || state.astronaut_id);
      setLastReading({
        reading_summary: "Stabilization protocol applied. Run a confirmatory scan to verify vitals within personal baseline.",
      });
    } finally {
      setStabilizing(false);
    }
  };

  const sys = Math.round(v.bp_systolic);
  const dia = Math.round(v.bp_diastolic);
  const hasAlert = Boolean(state?.active_alert) || state?.within_personal_baseline === false || state?.pending_verification_measurement;

  return (
    <div className="flex flex-col gap-6">
      <MissionTelemetryBar
        sw={state.space_weather}
        refreshing={donkiRefreshing}
        onRefresh={onRefreshDonki}
        streaming={streaming}
        onToggleStream={onToggleStream}
        onNextReading={onNextReading}
        live={live}
      />

      {/* Personal Baseline & Alert Verification Bar */}
      {pb && (
        <GlassCard
          className={`p-4 ${
            state?.active_alert?.severity === "CRITICAL"
              ? "!border-red-500/80 !bg-[#1A090C]"
              : hasAlert
              ? "!border-amber-400/75 !bg-[#191206]"
              : "border-white/15"
          }`}
        >
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                {state?.within_personal_baseline && !state?.active_alert ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/45 bg-emerald-500/15 px-3 py-0.5 text-[11px] font-bold text-emerald-200">
                    <ShieldCheck className="h-3.5 w-3.5" /> Personal Normality Verified
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/55 bg-amber-500/20 px-3 py-0.5 text-[11px] font-bold text-amber-200">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {state?.pending_verification_measurement
                      ? "Stabilized — Confirmatory Measurement Required"
                      : "Alert Active — Personal Baseline Deviation"}
                  </span>
                )}
                <span className="font-mono text-[11px] text-slate-300">
                  Personal Normal: HR {pb.hr_min}-{pb.hr_max} bpm • BP {pb.bp_sys_min}-{pb.bp_sys_max} mmHg • Temp {pb.temp_min}-{pb.temp_max}°C • SpO₂ ≥{pb.spo2_min}%
                </span>
              </div>

              {state?.baseline_deviations?.length > 0 && (
                <p className="text-xs text-amber-200">
                  Out-of-baseline indicators: <span className="font-semibold">{state.baseline_deviations.join(" • ")}</span>
                </p>
              )}
              {state?.active_alert?.message && (
                <p className="text-xs text-slate-200">
                  Active Alert (
                  {state.active_alert.origin_type === "MISSION_CONTROL_DISPATCH" ||
                  state.active_alert.source === "MISSION_CONTROL"
                    ? "Mission Control"
                    : "Auto-Triage"}
                  ):{" "}
                  <span className="font-semibold text-white">{state.active_alert.message}</span>
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              {state?.within_personal_baseline === false && onStabilizeCrew && (
                <button
                  type="button"
                  disabled={stabilizing}
                  onClick={runStabilization}
                  className="flex min-h-[40px] items-center gap-1.5 rounded-xl border border-emerald-400/50 bg-emerald-500/20 px-4 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-500/30 disabled:opacity-60 cursor-pointer"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {stabilizing ? "Stabilizing..." : "Apply Stabilization Protocol"}
                </button>
              )}
              {hasAlert && (
                <button
                  type="button"
                  disabled={measuring}
                  onClick={() => runScan("full_body")}
                  className="flex min-h-[40px] items-center gap-1.5 rounded-xl bg-sky-600 px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-sky-500 disabled:opacity-60 cursor-pointer"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {measuring ? "Verifying..." : "Run Confirmatory Scan"}
                </button>
              )}
            </div>
          </div>
        </GlassCard>
      )}

      {/* Vital cards row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {vitals.map((item) => (
          <VitalCard key={item.id} item={item} onClick={() => onSelectSystem?.(item.system)} />
        ))}
      </div>

      {/* Unified Cabin & Suit Environmental Telemetry + Quick Habitat Switcher */}
      <EnvironmentCockpitPanel
        state={state}
        onSwitchEnvironment={onSwitchEnvironment}
        busyAction={busyAction}
      />

      {/* Psychological Readiness Rank & Behavioral Contributors */}
      <PsychCockpitCard state={state} />

      {/* Charts + hologram */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="flex flex-col gap-4 lg:col-span-7">
          <TrendChart
            title="Blood Pressure"
            icon={Activity}
            unit="mmHg"
            live={liveReadings.map((r) => ({ t: r.t, value: r.sys }))}
            daily={dailySeries("bp_sys")}
            domain={[Math.min(90, sys - 20), Math.max(150, sys + 20)]}
            label={`${sys} / ${dia} mmHg`}
            status={toDashStatus(metricStatuses.bp)}
          />
          <TrendChart
            title="Heart Rate"
            icon={Heart}
            unit="bpm"
            live={liveReadings.map((r) => ({ t: r.t, value: r.hr }))}
            daily={dailySeries("hr")}
            domain={[Math.min(45, Math.round(v.heart_rate_bpm) - 15), Math.max(110, Math.round(v.heart_rate_bpm) + 15)]}
            status={toDashStatus(metricStatuses.hr)}
          />

          {/* Selected exam */}
          <GlassCard className="flex flex-wrap items-center gap-5 p-5">
            <Stethoscope className="h-12 w-12 text-sky-300" strokeWidth={1.3} />
            <div className="min-w-[160px] flex-1">
              <div className="text-xs text-slate-400">Selected Exam</div>
              <div className="text-xl font-semibold text-white">{displayExam}</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-emerald-300">
                <MapPin className="h-3.5 w-3.5 text-emerald-400" /> Location: {displayLocation}
              </div>
            </div>
            <div className="hidden h-14 w-px bg-white/15 sm:block" />
            <div className="min-w-[150px]">
              <div className="text-xs text-slate-400">Latest Reading</div>
              <div className="text-xl font-semibold text-white">{displayReading}</div>
              <StatusLine status={displayStatus} />
            </div>
            <button
              type="button"
              onClick={() => runScan()}
              disabled={measuring}
              className="ml-auto flex min-h-[44px] items-center gap-2 rounded-xl bg-sky-600 px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-sky-500 disabled:opacity-60 cursor-pointer"
            >
              <Scan className="h-4 w-4" />
              {measuring ? "Scanning..." : "Run Scan"}
            </button>
            {lastReading?.reading_summary && (
              <div className="w-full rounded-xl border border-white/15 bg-[#151922] px-3 py-2 font-mono text-[11px] text-slate-200">
                {lastReading.reading_summary}
              </div>
            )}
          </GlassCard>
        </div>

        {/* Custom Procedural 3D Body + Region Selector */}
        <div className="relative flex min-h-[480px] items-stretch lg:col-span-5">
          <div className="relative flex-1">
            <div className="pointer-events-none absolute inset-x-8 bottom-6 h-24 rounded-[50%] bg-white/[0.04] blur-2xl" />
            <HoloBodyCanvas
              state={state}
              selectedSystem={activeSystemId}
              selectedRegion={regionId}
              selectedPartId={selectedPartId}
              onSelectPart={handleSelectPart3D}
              onSelectSystem={onSelectSystem}
              measuring={measuring}
            />
          </div>
          <div className="flex flex-col justify-center gap-4 pl-2">
            {regions.map((r) => {
              const Icon = r.icon;
              const active = r.id === regionId;
              return (
                <button key={r.id} type="button" onClick={() => selectRegion(r)} className="group flex flex-col items-center gap-1 cursor-pointer">
                  <span
                    className={`flex h-14 w-14 items-center justify-center rounded-full border transition ${
                      active
                        ? "border-sky-400 bg-sky-500/20 shadow-[0_0_18px_rgba(56,189,248,0.45)]"
                        : "border-white/15 bg-[#12161F] group-hover:border-white/40"
                    }`}
                  >
                    <Icon className={`h-6 w-6 ${active ? "text-white" : "text-slate-300"}`} strokeWidth={1.4} />
                  </span>
                  <span className={`text-[11px] ${active ? "font-semibold text-white" : "text-slate-400"}`}>{r.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
