import { Brain } from "lucide-react";
import { getPsychologicalReadiness } from "../services/api";
import { METRIC_LIGHT_STYLE, StatusLedDot } from "./EnvironmentPanel";

const TIER_VISUAL = {
  OPTIMAL: {
    bar: "from-emerald-400 to-teal-300 shadow-[0_0_12px_rgba(52,211,153,0.55)]",
    badge: "border-emerald-400/50 bg-emerald-950/75 text-emerald-200",
    border: "border-white/12 bg-[#090C11]",
    scoreText: "text-emerald-300",
  },
  CAUTION: {
    bar: "from-amber-400 to-yellow-300 shadow-[0_0_12px_rgba(245,158,11,0.55)]",
    badge: "border-amber-400/60 bg-amber-950/70 text-amber-200",
    border: "border-amber-400/55 bg-amber-950/35",
    scoreText: "text-amber-300",
  },
  HIGH_STRAIN: {
    bar: "from-orange-500 to-amber-400 shadow-[0_0_12px_rgba(249,115,22,0.55)]",
    badge: "border-orange-400/70 bg-orange-950/75 text-orange-200",
    border: "border-amber-400/75 bg-amber-950/45 shadow-[0_0_14px_rgba(245,158,11,0.3)]",
    scoreText: "text-amber-200",
  },
  CRITICAL_STRAIN: {
    bar: "from-red-500 to-rose-400 shadow-[0_0_14px_rgba(239,68,68,0.75)]",
    badge: "border-red-400/80 bg-red-950/85 text-red-100 shadow-[0_0_12px_rgba(239,68,68,0.45)]",
    border: "border-red-500/85 bg-red-950/55 shadow-[0_0_16px_rgba(239,68,68,0.4)]",
    scoreText: "text-red-300",
  },
};

export function PsychCrewBar({ member }) {
  const psych = getPsychologicalReadiness(member.vitals, member.personal_baseline, {
    environmentId: member.environment_id,
  });
  const vis = TIER_VISUAL[psych.tier] || TIER_VISUAL.OPTIMAL;

  return (
    <div className={`mt-2.5 rounded-2xl border px-3 py-2 transition-colors ${vis.border}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <StatusLedDot status={psych.status} />
          <Brain className={`h-3.5 w-3.5 ${vis.scoreText}`} />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-200">
            Psych Readiness
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`font-mono text-xs font-bold ${vis.scoreText}`}>
            {psych.score}
            <span className="text-[10px] font-normal text-slate-400">/100</span>
          </span>
          <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${vis.badge}`}>
            {psych.label}
          </span>
        </div>
      </div>

      {/* Meter bar */}
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-slate-900/90 p-0.5 ring-1 ring-white/10">
        <div
          className={`h-full rounded-full bg-gradient-to-r transition-all duration-500 ${vis.bar}`}
          style={{ width: `${Math.max(4, psych.score)}%` }}
        />
      </div>
    </div>
  );
}

export function PsychCockpitCard({ state }) {
  if (!state?.vitals) return null;
  const psych = getPsychologicalReadiness(state.vitals, state.personal_baseline, {
    oneWayLatencySeconds: state.one_way_latency_seconds,
    environmentId: state.environment_id,
    psychEvaluation: state.psych_biofeedback,
  });
  const vis = TIER_VISUAL[psych.tier] || TIER_VISUAL.OPTIMAL;
  const cardTone =
    psych.status === "CRITICAL"
      ? "border-red-500/85 bg-[#1A090C] shadow-[0_0_20px_rgba(239,68,68,0.4)]"
      : psych.status === "WARNING"
        ? "border-amber-400/85 bg-[#191206] shadow-[0_0_18px_rgba(245,158,11,0.32)]"
        : "border-white/15 bg-[#0E1218] shadow-[0_12px_32px_rgba(0,0,0,0.65)]";

  return (
    <div className={`rounded-2xl border p-4 transition ${cardTone}`}>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Brain className={`h-5 w-5 ${vis.scoreText}`} />
            <h3 className="text-sm font-semibold text-white">Psychological Readiness Rank &amp; Behavioral Load</h3>
            <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${vis.badge}`}>
              <StatusLedDot status={psych.status} />
              {psych.label}
            </span>
          </div>
          <p className="text-xs text-[#CBD5E1]">{psych.summary}</p>
        </div>

        {/* Numeric Score Readout + Segmented Rank Meter */}
        <div className="flex items-center gap-4">
          <div className="min-w-[190px]">
            <div className="mb-1 flex items-center justify-between text-[10px] text-slate-300">
              <span>Critical (0)</span>
              <span>Caution (55)</span>
              <span>Optimal (100)</span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-slate-950/90 p-0.5 ring-1 ring-white/15">
              <div
                className={`h-full rounded-full bg-gradient-to-r transition-all duration-500 ${vis.bar}`}
                style={{ width: `${Math.max(4, psych.score)}%` }}
              />
            </div>
          </div>
          <div className="rounded-2xl border border-white/15 bg-[#151922] px-3.5 py-2 text-center">
            <div className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">Rank Score</div>
            <div className={`font-mono text-2xl font-extrabold leading-none ${vis.scoreText}`}>
              {psych.score}
              <span className="text-xs font-normal text-slate-400">/100</span>
            </div>
          </div>
        </div>
      </div>

      {/* 5 Psychological Sub-Factors with Individual Lights */}
      <div className="mt-3.5 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
        {psych.factors.map((f) => {
          const st = METRIC_LIGHT_STYLE[f.status] || METRIC_LIGHT_STYLE.NOMINAL;
          return (
            <div key={f.key} className={`relative rounded-xl border px-3 py-2.5 transition ${st.card}`}>
              <span className="absolute right-2.5 top-2.5">
                <StatusLedDot status={f.status} />
              </span>
              <div className={`text-[10px] font-medium ${st.label}`}>{f.label}</div>
              <div className={`mt-1 font-mono text-base font-bold ${st.value}`}>{f.display}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
