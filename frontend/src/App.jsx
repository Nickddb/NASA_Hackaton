import { useCallback, useEffect, useState } from "react";
import AgentChatPanel from "./components/AgentChatPanel";
import BodyModel3D from "./components/BodyModel3D";
import EmergencyProtocol from "./components/EmergencyProtocol";
import SmartwatchSim from "./components/SmartwatchSim";
import TelemedDossier from "./components/TelemedDossier";
import VitalsDashboard from "./components/VitalsDashboard";
import {
  generateTelemedicineDossier,
  getMissionState,
  getSpaceWeather,
  sendAgentChat,
  switchEnvironment,
  switchScenario,
  triggerMeasurement,
} from "./services/api";

const OCHMO_LIBRARY = [
  {
    code: "NASA-STD-3001 Vol 2 §6.2",
    title: "Cardiovascular & Orthostatic Tolerance",
    threshold: "HR 50–100 bpm resting | SpO2 >= 95% | Systolic 95–135 mmHg",
    note: "Monitors fluid shift, post-EVA orthostatic intolerance, and arrhythmias under microgravity.",
  },
  {
    code: "NASA-STD-3001 Vol 2 §7.1",
    title: "Hydration & Renal Stone Prevention",
    threshold: "Fluid >= 2.5 L/day | Urinary Output >= 2.0 L/day",
    note: "Bone demineralization in microgravity elevates urinary calcium; hydration is primary countermeasure.",
  },
  {
    code: "NASA-STD-3001 Vol 2 §6.6",
    title: "Space Radiation & Solar Particle Events",
    threshold: "ALARA | SPE Alert > 10 mSv/hr | Deep Space Shielding Required",
    note: "Integrates live NASA DONKI CME/SEP alerts to trigger storm-shelter protocol and antioxidant dosing.",
  },
  {
    code: "OCHMO-MED-04",
    title: "SANS (Spaceflight-Associated Neuro-ocular Syndrome)",
    threshold: "ICP proxy & Optic Nerve Sheath Diameter monitoring",
    note: "Cephalad fluid shift increases intracranial pressure; LBNP and resistive countermeasures evaluated.",
  },
];

