import React, { useState } from "react";
import {
  Activity,
  Brain,
  ChevronDown,
  ChevronUp,
  Droplets,
  Flame,
  HeartPulse,
  Moon,
  Radiation,
  ShieldCheck,
  Thermometer,
  TrendingUp,
  Utensils,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const STATUS_BADGE = {
  NOMINAL: "bg-[#ECFDF5] text-[#065F46] border-[#A7F3D0]",
  WARNING: "bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]",
  CRITICAL: "bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]",
};

const BORDER_LEFT = {
  NOMINAL: "border-l-[#10B981]",
  WARNING: "border-l-[#F59E0B]",
  CRITICAL: "border-l-[#EF4444]",
};

function getIndicatorStatus(id, vitals, nutrition) {
  if (!vitals) return "NOMINAL";
  switch (id) {
    case "heart_rate_hrv":
      if (vitals.heart_rate_bpm >= 110 || vitals.hrv_ms <= 24) return "CRITICAL";
      if (vitals.heart_rate_bpm >= 95 || vitals.hrv_ms < 35) return "WARNING";
      return "NOMINAL";
    case "blood_pressure":
      if (vitals.bp_systolic <= 82) return "CRITICAL";
      if (vitals.bp_systolic <= 92) return "WARNING";
      return "NOMINAL";
    case "blood_glucose":
      if (vitals.glucose_mg_dl < 60 || vitals.glucose_mg_dl >= 180) return "CRITICAL";
      if (vitals.glucose_mg_dl <= 70 || vitals.glucose_mg_dl >= 140) return "WARNING";
      return "NOMINAL";
    case "body_temperature":
      if (vitals.temperature_c >= 38.0) return "CRITICAL";
      if (vitals.temperature_c >= 37.5 || vitals.temperature_c < 35.8) return "WARNING";
      return "NOMINAL";
    case "sleep_circadian":
      if (vitals.sleep_streak_low_days >= 3 || vitals.sleep_hours < 4.5) return "CRITICAL";
      if (vitals.sleep_hours < 6.5) return "WARNING";
      return "NOMINAL";
    case "mood_cognitive":
      if (vitals.mood_score <= 2 && vitals.sleep_streak_low_days >= 3) return "CRITICAL";
      if (vitals.mood_score <= 2 || vitals.stress_index >= 75) return "WARNING";
      return "NOMINAL";
    case "radiation_dose":
      if (vitals.radiation_msv_h >= 0.5) return "CRITICAL";
      if (vitals.radiation_msv_h >= 0.15) return "WARNING";
      return "NOMINAL";
    case "nutrition_hydration": {
      const calPct = (nutrition.calories_kcal / Math.max(nutrition.goal_calories_kcal, 1)) * 100;
      const waterPct = (nutrition.water_ml / Math.max(nutrition.goal_water_ml, 1)) * 100;
      if (calPct < 50 || waterPct < 55 || nutrition.sodium_mg > nutrition.max_sodium_mg || nutrition.iron_mg > nutrition.max_iron_mg) {
        return "WARNING";
      }
      return "NOMINAL";
    }
    default:
      return "NOMINAL";
  }
}

function formatIndicatorValue(id, vitals, nutrition) {
  if (!vitals) return "--";
  switch (id) {
    case "heart_rate_hrv":
      return `${Math.round(vitals.heart_rate_bpm)} bpm | ${Math.round(vitals.hrv_ms)} ms`;
    case "blood_pressure":
      return `${Math.round(vitals.bp_systolic)}/${Math.round(vitals.bp_diastolic)} mmHg`;
    case "blood_glucose":
      return `${Math.round(vitals.glucose_mg_dl)} mg/dL`;
    case "body_temperature":
      return `${vitals.temperature_c.toFixed(1)} °C`;
    case "sleep_circadian":
      return `${vitals.sleep_hours.toFixed(1)} h (${Math.round(vitals.rem_sleep_pct)}% REM)`;
    case "mood_cognitive":
      return `${vitals.mood_score}/5 | Stress ${Math.round(vitals.stress_index)}%`;
    case "radiation_dose":
      return `${vitals.radiation_msv_h.toFixed(2)} mSv/h`;
    case "nutrition_hydration":
      return `${Math.round(nutrition.calories_kcal)} kcal | ${Math.round(nutrition.water_ml)} ml`;
    default:
      return "--";
  }
}

const INDICATOR_ICONS = {
  heart_rate_hrv: HeartPulse,
  blood_pressure: Activity,
  blood_glucose: Droplets,
  body_temperature: Thermometer,
  sleep_circadian: Moon,
  mood_cognitive: Brain,
  radiation_dose: Radiation,
  nutrition_hydration: Utensils,
};

export default function VitalsDashboard({ state, onSelectSystem }) {
  const [expandedGuide, setExpandedGuide] = useState(null);
  const [chartTab, setChartTab] = useState("cardio");

  const vitals = state?.vitals;
  const nutrition = state?.nutrition;
  const clinical = state?.clinical_evaluation;
  const ml = state?.ml_prediction;
  const guides = state?.indicators_guide || [];
  const series = state?.longitudinal_series || [];

  if (!vitals || !nutrition) return null;

  const calPct = Math.min(100, Math.round((nutrition.calories_kcal / nutrition.goal_calories_kcal) * 100));
  const waterPct = Math.min(100, Math.round((nutrition.water_ml / nutrition.goal_water_ml) * 100));
  const protPct = Math.min(100, Math.round((nutrition.protein_g / nutrition.goal_protein_g) * 100));
  const sodiumOver = nutrition.sodium_mg > nutrition.max_sodium_mg;
  const ironOver = nutrition.iron_mg > nutrition.max_iron_mg;

  return (
    <div className="flex flex-col gap-4">
      {/* 8 Core Health Indicators Grid */}
      <section className="eco-card rounded-3xl p-5">
        <div className="flex items-center justify-between gap-2 mb-3.5 flex-wrap">
          <div>
            <span className="text-[11px] uppercase tracking-widest text-[#059669] font-bold">
              8 Core Spaceflight Biomarkers
            </span>
            <h2 className="text-lg font-bold text-[#113D2E]">
              Live Telemetry &amp; Crew Guidance
            </h2>
          </div>
          <span className="text-[11px] text-[#476458] bg-[#EFF9F2] px-3 py-1 rounded-full border border-[#D5E8DD]">
            Tap chevron for &ldquo;How to Measure&rdquo;
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {guides.map((ind) => {
            const st = getIndicatorStatus(ind.id, vitals, nutrition);
            const Icon = INDICATOR_ICONS[ind.id] || Activity;
            const isOpen = expandedGuide === ind.id;
            return (
              <div
                key={ind.id}
                className={`bg-[#F7FBF9] border border-[#D5E8DD] border-l-4 ${BORDER_LEFT[st]} rounded-2xl p-3.5 transition-all hover:bg-white`}
              >
                <div className="flex items-start justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => onSelectSystem && onSelectSystem(ind.system_id)}
                    className="text-left group cursor-pointer"
                  >
                    <div className="flex items-center gap-1.5 text-xs text-[#476458] font-semibold group-hover:text-[#059669]">
                      <Icon className="w-3.5 h-3.5 text-[#059669]" />
                      {ind.name}
                    </div>
                    <div className="text-base font-bold text-[#113D2E] font-mono-telemetry mt-0.5">
                      {formatIndicatorValue(ind.id, vitals, nutrition)}
                    </div>
                  </button>

                  <div className="flex items-center gap-1.5">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${STATUS_BADGE[st]}`}>
                      {st}
                    </span>
                    <button
                      type="button"
                      onClick={() => setExpandedGuide(isOpen ? null : ind.id)}
                      aria-label={`Toggle guide for ${ind.name}`}
                      className="min-w-[36px] min-h-[36px] rounded-full border border-[#D5E8DD] bg-white hover:border-[#113D2E] flex items-center justify-center text-[#476458] hover:text-[#113D2E] cursor-pointer"
                    >
                      {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-[#476458] mt-1.5">
                  <span className="truncate pr-2">{ind.device}</span>
                  <span className="font-mono-telemetry text-[#476458] shrink-0">{ind.nominal_range}</span>
                </div>

                {isOpen && (
                  <div className="mt-2.5 pt-2.5 border-t border-[#D5E8DD] text-[11px] space-y-1.5 text-[#334E44]">
                    <div>
                      <span className="text-[#059669] font-bold">How to Measure: </span>
                      {ind.how_to_measure}
                    </div>
                    <div>
                      <span className="text-[#0284C7] font-bold">Why It Matters: </span>
                      {ind.why_it_matters}
                    </div>
                    <div className="text-[#476458]">
                      <span className="text-[#113D2E] font-bold">0g Mitigation: </span>
                      {ind.space_challenge}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Hybrid AI Layer 1 + Layer 2 Risk Attribution & Nutrition Guardrails */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* Layer 1 + Layer 2 ML Diagnostics (Soft Sky Tint) */}
        <section className="bg-[#EAF6FA] border border-[#C7E4EE] rounded-3xl p-4 space-y-3 shadow-xs">
          <div className="flex items-center justify-between gap-2">
            <div>
              <span className="text-[11px] uppercase tracking-widest text-[#0369A1] font-bold">
                Hybrid Edge AI (Layer 1 + 2)
              </span>
              <h3 className="text-sm font-bold text-[#113D2E]">
                IsolationForest &amp; RandomForest
              </h3>
            </div>
            <div className="text-right bg-white px-3 py-1 rounded-2xl border border-[#C7E4EE]">
              <div className="text-[9px] text-[#476458] uppercase font-semibold">Anomaly</div>
              <div
                className={`text-lg font-bold font-mono-telemetry ${
                  ml.anomaly_score >= 70
                    ? "text-[#DC2626]"
                    : ml.anomaly_score >= 45
                    ? "text-[#D97706]"
                    : "text-[#059669]"
                }`}
              >
                {ml.anomaly_score.toFixed(1)}%
              </div>
            </div>
          </div>

          <div className="bg-white border border-[#C7E4EE] rounded-2xl p-3 text-xs">
            <div className="text-[#476458] text-[10px] uppercase font-semibold">Predicted Mission State</div>
            <div className="font-bold text-[#113D2E] flex items-center justify-between mt-0.5 gap-2">
              <span className="truncate">{ml.predicted_syndrome_label}</span>
              <span className="font-mono-telemetry text-[#0284C7] shrink-0">{ml.confidence_pct.toFixed(1)}%</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="text-[10px] uppercase tracking-wider text-[#0F4C5C] font-bold">
              Top Feature Drivers
            </div>
            {ml.feature_importances.map((feat) => (
              <div key={feat.feature} className="space-y-0.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-[#113D2E] font-medium">{feat.label}</span>
                  <span className="font-mono-telemetry text-[#476458]">
                    {feat.current_value} ({feat.importance.toFixed(0)}%)
                  </span>
                </div>
                <div className="h-2 bg-white rounded-full overflow-hidden border border-[#C7E4EE]">
                  <div
                    className="h-full bg-[#0284C7] rounded-full transition-all"
                    style={{ width: `${Math.min(100, feat.importance)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-1.5 pt-1">
            {clinical.matched_rules.slice(0, 3).map((rule) => (
              <span
                key={rule}
                className="px-2.5 py-0.5 rounded-full bg-white border border-[#C7E4EE] text-[10px] font-mono-telemetry text-[#0F4C5C] font-semibold"
              >
                {rule}
              </span>
            ))}
          </div>
        </section>

        {/* Daily Nutrition, Hydration & Space Micronutrient Caps (Soft Mint Tint) */}
        <section className="bg-[#EFF9F2] border border-[#CBE2D5] rounded-3xl p-4 space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[11px] uppercase tracking-widest text-[#059669] font-bold">
                Nutrition &amp; Hydration Goals
              </span>
              <h3 className="text-sm font-bold text-[#113D2E]">
                PWD Water &amp; NASA Na/Fe Caps
              </h3>
            </div>
            <div className="w-9 h-9 rounded-full bg-[#C8EE90] flex items-center justify-center">
              <Flame className="w-4 h-4 text-[#113D2E]" />
            </div>
          </div>

          <div className="space-y-2.5 text-xs">
            {/* Calories */}
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-[#334E44] font-medium">Daily Energy</span>
                <span className="font-mono-telemetry font-bold text-[#113D2E]">
                  {Math.round(nutrition.calories_kcal)} / {nutrition.goal_calories_kcal} kcal ({calPct}%)
                </span>
              </div>
              <div className="h-2.5 bg-white rounded-full overflow-hidden border border-[#CBE2D5]">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${calPct < 55 ? "bg-[#F59E0B]" : "bg-[#10B981]"}`}
                  style={{ width: `${calPct}%` }}
                />
              </div>
            </div>

            {/* Hydration */}
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-[#334E44] font-medium">Water Dispenser (PWD)</span>
                <span className="font-mono-telemetry font-bold text-[#113D2E]">
                  {Math.round(nutrition.water_ml)} / {nutrition.goal_water_ml} ml ({waterPct}%)
                </span>
              </div>
              <div className="h-2.5 bg-white rounded-full overflow-hidden border border-[#CBE2D5]">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${waterPct < 55 ? "bg-[#F59E0B]" : "bg-[#0EA5E9]"}`}
                  style={{ width: `${waterPct}%` }}
                />
              </div>
            </div>

            {/* Protein */}
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-[#334E44] font-medium">Protein Muscle Shield</span>
                <span className="font-mono-telemetry font-bold text-[#113D2E]">
                  {Math.round(nutrition.protein_g)} / {nutrition.goal_protein_g} g ({protPct}%)
                </span>
              </div>
              <div className="h-2.5 bg-white rounded-full overflow-hidden border border-[#CBE2D5]">
                <div className="h-full bg-[#113D2E] rounded-full transition-all duration-500" style={{ width: `${protPct}%` }} />
              </div>
            </div>

            {/* Spaceflight Sodium & Iron Safety Caps */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div
                className={`p-2.5 rounded-2xl border text-[11px] ${
                  sodiumOver ? "bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]" : "bg-white border-[#CBE2D5] text-[#113D2E]"
                }`}
              >
                <div className="text-[10px] uppercase text-[#476458] font-semibold">Sodium Cap</div>
                <div className="font-mono-telemetry font-bold">
                  {Math.round(nutrition.sodium_mg)} / {nutrition.max_sodium_mg} mg
                </div>
              </div>
              <div
                className={`p-2.5 rounded-2xl border text-[11px] ${
                  ironOver ? "bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]" : "bg-white border-[#CBE2D5] text-[#113D2E]"
                }`}
              >
                <div className="text-[10px] uppercase text-[#476458] font-semibold">Iron Cap (0g)</div>
                <div className="font-mono-telemetry font-bold">
                  {nutrition.iron_mg.toFixed(1)} / {nutrition.max_iron_mg.toFixed(0)} mg
                </div>
              </div>
            </div>

            {/* Recent Chat Nutrition Logs */}
            {nutrition.logged_items?.length > 0 && (
              <div className="bg-white border border-[#CBE2D5] rounded-2xl p-2.5 space-y-1 max-h-24 overflow-y-auto">
                <div className="text-[10px] uppercase tracking-wider text-[#059669] font-bold flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Latest AI-Logged Intake
                </div>
                {nutrition.logged_items.slice(0, 3).map((entry, i) => (
                  <div key={i} className="flex justify-between text-[11px] text-[#334E44]">
                    <span className="truncate pr-2">{entry.item}</span>
                    <span className="font-mono-telemetry text-[#113D2E] font-semibold shrink-0">
                      +{Math.round(entry.calories_kcal)} kcal / +{Math.round(entry.water_ml)} ml
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Longitudinal Mission Trends (Recharts) */}
      <section className="eco-card rounded-3xl p-5 space-y-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <span className="text-[11px] uppercase tracking-widest text-[#059669] font-bold flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5" /> Longitudinal Surveillance (OCHMO-TB-043)
            </span>
            <h3 className="text-base font-bold text-[#113D2E]">7-Day Telemetry Trajectory</h3>
          </div>
          <div className="flex gap-1.5">
            {[
              { id: "cardio", label: "HR / HRV / Glucose" },
              { id: "sleep", label: "Sleep / REM" },
              { id: "radiation", label: "Radiation & LHS" },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setChartTab(t.id)}
                className={`min-h-[38px] px-3.5 rounded-full text-xs font-semibold border cursor-pointer transition-all ${
                  chartTab === t.id
                    ? "bg-[#113D2E] text-white border-[#113D2E]"
                    : "bg-[#F7FBF9] text-[#113D2E] border-[#D5E8DD] hover:bg-[#EFF9F2]"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="h-[210px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            {chartTab === "cardio" ? (
              <AreaChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2EFE8" />
                <XAxis dataKey="day" stroke="#476458" fontSize={11} />
                <YAxis stroke="#476458" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#CBE2D5", borderRadius: "12px", color: "#113D2E", fontSize: "12px" }} />
                <Area type="monotone" dataKey="hr" name="Heart Rate (bpm)" stroke="#DC2626" fill="#DC2626" fillOpacity={0.1} strokeWidth={2} />
                <Area type="monotone" dataKey="hrv" name="HRV (ms)" stroke="#059669" fill="#059669" fillOpacity={0.14} strokeWidth={2} />
                <Area type="monotone" dataKey="glucose" name="Glucose (mg/dL)" stroke="#0284C7" fill="#0284C7" fillOpacity={0.12} strokeWidth={2} />
              </AreaChart>
            ) : chartTab === "sleep" ? (
              <AreaChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2EFE8" />
                <XAxis dataKey="day" stroke="#476458" fontSize={11} />
                <YAxis stroke="#476458" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#CBE2D5", borderRadius: "12px", color: "#113D2E", fontSize: "12px" }} />
                <Area type="monotone" dataKey="sleep" name="Sleep (hrs)" stroke="#0284C7" fill="#0284C7" fillOpacity={0.16} strokeWidth={2} />
                <Area type="monotone" dataKey="rem" name="REM (%)" stroke="#059669" fill="#059669" fillOpacity={0.14} strokeWidth={2} />
              </AreaChart>
            ) : (
              <AreaChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2EFE8" />
                <XAxis dataKey="day" stroke="#476458" fontSize={11} />
                <YAxis stroke="#476458" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#CBE2D5", borderRadius: "12px", color: "#113D2E", fontSize: "12px" }} />
                <Area type="monotone" dataKey="radiation" name="Dose Rate (mSv/h)" stroke="#D97706" fill="#D97706" fillOpacity={0.18} strokeWidth={2} />
                <Area type="monotone" dataKey="mood" name="Mood (1-5)" stroke="#059669" fill="#059669" fillOpacity={0.12} strokeWidth={2} />
              </AreaChart>
            )}
          </ResponsiveContainer>
        </div>

        {/* LHS OCHMO-TB-043 & OCHMO-MTB-006/011 Sub-Telemetry Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
          <div className="bg-[#F7FBF9] border border-[#D5E8DD] rounded-2xl p-2.5">
            <div className="text-[#476458]">EVA Shoulder VAS (MTB-006)</div>
            <div className={`font-mono-telemetry font-bold ${vitals.shoulder_pain_score >= 4 ? "text-[#D97706]" : "text-[#059669]"}`}>
              {vitals.shoulder_pain_score}/10
            </div>
          </div>
          <div className="bg-[#F7FBF9] border border-[#D5E8DD] rounded-2xl p-2.5">
            <div className="text-[#476458]">PFO / DCS Risk (MTB-011)</div>
            <div className={`font-mono-telemetry font-bold ${vitals.pfo_decompression_risk !== "LOW" ? "text-[#D97706]" : "text-[#059669]"}`}>
              {vitals.pfo_decompression_risk}
            </div>
          </div>
          <div className="bg-[#F7FBF9] border border-[#D5E8DD] rounded-2xl p-2.5">
            <div className="text-[#476458]">SANS IOP (Tonometry)</div>
            <div className={`font-mono-telemetry font-bold ${vitals.intraocular_pressure_mmhg >= 20 ? "text-[#D97706]" : "text-[#113D2E]"}`}>
              {vitals.intraocular_pressure_mmhg.toFixed(1)} mmHg
            </div>
          </div>
          <div className="bg-[#F7FBF9] border border-[#D5E8DD] rounded-2xl p-2.5">
            <div className="text-[#476458]">Urolux Urinary Ca</div>
            <div className={`font-mono-telemetry font-bold ${vitals.urinary_calcium_mg_d > 250 ? "text-[#D97706]" : "text-[#113D2E]"}`}>
              {Math.round(vitals.urinary_calcium_mg_d)} mg/d
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
