import {
  AlertTriangle,
  Cloud,
  Droplets,
  Gauge,
  Globe,
  Orbit,
  Radiation,
  Rocket,
  ShieldCheck,
  Thermometer,
  Wind,
} from "lucide-react";
import { getEnvironmentStatuses } from "../services/api";

const STATUS_RANK = { NOMINAL: 0, WARNING: 1, CRITICAL: 2 };

export const METRIC_LIGHT_STYLE = {
  CRITICAL: {
    card: "border-red-500/85 bg-red-950/60 shadow-[0_0_16px_rgba(239,68,68,0.45)]",
    led: "bg-red-500 shadow-[0_0_10px_2px_rgba(239,68,68,0.95)] animate-pulse",
    ping: true,
    label: "text-red-200",
    value: "text-red-300",
    sub: "text-red-300/85",
    iconColor: "text-red-400",
  },
  WARNING: {
    card: "border-amber-400/85 bg-amber-950/50 shadow-[0_0_14px_rgba(245,158,11,0.38)]",
    led: "bg-amber-400 shadow-[0_0_9px_2px_rgba(245,158,11,0.9)] animate-pulse",
    ping: false,
    label: "text-amber-200",
    value: "text-amber-300",
    sub: "text-amber-200/85",
    iconColor: "text-amber-300",
  },
  NOMINAL: {
    card: "border-white/15 bg-[#151922]",
    led: "bg-emerald-400/85",
    ping: false,
    label: "text-slate-300",
    value: "text-white",
    sub: "text-slate-400",
    iconColor: null,
  },
};

export const ENV_SENSOR_META = {
  co2: { Icon: Cloud, defaultIcon: "text-sky-300" },
  o2: { Icon: Wind, defaultIcon: "text-emerald-300" },
  pressure: { Icon: Gauge, defaultIcon: "text-cyan-300" },
  radiation: { Icon: Radiation, defaultIcon: "text-purple-300" },
  climate: { Icon: Thermometer, defaultIcon: "text-amber-200" },
};

const SECTOR_META = {
  ISS: { label: "ISS Orbital", Icon: Orbit, accent: "border-sky-400/35 text-sky-200" },
  DEEP_SPACE: { label: "Deep Space Transit", Icon: Rocket, accent: "border-purple-400/35 text-purple-200" },
  EVA: { label: "EVA & Airlock Ops", Icon: Droplets, accent: "border-amber-400/35 text-amber-200" },
};

const FALLBACK_ENV_CATALOG = [
  { id: "orbital_station", short_label: "Orbital Station", gravity: "0g Microgravity", one_way_latency_seconds: 2 },
  { id: "transit", short_label: "Deep Space (0g)", gravity: "0g Microgravity", one_way_latency_seconds: 720 },
  { id: "planetary_surface", short_label: "Planetary Surface", gravity: "0.38g / 1/6g", one_way_latency_seconds: 380 },
];

export function StatusLedDot({ status, size = "h-2 w-2" }) {
  const st = METRIC_LIGHT_STYLE[status] || METRIC_LIGHT_STYLE.NOMINAL;
  return (
    <span className={`relative flex ${size} items-center justify-center`}>
      {st.ping && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-85" />
      )}
      <span className={`relative inline-flex ${size} rounded-full ${st.led}`} />
    </span>
  );
}

function StatusPill({ status, nominalText = "NOMINAL" }) {
  if (status === "CRITICAL") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-red-400/75 bg-red-950/85 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-red-200 shadow-[0_0_10px_rgba(239,68,68,0.45)]">
        <StatusLedDot status="CRITICAL" />
        CRITICAL ENV
      </span>
    );
  }
  if (status === "WARNING") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/75 bg-amber-950/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-200 shadow-[0_0_10px_rgba(245,158,11,0.35)]">
        <StatusLedDot status="WARNING" />
        ENV ALERT
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/40 bg-emerald-950/60 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-200">
      <StatusLedDot status="NOMINAL" />
      {nominalText}
    </span>
  );
}