export default function App() {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState(false);
  const [error, setError] = useState("");
  const [selectedOrgan, setSelectedOrgan] = useState("heart");

  const [dossier, setDossier] = useState(null);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [showOchmoModal, setShowOchmoModal] = useState(false);
  const [showWeatherDrawer, setShowWeatherDrawer] = useState(false);
  const [spaceWeather, setSpaceWeather] = useState(null);

  const loadState = useCallback(async () => {
    try {
      const data = await getMissionState();
      setState(data);
      setError("");
    } catch (err) {
      setError(err?.message || "Failed to connect to AstraCare backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadState();
  }, [loadState]);

  const handleToggleWeather = async () => {
    const next = !showWeatherDrawer;
    setShowWeatherDrawer(next);
    if (next && !spaceWeather) {
      try {
        const w = await getSpaceWeather();
        setSpaceWeather(w);
      } catch {
        setSpaceWeather({ source: "OFFLINE_FALLBACK", summary: "DONKI feed unavailable; using onboard dosimeter." });
      }
    }
  };

  const handleSwitchScenario = async (scenarioId) => {
    setBusyAction(true);
    try {
      const next = await switchScenario(scenarioId);
      setState(next);
      setError("");
    } catch (err) {
      setError(err?.message || "Failed to switch scenario.");
    } finally {
      setBusyAction(false);
    }
  };

  const handleSwitchEnvironment = async (envId) => {
    setBusyAction(true);
    try {
      const next = await switchEnvironment(envId);
      setState(next);
      setError("");
    } catch (err) {
      setError(err?.message || "Failed to switch environment.");
    } finally {
      setBusyAction(false);
    }
  };

  const handleTriggerMeasurement = async (type) => {
    setBusyAction(true);
    try {
      const next = await triggerMeasurement(type);
      setState(next);
      setError("");
    } catch (err) {
      setError(err?.message || "Measurement failed.");
    } finally {
      setBusyAction(false);
    }
  };

  const handleOpenDossier = async () => {
    setDossierLoading(true);
    setDossier(null);
    try {
      const data = await generateTelemedicineDossier();
      setDossier(data);
    } catch (err) {
      setError(err?.message || "Could not generate telemedicine dossier.");
    } finally {
      setDossierLoading(false);
    }
  };

  const handleSendChat = async (message) => {
    return await sendAgentChat(message);
  };

  const overallStatus = state?.clinical_evaluation?.overall_status || "NOMINAL";
  const statusPillClass =
    overallStatus === "CRITICAL"
      ? "border-[#FCA5A5] bg-[#FEF2F2] text-[#991B1B]"
      : overallStatus === "WARNING"
      ? "border-[#FCD34D] bg-[#FFFBEB] text-[#92400E]"
      : "border-[#A7F3D0] bg-[#ECFDF5] text-[#065F46]";

  return (
    <div className="flex min-h-screen flex-col text-[#113D2E]">
      {/* Sticky Top Navigation Bar */}
      <header className="sticky top-0 z-30 border-b border-[#D5E8DD] bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#113D2E] text-[#C8EE90] shadow-sm">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 4.5v15m7.5-7.5h-15"
                />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-extrabold tracking-tight text-[#113D2E]">
                  AstraCare AI
                </h1>
                <span className="rounded-full bg-[#EFF9F2] px-2.5 py-0.5 text-[11px] font-bold text-[#059669] border border-[#CBE2D5]">
                  AUTONOMOUS FLIGHT SURGEON
                </span>
              </div>
              <p className="text-xs text-[#476458]">
                {state?.crew_member || "Cmdr. Elena Vance"} • Mission Day{" "}
                {state?.mission_day ?? 142} • Latency {state?.one_way_latency_seconds ?? 0}s
              </p>
            </div>
          </div>

          {/* Right Controls */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex min-h-[38px] items-center gap-1.5 rounded-full border px-3.5 text-xs font-bold ${statusPillClass}`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  overallStatus === "CRITICAL"
                    ? "bg-[#DC2626] animate-ping"
                    : overallStatus === "WARNING"
                    ? "bg-[#D97706]"
                    : "bg-[#059669]"
                }`}
              />
              {overallStatus}
            </span>

            <button
              type="button"
              onClick={handleToggleWeather}
              className={`min-h-[44px] rounded-full border px-4 text-xs font-semibold transition ${
                showWeatherDrawer
                  ? "border-[#113D2E] bg-[#113D2E] text-white"
                  : "border-[#CBE2D5] bg-[#EFF9F2] text-[#113D2E] hover:bg-[#C8EE90]/50"
              }`}
            >
              NASA DONKI Space Weather
            </button>

            <button
              type="button"
              onClick={() => setShowOchmoModal(true)}
              className="min-h-[44px] rounded-full border border-[#CBE2D5] bg-white px-4 text-xs font-semibold text-[#113D2E] transition hover:bg-[#EFF9F2]"
            >
              OCHMO Standards
            </button>

            <button
              type="button"
              onClick={handleOpenDossier}
              className="min-h-[44px] rounded-full bg-[#C8EE90] px-4 text-xs font-bold text-[#113D2E] shadow-sm transition hover:bg-[#b8e576]"
            >
              Telemedicine Dossier
            </button>
          </div>
        </div>

        {/* Collapsible NASA DONKI Space Weather Drawer */}
        {showWeatherDrawer && (
          <div className="border-t border-[#CBE2D5] bg-[#EFF9F2] px-4 py-3 sm:px-6">
            <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="rounded-full bg-[#113D2E] px-3 py-1 font-bold text-[#C8EE90]">
                  DONKI FEED
                </span>
                <span className="font-semibold text-[#113D2E]">
                  {spaceWeather?.summary ||
                    state?.space_weather?.summary ||
                    "Solar activity nominal. Onboard radiation dosimeter active."}
                </span>
              </div>
              <span className="font-mono text-[11px] text-[#476458]">
                Source: {spaceWeather?.source || "NASA DONKI + Onboard Dosimetry"}
              </span>
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-6 sm:px-6">
        {error && (
          <div className="mb-4 rounded-2xl border border-[#FCA5A5] bg-[#FEF2F2] px-4 py-3 text-sm font-medium text-[#991B1B]">
            {error}
          </div>
        )}

        {loading && !state ? (
          <div className="eco-card flex min-h-[420px] flex-col items-center justify-center rounded-3xl bg-white p-8">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#CBE2D5] border-t-[#113D2E]" />
            <p className="mt-4 text-sm font-semibold text-[#113D2E]">
              Initializing AstraCare Medical Cleanroom Telemetry...
            </p>
          </div>
        ) : (
          <>
            <EmergencyProtocol state={state} onOpenDossier={handleOpenDossier} />

            <SmartwatchSim
              state={state}
              busy={busyAction}
              onSwitchScenario={handleSwitchScenario}
              onSwitchEnvironment={handleSwitchEnvironment}
              onTriggerMeasurement={handleTriggerMeasurement}
            />

            {/* 3-Column Clinical Workspace */}
            <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-12">
              <div className="xl:col-span-4">
                <BodyModel3D
                  state={state}
                  selectedOrgan={selectedOrgan}
                  onSelectOrgan={setSelectedOrgan}
                  onTriggerMeasurement={handleTriggerMeasurement}
                />
              </div>

              <div className="xl:col-span-4">
                <VitalsDashboard state={state} selectedOrgan={selectedOrgan} />
              </div>

              <div className="xl:col-span-4">
                <AgentChatPanel state={state} onSendChat={handleSendChat} />
              </div>
            </div>
          </>
        )}
      </main>

      {/* Deep Forest Footer Band */}
      <footer className="mt-10 bg-[#113D2E] text-white">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-3 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#C8EE90]" />
              <span className="text-sm font-bold tracking-tight">AstraCare AI</span>
            </div>
            <p className="mt-1 text-xs text-[#CBE2D5]">
              Autonomous Deep-Space Medical Telemetry & Flight Surgeon Decision Support
            </p>
          </div>
          <p className="text-xs font-medium text-[#C8EE90]">
            Built with NASA Data • NASA-STD-3001 & OCHMO Clinical Standards
          </p>
        </div>
      </footer>

      {/* OCHMO Clinical Reference Modal */}
      {showOchmoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#113D2E]/40 p-4 backdrop-blur-sm">
          <div className="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-[#CBE2D5] bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#E2EFE8] pb-4">
              <div>
                <span className="rounded-full bg-[#EFF9F2] px-3 py-1 text-xs font-bold text-[#059669] border border-[#CBE2D5]">
                  CLINICAL STANDARDS
                </span>
                <h2 className="mt-2 text-xl font-bold text-[#113D2E]">
                  NASA-STD-3001 & OCHMO Reference Library
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setShowOchmoModal(false)}
                className="min-h-[44px] rounded-full border border-[#CBE2D5] bg-[#F7FBF9] px-4 text-sm font-semibold text-[#113D2E] hover:bg-[#EFF9F2]"
              >
                Close
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {OCHMO_LIBRARY.map((item) => (
                <div
                  key={item.code}
                  className="rounded-2xl border border-[#CBE2D5] bg-[#F7FBF9] p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs font-bold text-[#059669]">{item.code}</span>
                    <span className="rounded-full bg-white px-2.5 py-0.5 text-[11px] font-semibold text-[#113D2E] border border-[#CBE2D5]">
                      {item.threshold}
                    </span>
                  </div>
                  <h3 className="mt-1.5 text-sm font-bold text-[#113D2E]">{item.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-[#476458]">{item.note}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Telemedicine Dossier Modal */}
      <TelemedDossier
        dossier={dossier}
        loading={dossierLoading}
        onClose={() => {
          setDossier(null);
          setDossierLoading(false);
        }}
      />
    </div>
  );
}
