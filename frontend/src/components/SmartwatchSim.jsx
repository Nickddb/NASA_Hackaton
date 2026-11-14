import React, { useEffect, useState } from "react";
import {
  BellRing,
  Clock,
  Globe2,
  HeartPulse,
  Radiation,
  Radio,
  Rocket,
  ShieldAlert,
  Watch,
} from "lucide-react";

const SEV_PILL = {
  NOMINAL: "border-[#A7F3D0] text-[#065F46] bg-[#ECFDF5]",
  WARNING: "border-[#FDE68A] text-[#92400E] bg-[#FFFBEB]",
  CRITICAL: "border-[#FECACA] text-[#991B1B] bg-[#FEF2F2]",
};

export default function SmartwatchSim({
  state,
  onSwitchScenario,
  onSwitchEnvironment,
  onTriggerWristScan,
  loadingScenario,
}) {
  const [countdown, setCountdown] = useState(298);
  const [wristFeedback, setWristFeedback] = useState("");

  useEffect(() => {
    const id = setInterval(() => {
      setCountdown((prev) => (prev <= 1 ? 300 : prev - 1));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  if (!state) return null;

  const vitals = state.vitals;
  const status = state.clinical_evaluation?.overall_status || "NOMINAL";
  const scenarios = state.scenarios_catalog || [];
  const environments = state.environments_catalog || [];

  const mins = String(Math.floor(countdown / 60)).padStart(2, "0");
  const secs = String(countdown % 60).padStart(2, "0");

  const handleWristScan = async () => {
    setWristFeedback("Synchronizing PPG + BLE Dosimeter...");
    const res = await onTriggerWristScan("cardiovascular");
    setWristFeedback(res?.reading_summary || "Wrist biometric sync complete.");
    setCountdown(300);
  };

  return (
    <div className="space-y-4">
      {/* Mission Simulation & Environment Control Bar */}
      <section className="eco-card rounded-3xl p-4 sm:p-5 space-y-3.5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* 6 Clinical Scenarios */}
          <div className="space-y-1.5">
            <div className="text-[11px] uppercase tracking-widest text-[#059669] font-bold flex items-center gap-1.5">
              <Rocket className="w-3.5 h-3.5" /> Mission Scenario Simulator (NASA-STD-3001)
            </div>
            <div className="flex flex-wrap gap-1.5">
              {scenarios.map((sc) => {
                const active = state.scenario_id === sc.id;
                return (
                  <button
                    key={sc.id}
                    type="button"
                    disabled={loadingScenario}
                    onClick={() => onSwitchScenario(sc.id)}
                    className={`min-h-[44px] px-4 py-1.5 rounded-full text-xs font-bold border transition-all cursor-pointer ${
                      active
                        ? "bg-[#113D2E] text-white border-[#113D2E] shadow-sm"
                        : `${SEV_PILL[sc.severity] || "border-[#D5E8DD] text-[#113D2E]"} hover:border-[#113D2E]`
                    }`}
                  >
                    {sc.short_label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 3 Space Environments */}
          <div className="space-y-1.5">
            <div className="text-[11px] uppercase tracking-widest text-[#0284C7] font-bold flex items-center gap-1.5">
              <Globe2 className="w-3.5 h-3.5" /> Space Environment Calibration
            </div>
            <div className="flex flex-wrap gap-1.5">
              {environments.map((env) => {
                const active = state.environment_id === env.id;
                return (
                  <button
                    key={env.id}
                    type="button"
                    onClick={() => onSwitchEnvironment(env.id)}
                    className={`min-h-[44px] px-4 py-1.5 rounded-full text-xs font-bold border transition-all cursor-pointer ${
                      active
                        ? "bg-[#C8EE90] text-[#113D2E] border-[#9AD158]"
                        : "bg-[#EAF6FA] text-[#0F4C5C] border-[#C7E4EE] hover:border-[#0284C7]"
                    }`}
                  >
                    {env.short_label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Active Environment & Latency Strip */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-[#E4F0E9] text-xs">
          <div className="text-[#334E44]">
            <span className="text-[#113D2E] font-bold">{state.environment_name}:</span>{" "}
            {state.clinical_evaluation?.environment_calibration_notes?.[0]}
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#EAF6FA] border border-[#C7E4EE] font-mono-telemetry text-[11px] text-[#0F4C5C] font-semibold shrink-0">
            <Radio className="w-3.5 h-3.5 text-[#0284C7]" />
            Earth One-Way Latency: {state.one_way_latency_seconds}s (
            {state.one_way_latency_seconds > 60
              ? `${Math.round(state.one_way_latency_seconds / 60)} min`
              : `${state.one_way_latency_seconds}s`}
            )
          </div>
        </div>
      </section>

      {/* Edge Biometric Smartwatch Widget (Soft Mint Card + Crisp Dark Watch Bezel) */}
      <section className="bg-[#EFF9F2] border border-[#CBE2D5] rounded-3xl p-4 sm:p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row items-center gap-5">
          {/* Wristwatch Bezel */}
          <div
            className={`relative w-44 h-44 rounded-[2.25rem] bg-[#113D2E] border-4 p-3.5 flex flex-col justify-between shrink-0 transition-all shadow-lg ${
              status === "CRITICAL"
                ? "border-[#EF4444] animate-pulse"
                : status === "WARNING"
                ? "border-[#F59E0B]"
                : "border-[#C8EE90]"
            }`}
          >
            <div className="flex items-center justify-between text-[10px] text-[#A7D7C5] font-mono-telemetry">
              <span className="flex items-center gap-1 text-[#C8EE90] font-bold">
                <Watch className="w-3 h-3" /> EDGE
              </span>
              <span>SOL {state.mission_day}</span>
            </div>

            <svg viewBox="0 0 140 30" className="w-full h-7">
              <path
                d="M0,16 L24,16 L30,10 L35,20 L42,4 L48,26 L54,16 L80,16 L86,12 L92,16 L140,16"
                fill="none"
                stroke={status === "CRITICAL" ? "#FCA5A5" : status === "WARNING" ? "#FCD34D" : "#C8EE90"}
                strokeWidth="2.2"
                className="animate-ecg"
              />
            </svg>

            <div className="grid grid-cols-2 gap-1.5 text-center">
              <div className="bg-white/10 rounded-xl py-1">
                <div className="text-[9px] text-[#A7D7C5]">HR</div>
                <div className="text-sm font-bold text-white font-mono-telemetry">
                  {Math.round(vitals.heart_rate_bpm)}
                </div>
              </div>
              <div className="bg-white/10 rounded-xl py-1">
                <div className="text-[9px] text-[#A7D7C5]">SpO2</div>
                <div className="text-sm font-bold text-[#C8EE90] font-mono-telemetry">
                  {vitals.spo2_pct.toFixed(0)}%
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-[10px] font-mono-telemetry">
              <span className="text-[#FDE68A] flex items-center gap-0.5">
                <Radiation className="w-3 h-3" /> {vitals.radiation_msv_h.toFixed(2)}
              </span>
              <span className="text-white/90 font-semibold">{status}</span>
            </div>
          </div>

          {/* Smartwatch Autonomous Schedule & Controls */}
          <div className="flex-1 space-y-2.5 w-full">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <span className="text-[11px] uppercase tracking-widest text-[#059669] font-bold">
                  Onboard Edge Smartwatch (Offline-First BLE)
                </span>
                <h3 className="text-base font-bold text-[#113D2E]">
                  Autonomous Scheduled Monitoring &amp; Haptic Interrupts
                </h3>
              </div>
              <span className="text-xs font-mono-telemetry px-3 py-1 rounded-full bg-white border border-[#CBE2D5] text-[#113D2E] font-semibold flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#059669]" />
                Next Auto-Scan: {mins}:{secs}
              </span>
            </div>

            <p className="text-xs text-[#334E44] leading-relaxed">
              Continuously samples optical PPG with 6-axis 0g motion noise filtering, sleep actigraphy, and BLE personal dosimetry even during complete Earth communication blackouts.
            </p>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleWristScan}
                className="min-h-[44px] px-5 rounded-full bg-[#113D2E] hover:bg-[#19533F] text-white text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
              >
                <HeartPulse className="w-4 h-4 text-[#C8EE90]" />
                Run Scheduled Wrist Scan
              </button>

              {status !== "NOMINAL" && (
                <span
                  className={`px-3.5 py-2 rounded-full text-xs font-bold flex items-center gap-1.5 border ${
                    status === "CRITICAL"
                      ? "bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]"
                      : "bg-[#FFFBEB] border-[#FDE68A] text-[#92400E]"
                  }`}
                >
                  {status === "CRITICAL" ? <ShieldAlert className="w-4 h-4" /> : <BellRing className="w-4 h-4" />}
                  Haptic Alert Active: {state.clinical_evaluation?.primary_diagnosis}
                </span>
              )}
            </div>

            {wristFeedback && (
              <div className="text-[11px] font-mono-telemetry text-[#065F46] bg-white border border-[#A7F3D0] rounded-xl px-3 py-2">
                {wristFeedback}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
