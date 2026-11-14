import { useCallback, useEffect, useRef, useState } from "react";
import { BarChart3, Home, LogOut, Orbit, Settings } from "lucide-react";
import AgentChatPanel from "./components/AgentChatPanel";
import BodyModel3D from "./components/BodyModel3D";
import ChatBar from "./components/ChatBar";
import EmergencyProtocol from "./components/EmergencyProtocol";
import HomeDashboard from "./components/HomeDashboard";
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
  const [selectedSystem, setSelectedSystem] = useState("cardiovascular");

  const [dossier, setDossier] = useState(null);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [showOchmoModal, setShowOchmoModal] = useState(false);
  const [showWeatherDrawer, setShowWeatherDrawer] = useState(false);
  const [spaceWeather, setSpaceWeather] = useState(null);
  const [tab, setTab] = useState("home");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef(null);

  useEffect(() => {
    const close = (e) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target)) setSettingsOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

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

  const handleTriggerMeasurement = async (systemId) => {
    setBusyAction(true);
    try {
      const reading = await triggerMeasurement(systemId);
      await loadState();
      setError("");
      return reading;
    } catch (err) {
      setError(err?.message || "Measurement failed.");
      return null;
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
    const res = await sendAgentChat(message);
    await loadState();
    return res;
  };

  const overallStatus = state?.clinical_evaluation?.overall_status || "NOMINAL";
  const statusDot =
    overallStatus === "CRITICAL" ? "bg-[#EF4444] animate-ping" : overallStatus === "WARNING" ? "bg-[#F59E0B]" : "bg-[#22C55E]";

  const navBtn = (active) =>
    `relative flex h-11 w-11 items-center justify-center rounded-xl transition ${
      active ? "text-white" : "text-[#CBD5E1] hover:bg-white/5 hover:text-white"
    }`;

  return (
    <div className="space-bg relative flex min-h-screen flex-col overflow-x-hidden text-white">
      {/* Vertical Continuum Backdrop Layers: Cosmos -> Aurora -> Stratosphere Clouds -> Emerald Biosphere */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {/* Layer 1 (Top): Deep Cosmos Nebula & Orbiting Planet */}
        <div className="earth absolute -right-40 -top-24 h-[520px] w-[520px] rounded-full" />
        <div className="absolute left-[8%] top-[4%] h-44 w-96 rounded-full bg-[#A855F7]/20 blur-3xl" />

        {/* Layer 2 (Upper-Mid): Aurora Borealis Shimmering Curtain */}
        <div className="absolute -left-20 top-[18%] h-40 w-[120%] -rotate-2 bg-gradient-to-r from-transparent via-[#10B981]/25 to-[#38BDF8]/25 blur-3xl" />

        {/* Layer 3 (Middle): Stratosphere Soft Cloud Wisps */}
        <div className="absolute left-[5%] top-[48%] h-48 w-[55%] rounded-full bg-white/[0.04] blur-3xl" />
        <div className="absolute right-[6%] top-[54%] h-44 w-[48%] rounded-full bg-[#BAE6FD]/[0.06] blur-3xl" />

        {/* Layer 4 (Bottom): Emerald Biosphere Canopy & Waterfall Mist Horizon */}
        <svg
          viewBox="0 0 1440 320"
          preserveAspectRatio="none"
          className="absolute bottom-0 left-0 h-[280px] w-full opacity-45"
        >
          <defs>
            <linearGradient id="biosphereHills" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#042F2E" stopOpacity="0.85" />
            </linearGradient>
            <linearGradient id="biosphereFore" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#059669" stopOpacity="0.45" />
              <stop offset="50%" stopColor="#0D9488" stopOpacity="0.55" />
              <stop offset="100%" stopColor="#022C22" stopOpacity="0.92" />
            </linearGradient>
          </defs>
          {/* Distant Emerald Mountains */}
          <path
            fill="url(#biosphereHills)"
            d="M0,160 C240,90 420,210 720,140 C1020,70 1220,170 1440,110 L1440,320 L0,320 Z"
          />
          {/* Foreground Forest Valley & River Curve */}
          <path
            fill="url(#biosphereFore)"
            d="M0,215 C310,165 540,265 890,195 C1140,145 1310,210 1440,185 L1440,320 L0,320 Z"
          />
        </svg>
      </div>

      {/* Top Navigation */}
      <header className="sticky top-0 z-30 border-b border-[#3B82F6]/30 bg-[#050B1A]/70 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-3 px-4 py-3 sm:px-8">
          <button type="button" onClick={() => setTab("home")} className="flex items-center gap-3">
            <Orbit className="h-9 w-9 text-white" strokeWidth={1.6} />
            <span className="text-lg font-semibold tracking-tight text-white">AstraCare</span>
            <span className="hidden items-center gap-1.5 rounded-full border border-[#3B82F6]/40 px-2.5 py-0.5 text-[10px] font-semibold text-[#BFDBFE] sm:inline-flex">
              <span className={`h-1.5 w-1.5 rounded-full ${statusDot}`} />
              {overallStatus}
            </span>
          </button>

          <nav className="flex items-center gap-2">
            <button type="button" title="Home" onClick={() => setTab("home")} className={navBtn(tab === "home")}>
              <Home className="h-6 w-6" strokeWidth={1.7} />
              {tab === "home" && <span className="absolute -bottom-1.5 left-1 right-1 h-0.5 rounded bg-[#60A5FA]" />}
            </button>
            <button type="button" title="Analytics" onClick={() => setTab("analytics")} className={navBtn(tab === "analytics")}>
              <BarChart3 className="h-6 w-6" strokeWidth={1.7} />
              {tab === "analytics" && <span className="absolute -bottom-1.5 left-1 right-1 h-0.5 rounded bg-[#60A5FA]" />}
            </button>
            <div className="relative" ref={settingsRef}>
              <button type="button" title="Settings" onClick={() => setSettingsOpen((o) => !o)} className={navBtn(settingsOpen)}>
                <Settings className="h-6 w-6" strokeWidth={1.7} />
              </button>
              {settingsOpen && (
                <div className="absolute right-0 top-12 z-40 w-60 overflow-hidden rounded-2xl border border-[#3B82F6]/30 bg-[#0B1530]/95 p-1.5 text-sm shadow-xl backdrop-blur-md">
                  {[
                    { label: "NASA DONKI Space Weather", action: handleToggleWeather },
                    { label: "OCHMO Standards", action: () => setShowOchmoModal(true) },
                    { label: "Telemedicine Dossier", action: handleOpenDossier },
                    { label: "Scenarios & Smartwatch", action: () => setTab("analytics") },
                  ].map((item) => (
                    <button
                      key={item.label}
                      type="button"
                      onClick={() => {
                        setSettingsOpen(false);
                        item.action();
                      }}
                      className="block w-full rounded-xl px-3 py-2 text-left text-[#DBEAFE] hover:bg-[#1D4ED8]/30"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              type="button"
              title="End session"
              onClick={() => {
                setTab("home");
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              className={navBtn(false)}
            >
              <LogOut className="h-6 w-6" strokeWidth={1.7} />
            </button>
          </nav>
        </div>

        {showWeatherDrawer && (
          <div className="border-t border-[#3B82F6]/30 bg-[#0B1530]/90 px-4 py-2.5 sm:px-8">
            <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="rounded-full bg-[#2563EB] px-3 py-1 font-bold text-white">DONKI FEED</span>
                <span className="text-[#DBEAFE]">
                  {spaceWeather?.alara_instruction ||
                    spaceWeather?.summary ||
                    state?.space_weather?.alara_instruction ||
                    "Solar activity nominal. Onboard radiation dosimeter active."}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-[11px] text-[#94A3B8]">
                  Source: {spaceWeather?.source || "NASA DONKI + Onboard Dosimetry"}
                </span>
                <button type="button" onClick={handleToggleWeather} className="text-[#93C5FD] hover:text-white">
                  ✕
                </button>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="relative z-10 mx-auto w-full max-w-[1400px] flex-1 px-4 pb-6 pt-10 sm:px-8">
        {/* Hero */}
        <section className="mb-8">
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[#34D399]/35 bg-[#064E3B]/40 px-3.5 py-1 text-[11px] font-semibold tracking-wide text-[#A7F3D0] backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-[#34D399]" />
            COSMOS → AURORA → STRATOSPHERE → EARTH BIOSPHERE TELEMETRY
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
            Welcome,{" "}
            <span className="bg-gradient-to-r from-[#C084FC] via-[#38BDF8] to-[#34D399] bg-clip-text text-transparent">
              Astronaut!
            </span>
          </h1>
          <p className="mt-2 text-base text-[#E2E8F0]">
            Track your exams and monitor your health in real time — from deep-space orbit down to Earth biosphere vitals.
            <span className="ml-2 text-xs text-[#A7F3D0]/80">
              {state?.crew_member || "Cmdr. Elena Vance"} • Mission Day {state?.mission_day ?? 142} • Latency{" "}
              {state?.one_way_latency_seconds ?? 0}s
            </span>
          </p>
        </section>

        {error && (
          <div className="mb-4 rounded-2xl border border-[#F87171]/50 bg-[#7F1D1D]/40 px-4 py-3 text-sm font-medium text-[#FECACA]">
            {error}
          </div>
        )}

        {loading && !state ? (
          <div className="flex min-h-[420px] flex-col items-center justify-center rounded-3xl border border-[#3B82F6]/30 bg-[#0B1530]/60 p-8">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#1E3A8A] border-t-[#60A5FA]" />
            <p className="mt-4 text-sm font-semibold text-[#BFDBFE]">Initializing AstraCare telemetry...</p>
          </div>
        ) : (
          <>
            <EmergencyProtocol state={state} onOpenDossier={handleOpenDossier} />

            {tab === "home" ? (
              <HomeDashboard
                state={state}
                onTriggerMeasurement={handleTriggerMeasurement}
                onSelectSystem={setSelectedSystem}
              />
            ) : (
              /* Detailed clinical workspace (original panels) */
              <div className="rounded-3xl bg-[#F7FBF9] p-4 text-[#113D2E] sm:p-5">
                <SmartwatchSim
                  state={state}
                  loadingScenario={busyAction}
                  onSwitchScenario={handleSwitchScenario}
                  onSwitchEnvironment={handleSwitchEnvironment}
                  onTriggerWristScan={handleTriggerMeasurement}
                />
                <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-12">
                  <div className="xl:col-span-4">
                    <BodyModel3D
                      state={state}
                      selectedSystem={selectedSystem}
                      onSelectSystem={setSelectedSystem}
                      onTriggerMeasurement={handleTriggerMeasurement}
                    />
                  </div>
                  <div className="xl:col-span-4">
                    <VitalsDashboard state={state} onSelectSystem={setSelectedSystem} />
                  </div>
                  <div className="xl:col-span-4">
                    <AgentChatPanel state={state} onSendChat={handleSendChat} />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Bottom assistant bar */}
      {tab === "home" && (
        <div className="sticky bottom-0 z-20 bg-gradient-to-t from-[#04231F] via-[#062C28]/85 to-transparent pb-4 pt-6">
          <div className="mx-auto max-w-[1400px] px-4 sm:px-8">
            <ChatBar onSendChat={handleSendChat} />
          </div>
        </div>
      )}

      <footer className="relative z-10 border-t border-[#10B981]/25 bg-[#04231F]/60 py-4 text-center text-[11px] text-[#A7F3D0]/75 backdrop-blur-sm">
        AstraCare AI • From Deep Cosmos to Earth Biosphere • Built with NASA Data • NASA-STD-3001 &amp; OCHMO Clinical Standards
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
