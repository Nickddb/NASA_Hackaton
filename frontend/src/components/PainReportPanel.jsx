import { useEffect, useState } from "react";
import { CheckCircle2, MapPin } from "lucide-react";
import { ANATOMICAL_PARTS_META } from "./AnatomyBody3D";

const QUALITIES = ["aching", "sharp", "burning", "throbbing", "cramping", "pressure"];

const intensityTone = (n) =>
  n >= 7 ? "bg-[#E5484D] text-white" : n >= 4 ? "bg-[#F08A4B] text-[#1A0B02]" : "bg-[#F2B35B] text-[#1A0F02]";

export default function PainReportPanel({ partId, reports = [], crossDiagnosis, mlPainSummary, live, busy, onReport, onResolve }) {
  const part = partId ? ANATOMICAL_PARTS_META[partId] : null;
  const existing = reports.find((r) => r.region === partId);
  const [intensity, setIntensity] = useState(existing?.intensity || 5);
  const [quality, setQuality] = useState(existing?.quality || "aching");
  const [note, setNote] = useState("");

  useEffect(() => {
    setIntensity(existing?.intensity || 5);
    setQuality(existing?.quality || "aching");
    setNote("");
  }, [partId]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async (e) => {
    e.preventDefault();
    if (!part) return;
    await onReport({ region: partId, intensity, quality, note });
    setNote("");
  };

  return (
    <div className="flex h-full flex-col gap-5 rounded-2xl border border-white/10 bg-[#0B0E14]/85 p-5">
      <div>
        <h2 className="text-base font-semibold text-white">Where does it hurt?</h2>
        <p className="mt-1 text-xs leading-relaxed text-slate-400">
          Tap a part of the body, rate the pain and send it. The rules, the cause tree and the ML read it right away.
        </p>
      </div>

      {!part ? (
        <p className="flex items-center gap-2 rounded-xl border border-dashed border-white/15 px-4 py-6 text-sm text-slate-400">
          <MapPin className="h-4 w-4" aria-hidden="true" /> No body part selected yet.
        </p>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <p className="text-sm font-semibold text-emerald-300">{part.label}</p>

          <fieldset>
            <legend className="mb-2 text-xs font-medium text-slate-300">
              Intensity <span className="font-mono text-white">{intensity}/10</span>
            </legend>
            <div className="grid grid-cols-10 gap-1">
              {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  aria-pressed={intensity === n}
                  aria-label={`${n} of 10`}
                  onClick={() => setIntensity(n)}
                  className={`min-h-[40px] rounded-md font-mono text-sm font-semibold transition cursor-pointer ${
                    n <= intensity ? intensityTone(intensity) : "bg-white/[0.06] text-slate-400 hover:bg-white/10"
                  } ${intensity === n ? "ring-2 ring-white/70" : ""}`}
                >
                  {n}
                </button>
              ))}
            </div>
            <div className="mt-1 flex justify-between text-[11px] text-slate-500">
              <span>mild</span>
              <span>worst imaginable</span>
            </div>
          </fieldset>

          <fieldset>
            <legend className="mb-2 text-xs font-medium text-slate-300">What does it feel like?</legend>
            <div className="flex flex-wrap gap-1.5">
              {QUALITIES.map((q) => (
                <button
                  key={q}
                  type="button"
                  aria-pressed={quality === q}
                  onClick={() => setQuality(q)}
                  className={`min-h-[34px] rounded-full px-3 text-xs capitalize transition cursor-pointer ${
                    quality === q ? "bg-white text-slate-950 font-semibold" : "border border-white/15 text-slate-300 hover:border-white/35"
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>
          </fieldset>

          <label className="block text-xs font-medium text-slate-300">
            Note (optional)
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={280}
              placeholder="e.g. started after the EVA, worse when lifting"
              className="mt-1.5 min-h-[40px] w-full rounded-lg border border-white/15 bg-[#05070B] px-3 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
            />
          </label>

          <button
            type="submit"
            disabled={busy || !live}
            className="min-h-[44px] w-full rounded-lg bg-emerald-400 text-sm font-semibold text-[#04231F] transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
          >
            {busy ? "Sending…" : existing ? `Update ${part.label.toLowerCase()} pain` : `Report ${part.label.toLowerCase()} pain`}
          </button>
          {!live && <p className="text-xs text-amber-300">Pain reports need the onboard backend.</p>}
        </form>
      )}

      {reports.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-slate-300">Active pain</h3>
          <ul className="mt-2 divide-y divide-white/[0.06]">
            {reports.map((r) => (
              <li key={r.region} className="flex items-center gap-3 py-2">
                <span className={`rounded-md px-2 py-0.5 font-mono text-xs font-bold ${intensityTone(r.intensity)}`}>{r.intensity}</span>
                <span className="flex-1 text-sm text-slate-200">
                  {r.region_label} <span className="text-xs text-slate-500">· {r.quality}</span>
                </span>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onResolve(r.region)}
                  className="inline-flex min-h-[32px] items-center gap-1 rounded-md px-2 text-xs text-slate-400 hover:bg-white/5 hover:text-white cursor-pointer"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> Resolved
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {reports.length > 0 && (crossDiagnosis || mlPainSummary) && (
        <div className="mt-auto rounded-xl bg-white/[0.04] p-4 text-xs leading-relaxed">
          <p className="font-medium text-slate-300">How the system read it</p>
          {crossDiagnosis && (
            <p className="mt-1 text-slate-200">
              <span className="text-slate-400">Cause tree:</span> {crossDiagnosis.title}
              {crossDiagnosis.earth_priority === "IMMEDIATE" && (
                <span className="ml-1 font-semibold text-red-300">· Flight Surgeon now</span>
              )}
            </p>
          )}
          {mlPainSummary && (
            <p className="mt-1 text-slate-200">
              <span className="text-slate-400">ML:</span> {mlPainSummary}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
