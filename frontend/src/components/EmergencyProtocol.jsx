import { useState } from "react";

export default function EmergencyProtocol({ state, onOpenDossier }) {
  const [openModal, setOpenModal] = useState(false);
  const [checkedSteps, setCheckedSteps] = useState({});

  const clinical = state?.clinical_evaluation;
  const isCritical = clinical?.overall_status === "CRITICAL";
  const checklist = clinical?.stabilization_checklist || [];
  const latency = state?.one_way_latency_seconds ?? 0;

  if (!isCritical) return null;

  const toggleStep = (idx) => {
    setCheckedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <>
      {/* Persistent Critical Alert Banner */}
      <div className="mb-5 rounded-3xl border-2 border-[#DC2626] bg-[#FEF2F2] p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#DC2626] text-white shadow-sm">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-[#DC2626] px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider text-white">
                  CRITICAL MEDICAL ALERT
                </span>
                {state?.crew_member && (
                  <span className="rounded-full bg-[#FEE2E2] px-2.5 py-0.5 text-[11px] font-bold text-[#991B1B]">
                    {state.crew_member}
                  </span>
                )}
                <span className="text-xs font-semibold text-[#991B1B]">
                  One-Way Earth Latency: {latency}s
                </span>
              </div>
              <h3 className="mt-1 text-base font-bold text-[#113D2E]">
                {clinical?.primary_diagnosis || "Critical Crew Health Anomaly Detected"}
              </h3>
              <p className="text-xs text-[#7F1D1D]">
                {state?.pending_verification_measurement
                  ? "Stabilization applied — execute a confirmatory biometric scan to verify vitals within personal baseline and clear alert."
                  : "Autonomous onboard stabilization active. Execute NASA-STD-3001 immediate countermeasures and transmit Telemedicine Dossier."}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={() => setOpenModal(true)}
              className="min-h-[44px] rounded-full bg-[#DC2626] px-5 text-sm font-semibold text-white transition hover:bg-[#B91C1C]"
            >
              Open Stabilization Checklist ({checklist.length})
            </button>
            <button
              type="button"
              onClick={onOpenDossier}
              className="min-h-[44px] rounded-full border border-[#113D2E] bg-white px-5 text-sm font-semibold text-[#113D2E] transition hover:bg-[#EFF9F2]"
            >
              Generate Telemedicine Dossier
            </button>
          </div>
        </div>
      </div>

      {/* Stabilization Checklist Modal */}
      {openModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#113D2E]/40 p-4 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-[#CBE2D5] bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-[#E2EFE8] pb-4">
              <div>
                <span className="inline-flex items-center rounded-full bg-[#FEF2F2] px-3 py-1 text-xs font-bold uppercase tracking-wider text-[#DC2626] border border-[#FCA5A5]">
                  Emergency Protocol • NASA-STD-3001
                </span>
                <h3 className="mt-2 text-xl font-bold text-[#113D2E]">
                  {clinical?.primary_diagnosis || "Autonomous Stabilization Protocol"}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setOpenModal(false)}
                className="min-h-[44px] min-w-[44px] rounded-full border border-[#CBE2D5] bg-[#F7FBF9] px-3 text-sm font-semibold text-[#113D2E] hover:bg-[#EFF9F2]"
              >
                Close
              </button>
            </div>

            {/* Diagnostic Summary Cards */}
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-[#FCA5A5] bg-[#FEF2F2] p-3.5">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#991B1B]">
                  ML Anomaly Score
                </div>
                <div className="mt-1 font-mono text-2xl font-bold text-[#DC2626]">
                  {state?.ml_prediction?.anomaly_score?.toFixed(2) ?? "N/A"}
                </div>
              </div>
              <div className="rounded-2xl border border-[#FCD34D] bg-[#FFFBEB] p-3.5">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#92400E]">
                  Earth Comm Delay
                </div>
                <div className="mt-1 font-mono text-2xl font-bold text-[#B45309]">
                  {latency}s one-way
                </div>
              </div>
            </div>

            {/* Matched Rules */}
            {clinical?.matched_rules && clinical.matched_rules.length > 0 && (
              <div className="mt-4 rounded-2xl border border-[#C7E4EE] bg-[#EAF6FA] p-3.5">
                <div className="text-xs font-bold uppercase tracking-wider text-[#113D2E]">
                  Triggered Clinical Rules
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {clinical.matched_rules.map((rule, i) => (
                    <span
                      key={i}
                      className="rounded-full border border-[#C7E4EE] bg-white px-3 py-1 font-mono text-xs font-semibold text-[#113D2E]"
                    >
                      {rule}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Interactive Checklist */}
            <div className="mt-5">
              <div className="mb-2.5 text-xs font-bold uppercase tracking-wider text-[#476458]">
                Immediate Stabilization Steps
              </div>
              <div className="space-y-2.5">
                {checklist.map((step, idx) => {
                  const done = !!checkedSteps[idx];
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => toggleStep(idx)}
                      className={`flex w-full items-start gap-3 rounded-2xl border p-3.5 text-left transition ${
                        done
                          ? "border-[#A7F3D0] bg-[#ECFDF5] text-[#065F46]"
                          : "border-[#CBE2D5] bg-[#F7FBF9] text-[#113D2E] hover:bg-[#EFF9F2]"
                      }`}
                    >
                      <span
                        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${
                          done
                            ? "border-[#059669] bg-[#059669] text-white"
                            : "border-[#476458] bg-white text-transparent"
                        }`}
                      >
                        ✓
                      </span>
                      <span className={`text-sm font-medium ${done ? "line-through opacity-80" : ""}`}>
                        {step}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-6 flex flex-wrap justify-end gap-2.5 border-t border-[#E2EFE8] pt-4">
              <button
                type="button"
                onClick={() => {
                  setOpenModal(false);
                  onOpenDossier();
                }}
                className="min-h-[44px] rounded-full bg-[#113D2E] px-5 text-sm font-semibold text-white transition hover:bg-[#195440]"
              >
                Prepare Telemedicine Dossier
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