function EnvMiniChipGrid({ sensors, spacingClass = "mt-2.5", chipRoundedClass = "rounded-xl px-1.5", valueTextClass = "text-[11px]" }) {
  return (
    <div className={`${spacingClass} grid grid-cols-5 gap-1.5 text-center`}>
      {sensors.map((s) => {
        const st = METRIC_LIGHT_STYLE[s.status] || METRIC_LIGHT_STYLE.NOMINAL;
        const SensorIcon = ENV_SENSOR_META[s.key]?.Icon || Gauge;
        return (
          <div
            key={s.key}
            title={`${s.label}: ${s.display} ${s.unit} (Normal ${s.range})`}
            className={`relative border py-1.5 transition-colors ${chipRoundedClass} ${st.card}`}
          >
            <span className="absolute right-1 top-1">
              <StatusLedDot status={s.status} size="h-1.5 w-1.5" />
            </span>
            <div className={`flex items-center justify-center gap-0.5 text-[9px] ${st.label}`}>
              <SensorIcon className={`h-2.5 w-2.5 ${st.iconColor || ENV_SENSOR_META[s.key]?.defaultIcon}`} />
              <span>{s.shortLabel}</span>
            </div>
            <div className={`mt-0.5 font-mono font-bold leading-tight ${valueTextClass} ${st.value}`}>
              {s.shortValue}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function EnvironmentSectorSummary({ crew = [] }) {
  const sectors = ["ISS", "DEEP_SPACE", "EVA"]
    .map((group) => {
      const members = crew.filter((m) => m.mission_group === group);
      if (!members.length) return null;

      const evals = members.map((m) => getEnvironmentStatuses(m.mission_context, m.vitals, m.personal_baseline));
      const worstByKey = {};
      let overall = "NOMINAL";

      for (const key of ["co2", "o2", "pressure", "radiation", "climate"]) {
        let pick = evals[0].sensors[key];
        for (const ev of evals) {
          const cur = ev.sensors[key];
          if ((STATUS_RANK[cur.status] || 0) > (STATUS_RANK[pick.status] || 0)) {
            pick = cur;
          } else if (cur.status === pick.status && Math.abs(cur.value) > Math.abs(pick.value)) {
            pick = cur;
          }
        }
        worstByKey[key] = pick;
        if ((STATUS_RANK[pick.status] || 0) > (STATUS_RANK[overall] || 0)) {
          overall = pick.status;
        }
      }

      const modules = Array.from(new Set(members.map((m) => m.location_module))).join(" • ");
      return {
        group,
        membersCount: members.length,
        modules,
        overall,
        sensors: ["co2", "o2", "pressure", "radiation", "climate"].map((k) => worstByKey[k]),
      };
    })
    .filter(Boolean);

  if (!sectors.length) return null;

  return (
    <div className="rounded-2xl border border-white/15 bg-[#0E1218] p-4 shadow-[0_12px_32px_rgba(0,0,0,0.65)]">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Globe className="h-4 w-4 text-sky-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-white">
            Habitat &amp; Cabin Environmental Telemetry (By Sector)
          </h2>
        </div>
        <span className="text-[11px] text-slate-400">
          Worst-case reading per active zone • Red/Yellow lights mark altered sensors
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {sectors.map((sec) => {
          const meta = SECTOR_META[sec.group] || SECTOR_META.ISS;
          const SectorIcon = meta.Icon;
          const borderHighlight =
            sec.overall === "CRITICAL"
              ? "border-red-500/80 bg-[#1B090C]"
              : sec.overall === "WARNING"
                ? "border-amber-400/75 bg-[#1A1307]"
                : "border-white/12 bg-[#12161F]";

          return (
            <div key={sec.group} className={`rounded-2xl border p-3 transition ${borderHighlight}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-white">
                    <SectorIcon className="h-3.5 w-3.5 text-sky-300 shrink-0" />
                    <span>{meta.label}</span>
                    <span className="rounded-full bg-white/10 px-1.5 py-0.5 font-mono text-[10px] text-slate-200">
                      {sec.membersCount} crew
                    </span>
                  </div>
                  <div className="mt-0.5 truncate text-[10px] text-[#94A3B8]" title={sec.modules}>
                    {sec.modules}
                  </div>
                </div>
                <StatusPill status={sec.overall} nominalText="ENV OK" />
              </div>

              <EnvMiniChipGrid sensors={sec.sensors} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function EnvironmentCrewChips({ member }) {
  const envEval = getEnvironmentStatuses(member.mission_context, member.vitals, member.personal_baseline);
  return (
    <div className="mt-2.5 rounded-2xl border border-white/12 bg-[#090C11] p-2.5">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="truncate text-[10px] font-semibold uppercase tracking-wider text-slate-300">
          Cabin Env • {member.location_module}
        </span>
        <StatusPill status={envEval.overall} nominalText="ENV OK" />
      </div>
      <EnvMiniChipGrid
        sensors={envEval.list}
        spacingClass=""
        chipRoundedClass="rounded-lg px-1"
        valueTextClass="text-[10px]"
      />
    </div>
  );
}

export function EnvironmentCockpitPanel({ state, onSwitchEnvironment, busyAction }) {
  if (!state) return null;
  const envEval = getEnvironmentStatuses(state.mission_context, state.vitals, state.personal_baseline);
  const catalog = state.environments_catalog?.length ? state.environments_catalog : FALLBACK_ENV_CATALOG;
  const latencySec = state.one_way_latency_seconds ?? 2;
  const latencyLabel = latencySec >= 60 ? `~${Math.round(latencySec / 60)} min delay` : `${latencySec}s relay`;
  const gravityLabel = state.mission_context?.gravitational_g ? `${state.mission_context.gravitational_g}g` : "0g Microgravity";

  const alteredSensors = envEval.list.filter((s) => s.status !== "NOMINAL");

  return (
    <div className="rounded-2xl border border-white/15 bg-[#0E1218] p-4 shadow-[0_12px_32px_rgba(0,0,0,0.65)]">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Globe className="h-5 w-5 text-sky-400" />
            <h3 className="text-sm font-semibold text-white">Cabin &amp; Suit Environmental Sensors</h3>
            <StatusPill status={envEval.overall} nominalText="CABIN NOMINAL" />
            <span className="rounded-full border border-white/15 bg-[#151922] px-2.5 py-0.5 font-mono text-[10px] text-slate-200">
              {gravityLabel} • {latencyLabel}
            </span>
          </div>
          <p className="text-xs text-slate-300">
            Active habitat: <span className="font-semibold text-white">{state.environment_name}</span>
            {alteredSensors.length > 0 && (
              <span className="ml-2 inline-flex items-center gap-1 text-amber-200">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-300" />
                Altered: {alteredSensors.map((s) => `${s.label} (${s.display} ${s.unit})`).join(" • ")}
              </span>
            )}
          </p>
        </div>

        {/* Quick Habitat / Environment Switcher */}
        {onSwitchEnvironment && (
          <div className="flex flex-wrap items-center gap-1.5">
            {catalog.map((env) => {
              const active = state.environment_id === env.id;
              return (
                <button
                  key={env.id}
                  type="button"
                  disabled={busyAction}
                  onClick={() => onSwitchEnvironment(env.id)}
                  className={`min-h-[34px] rounded-xl px-3 text-[11px] font-semibold transition cursor-pointer disabled:opacity-60 ${
                    active
                      ? "bg-white text-slate-950 font-bold shadow-sm"
                      : "border border-white/15 bg-[#151922] text-slate-200 hover:border-white/35 hover:text-white"
                  }`}
                >
                  {env.short_label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* 5 Environmental Sensor Tiles with Red/Yellow Lights */}
      <div className="mt-3.5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {envEval.list.map((s) => {
          const st = METRIC_LIGHT_STYLE[s.status] || METRIC_LIGHT_STYLE.NOMINAL;
          const SensorIcon = ENV_SENSOR_META[s.key]?.Icon || Gauge;
          const statusLabel = s.status === "CRITICAL" ? "Critical" : s.status === "WARNING" ? "Attention" : "Normal";
          const statusTextColor =
            s.status === "CRITICAL" ? "text-[#F87171]" : s.status === "WARNING" ? "text-[#FBBF24]" : "text-[#4ADE80]";

          return (
            <div key={s.key} className={`relative rounded-2xl border p-3.5 transition ${st.card}`}>
              <span className="absolute right-3 top-3">
                <StatusLedDot status={s.status} size="h-2.5 w-2.5" />
              </span>
              <div className="flex items-center gap-2">
                <SensorIcon className={`h-5 w-5 ${st.iconColor || ENV_SENSOR_META[s.key]?.defaultIcon}`} strokeWidth={1.5} />
                <span className={`text-[11px] font-medium ${st.label}`}>{s.label}</span>
              </div>
              <div className={`mt-2 font-mono text-xl font-bold ${st.value}`}>
                {s.display}
                {s.key !== "climate" && <span className="ml-1 text-xs font-normal text-[#CBD5E1]">{s.unit}</span>}
              </div>
              <div className="mt-1.5 flex items-center justify-between gap-2 text-[10px]">
                <span className={`flex items-center gap-1 font-medium ${statusTextColor}`}>
                  {s.status === "NOMINAL" && <ShieldCheck className="h-3 w-3" />}
                  {statusLabel}
                </span>
                <span className={st.sub}>{s.range}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
