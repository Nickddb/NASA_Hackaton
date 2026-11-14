export default function TelemedDossier({ dossier, loading, onClose }) {
  if (!dossier && !loading) return null;

  const handleDownloadJson = () => {
    if (!dossier) return;
    const blob = new Blob([JSON.stringify(dossier, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${dossier.dossier_id || "astracare-dossier"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const urgency = String(dossier?.urgency || "ROUTINE").toUpperCase();
  const urgencyBadge =
    urgency === "CRITICAL" || urgency === "EMERGENCY"
      ? "border-[#FCA5A5] bg-[#FEF2F2] text-[#991B1B]"
      : urgency === "WARNING" || urgency === "URGENT"
      ? "border-[#FCD34D] bg-[#FFFBEB] text-[#92400E]"
      : "border-[#A7F3D0] bg-[#ECFDF5] text-[#065F46]";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#113D2E]/40 p-4 backdrop-blur-sm">
      <div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-[#CBE2D5] bg-white p-6 shadow-2xl">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#CBE2D5] border-t-[#113D2E]" />
            <p className="mt-4 text-sm font-semibold text-[#113D2E]">
              Compiling Store-and-Forward Telemedicine Dossier...
            </p>
            <p className="mt-1 text-xs text-[#476458]">
              Packaging NASA-STD-3001 vitals, ML anomaly scores, and space weather context
            </p>
          </div>
        ) : (
          <>
            {/* Modal Header */}
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#E2EFE8] pb-4">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-[#113D2E] px-3 py-1 font-mono text-xs font-bold text-[#C8EE90]">
                    {dossier.dossier_id}
                  </span>
                  <span className={`rounded-full border px-3 py-1 text-xs font-bold ${urgencyBadge}`}>
                    URGENCY: {urgency}
                  </span>
                </div>
                <h2 className="mt-2 text-xl font-bold text-[#113D2E]">
                  Earth Telemedicine Dossier — {dossier.crew_member}
                </h2>
                <p className="text-xs text-[#476458]">
                  Mission Day {dossier.mission_day} • Mode: {dossier.transmission_mode} • Latency:{" "}
                  {dossier.one_way_latency_seconds}s
                </p>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="min-h-[44px] rounded-full border border-[#CBE2D5] bg-[#F7FBF9] px-4 text-sm font-semibold text-[#113D2E] hover:bg-[#EFF9F2]"
              >
                Close
              </button>
            </div>

            {/* Executive Summary */}
            <div className="mt-4 rounded-2xl border border-[#CBE2D5] bg-[#EFF9F2] p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-[#113D2E]">
                Executive Clinical Summary
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-[#113D2E]">
                {dossier.executive_summary}
              </p>
              {dossier.recipient_roles && dossier.recipient_roles.length > 0 && (
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-[#476458]">Recipients:</span>
                  {dossier.recipient_roles.map((role) => (
                    <span
                      key={role}
                      className="rounded-full border border-[#CBE2D5] bg-white px-2.5 py-0.5 text-[11px] font-semibold text-[#113D2E]"
                    >
                      {role}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Vitals & Nutrition Snapshots */}
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
              {dossier.vitals_snapshot && (
                <div className="rounded-2xl border border-[#C7E4EE] bg-[#EAF6FA] p-4">
                  <div className="text-xs font-bold uppercase tracking-wider text-[#113D2E]">
                    Vitals Snapshot
                  </div>
                  <div className="mt-2.5 grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(dossier.vitals_snapshot).map(([k, v]) => (
                      <div key={k} className="rounded-xl border border-[#C7E4EE] bg-white px-2.5 py-2">
                        <div className="text-[10px] font-semibold uppercase text-[#476458]">
                          {k.replaceAll("_", " ")}
                        </div>
                        <div className="mt-0.5 font-mono font-bold text-[#113D2E]">{String(v)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {dossier.nutrition_snapshot && (
                <div className="rounded-2xl border border-[#CBE2D5] bg-[#F7FBF9] p-4">
                  <div className="text-xs font-bold uppercase tracking-wider text-[#113D2E]">
                    Nutrition & Hydration Snapshot
                  </div>
                  <div className="mt-2.5 grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(dossier.nutrition_snapshot).map(([k, v]) => (
                      <div key={k} className="rounded-xl border border-[#CBE2D5] bg-white px-2.5 py-2">
                        <div className="text-[10px] font-semibold uppercase text-[#476458]">
                          {k.replaceAll("_", " ")}
                        </div>
                        <div className="mt-0.5 font-mono font-bold text-[#113D2E]">{String(v)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Space Weather Alert */}
            {dossier.space_weather_alert && (
              <div className="mt-4 rounded-2xl border border-[#FCD34D] bg-[#FFFBEB] p-4">
                <div className="text-xs font-bold uppercase tracking-wider text-[#92400E]">
                  Space Weather Context
                </div>
                <p className="mt-1 text-sm text-[#78350F]">{dossier.space_weather_alert}</p>
              </div>
            )}

            {/* Recommended Earth Questions */}
            {dossier.recommended_earth_questions && dossier.recommended_earth_questions.length > 0 && (
              <div className="mt-4 rounded-2xl border border-[#CBE2D5] bg-[#EFF9F2] p-4">
                <div className="text-xs font-bold uppercase tracking-wider text-[#113D2E]">
                  Recommended Questions for Earth Flight Surgeon
                </div>
                <ul className="mt-2 space-y-1.5 text-sm text-[#113D2E]">
                  {dossier.recommended_earth_questions.map((q, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="font-bold text-[#059669]">•</span>
                      <span>{q}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Actions */}
            <div className="mt-6 flex flex-wrap items-center justify-end gap-3 border-t border-[#E2EFE8] pt-4">
              <button
                type="button"
                onClick={handleDownloadJson}
                className="min-h-[44px] rounded-full bg-[#113D2E] px-5 text-sm font-semibold text-white transition hover:bg-[#195440]"
              >
                Download JSON Dossier
              </button>
              <button
                type="button"
                onClick={onClose}
                className="min-h-[44px] rounded-full border border-[#CBE2D5] bg-white px-5 text-sm font-semibold text-[#113D2E] transition hover:bg-[#EFF9F2]"
              >
                Done
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
