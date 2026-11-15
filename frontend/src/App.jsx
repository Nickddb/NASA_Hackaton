import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, BarChart3, Home, LogOut, Orbit, Satellite, Settings, Users } from "lucide-react";
import AgentChatPanel from "./components/AgentChatPanel";
import BodyModel3D from "./components/BodyModel3D";
import ChatBar from "./components/ChatBar";
import CrewHub from "./components/CrewHub";
import EmergencyProtocol from "./components/EmergencyProtocol";
import HomeDashboard from "./components/HomeDashboard";
import SmartwatchSim from "./components/SmartwatchSim";
import TelemedDossier from "./components/TelemedDossier";
import VitalsDashboard from "./components/VitalsDashboard";
import {
  acknowledgeCrewAlert,
  dispatchCrewAlert,
  generateTelemedicineDossier,
  getCrewRoster,
  getMissionState,
  getSpaceWeather,
  measureCrewMember,
  selectCrewMember,
  sendAgentChat,
  stabilizeCrewMember,
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
  const [roster, setRoster] = useState(null);
  const [activeCrewId, setActiveCrewId] = useState("elena_vance");
  const [viewMode, setViewMode] = useState("control");
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState(false);
  const [error, setError] = useState("");
  const [selectedSystem, setSelectedSystem] = useState("cardiovascular");

  const [dossier, setDossier] = useState(null);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [showOchmoModal, setShowOchmoModal] = useState(false);
  const [showWeatherDrawer, setShowWeatherDrawer] = useState(false);
  const [spaceWeather, setSpaceWeather] = useState(null);
  const [tab, setTab] = useState("crew");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef(null);

  useEffect(() => {
    const close = (e) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target)) setSettingsOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const loadState = useCallback(async (crewOverride = null) => {
    const targetCrew = crewOverride || activeCrewId;
    try {
      const [rosterData, stateData] = await Promise.all([
        getCrewRoster(),
        getMissionState(targetCrew),
      ]);
      setRoster(rosterData);
      setState(stateData);
      if (stateData?.crew_id) setActiveCrewId(stateData.crew_id);
      setError("");
    } catch (err) {
      setError(err?.message || "Failed to connect to AstraCare backend.");
    } finally {
      setLoading(false);
    }
  }, [activeCrewId]);

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

  const handleSelectAstronaut = async (crewId) => {
    setBusyAction(true);
    try {
      const next = await selectCrewMember(crewId);
      setActiveCrewId(crewId);
      setState(next);
      const rosterData = await getCrewRoster();
      setRoster(rosterData);
      setTab("home");
      setError("");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err?.message || "Failed to select crew member.");
    } finally {
      setBusyAction(false);
    }
  };

  const handleDispatchAlert = async (crewId, payload) => {
    setBusyAction(true);
    try {
      const nextRoster = await dispatchCrewAlert(crewId, payload);
      setRoster(nextRoster);
      if (crewId === activeCrewId) {
        const nextState = await getMissionState(crewId);
        setState(nextState);
      }
      setError("");
    } catch (err) {
      setError(err?.message || "Failed to dispatch alert.");
    } finally {
      setBusyAction(false);
    }
  };

  const handleAcknowledgeAlert = async (crewId) => {
    setBusyAction(true);
    try {
      const nextRoster = await acknowledgeCrewAlert(crewId);
      setRoster(nextRoster);
      if (crewId === activeCrewId) {
        const nextState = await getMissionState(crewId);
        setState(nextState);
      }
      setError("");
    } catch (err) {
      setError(err?.message || "Failed to acknowledge alert.");
    } finally {
      setBusyAction(false);
    }
  };

  const handleStabilizeCrew = async (crewId, note) => {
    setBusyAction(true);
    try {
      const nextState = await stabilizeCrewMember(crewId, note);
      if (crewId === activeCrewId) setState(nextState);
      const nextRoster = await getCrewRoster();
      setRoster(nextRoster);
      setError("");
      return nextState;
    } catch (err) {
      setError(err?.message || "Stabilization protocol failed.");
      return null;
    } finally {
      setBusyAction(false);
    }
  };

  const handleMeasureCrew = async (crewId, systemId = "full_body") => {
    setBusyAction(true);
    try {
      const reading = await measureCrewMember(crewId, systemId);
      if (crewId === activeCrewId && reading?.state) setState(reading.state);
      const nextRoster = await getCrewRoster();
      setRoster(nextRoster);
      setError("");
      return reading;
    } catch (err) {
      setError(err?.message || "Measurement failed.");
      return null;
    } finally {
      setBusyAction(false);
    }
  };

  const handleSwitchScenario = async (scenarioId) => {
    setBusyAction(true);
    try {
      const next = await switchScenario(scenarioId, activeCrewId);
      setState(next);
      const nextRoster = await getCrewRoster();
      setRoster(nextRoster);
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
      const next = await switchEnvironment(envId, activeCrewId);
      setState(next);
      const nextRoster = await getCrewRoster();
      setRoster(nextRoster);
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
      const reading = await triggerMeasurement(systemId, activeCrewId);
      if (reading?.state) setState(reading.state);
      const nextRoster = await getCrewRoster();
      setRoster(nextRoster);
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
      const data = await generateTelemedicineDossier(activeCrewId);
      setDossier(data);
    } catch (err) {
      setError(err?.message || "Could not generate telemedicine dossier.");
    } finally {
      setDossierLoading(false);
    }
  };

  const handleSendChat = async (message) => {
    const res = await sendAgentChat(message, activeCrewId);
    await loadState(activeCrewId);
    return res;
  };

  const fleetCounts = roster?.summary_counts;
  const fleetStatus =
    (fleetCounts?.critical || 0) > 0
      ? "CRITICAL"
      : (fleetCounts?.warning || 0) > 0
      ? "WARNING"
      : "NOMINAL";
  const overallStatus = tab === "crew" ? fleetStatus : (state?.clinical_evaluation?.overall_status || "NOMINAL");
  const statusDot =
    overallStatus === "CRITICAL"
      ? "bg-[#EF4444] animate-ping"
      : overallStatus === "WARNING"
      ? "bg-[#F59E0B] animate-pulse"
      : "bg-[#34D399] shadow-[0_0_8px_#34D399]";

  const statusBadgeClass =
    overallStatus === "CRITICAL"
      ? "border-red-400/50 bg-red-950/75 text-red-200 shadow-[0_0_16px_rgba(239,68,68,0.4)]"
      : overallStatus === "WARNING"
      ? "border-amber-400/50 bg-amber-950/75 text-amber-200 shadow-[0_0_14px_rgba(245,158,11,0.3)]"
      : "border-emerald-400/40 bg-[#071E2E]/85 text-emerald-200 shadow-[0_0_16px_rgba(52,211,153,0.28)]";

  const navBtn = (active) =>
    `relative flex h-11 w-11 items-center justify-center rounded-xl transition cursor-pointer ${
      active
        ? "border border-emerald-300/45 bg-gradient-to-b from-emerald-400/20 via-sky-400/15 to-transparent text-white shadow-[0_0_18px_rgba(52,211,153,0.3)]"
        : "border border-transparent text-[#CBD5E1] hover:border-white/15 hover:bg-white/5 hover:text-white"
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

      {/* Top Navigation — Arctic Aurora Borealis & Orbital Telemetry Header */}
      <header className="aurora-header-shell sticky top-0 z-30 relative border-b border-emerald-400/20 backdrop-blur-xl">
        {/* Dynamic Aurora Borealis Ribbons & Starfield Layers (Clipped to Header Bar so Dropdowns can overflow) */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="aurora-starfield absolute inset-0 opacity-85" />
          <div className="aurora-curtain-primary absolute -inset-x-16 -top-10 h-44" />
          <div className="aurora-curtain-secondary absolute inset-0 opacity-90" />

          {/* Subtle SVG Polar Ionosphere Wave Curtains */}
          <svg
            className="absolute inset-0 h-full w-full opacity-35"
            preserveAspectRatio="none"
            viewBox="0 0 1440 84"
            fill="none"
          >
            <path
              d="M0 62 C320 14, 620 82, 960 32 C1180 6, 1320 48, 1440 22"
              stroke="url(#auroraWave1)"
              strokeWidth="1.8"
            />
            <path
              d="M0 26 C280 70, 740 8, 1080 54 C1260 76, 1360 24, 1440 44"
              stroke="url(#auroraWave2)"
              strokeWidth="1.2"
              strokeDasharray="6 6"
            />
            <defs>
              <linearGradient id="auroraWave1" x1="0" y1="0" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#10B981" stopOpacity="0" />
                <stop offset="28%" stopColor="#34D399" stopOpacity="0.95" />
                <stop offset="62%" stopColor="#38BDF8" stopOpacity="0.9" />
                <stop offset="86%" stopColor="#C084FC" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#A7F3D0" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="auroraWave2" x1="0" y1="0" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#38BDF8" stopOpacity="0" />
                <stop offset="45%" stopColor="#A7F3D0" stopOpacity="0.75" />
                <stop offset="80%" stopColor="#818CF8" stopOpacity="0.65" />
                <stop offset="100%" stopColor="#34D399" stopOpacity="0" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <div className="relative z-10 mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-8">
          {/* Left: Brand + Animated Orbital Emblem + Status Pill */}
          <button
            type="button"
            onClick={() => setTab("crew")}
            className="group flex items-center gap-3.5 text-left cursor-pointer"
          >
            <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-300/35 bg-[#051224]/85 shadow-[0_0_24px_rgba(16,185,129,0.3)] backdrop-blur-md transition group-hover:border-emerald-300/70">
              <div className="pointer-events-none absolute -inset-1 rounded-2xl bg-gradient-to-tr from-emerald-400/25 via-sky-400/25 to-purple-400/25 blur-sm transition group-hover:opacity-100" />
              <Orbit className="relative h-6 w-6 text-emerald-200 transition-transform duration-700 group-hover:rotate-90" strokeWidth={1.8} />
            </div>

            <div>
              <div className="flex items-center gap-2.5">
                <span className="bg-gradient-to-r from-white via-emerald-100 to-sky-200 bg-clip-text text-xl font-extrabold tracking-tight text-transparent drop-shadow-[0_2px_12px_rgba(52,211,153,0.3)]">
                  AstraCare
                </span>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wider uppercase backdrop-blur-md ${statusBadgeClass}`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${statusDot}`} />
                  {overallStatus}
                </span>
              </div>
              <div className="hidden items-center gap-2 text-[11px] text-emerald-100/75 sm:flex">
                <span>Polar &amp; Orbital Bio-Shield</span>
                <span className="text-emerald-400/60">•</span>
                <span className="font-mono text-emerald-300">SOL {state?.mission_day ?? 142}</span>
              </div>
            </div>
          </button>

          {/* Center: View Role Toggle (Mission Control vs Crew Onboard) + Bio-Wave */}
          <div className="flex flex-wrap items-center gap-3">
            <div
              className="flex items-center rounded-full border border-emerald-300/25 bg-[#040E1E]/85 p-1 backdrop-blur-md"
              role="group"
              aria-label="Perspective Mode"
            >
              <button
                type="button"
                onClick={() => setViewMode("control")}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-bold transition cursor-pointer ${
                  viewMode === "control"
                    ? "bg-gradient-to-r from-[#0284C7] to-[#10B981] text-white shadow-[0_0_12px_rgba(16,185,129,0.4)]"
                    : "text-slate-300 hover:text-white"
                }`}
              >
                <Satellite className="h-3.5 w-3.5" />
                Mission Control
              </button>
              <button
                type="button"
                onClick={() => setViewMode("crew")}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-bold transition cursor-pointer ${
                  viewMode === "crew"
                    ? "bg-gradient-to-r from-[#0284C7] to-[#10B981] text-white shadow-[0_0_12px_rgba(56,189,248,0.4)]"
                    : "text-slate-300 hover:text-white"
                }`}
              >
                <Users className="h-3.5 w-3.5" />
                Crew Onboard
              </button>
            </div>

            <div className="hidden xl:flex items-center gap-3 rounded-full border border-emerald-300/20 bg-[#040E1E]/70 px-4 py-1.5 backdrop-blur-md shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                </span>
                <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-emerald-200">
                  AURORA SYNC
                </span>
              </div>

              <div className="h-3.5 w-[1px] bg-white/15" />

              {/* Live Shimmering Bio-Wave SVG */}
              <svg viewBox="0 0 110 24" className="h-5 w-20">
                <path
                  d="M0,12 L18,12 L23,6 L28,18 L34,3 L40,21 L45,12 L68,12 L74,7 L80,12 L110,12"
                  fill="none"
                  stroke="url(#ecgAuroraGrad)"
                  strokeWidth="2"
                  className="animate-ecg"
                />
                <defs>
                  <linearGradient id="ecgAuroraGrad" x1="0" y1="0" x2="110" y2="0" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#34D399" />
                    <stop offset="0.5" stopColor="#38BDF8" />
                    <stop offset="1" stopColor="#C084FC" />
                  </linearGradient>
                </defs>
              </svg>

              <div className="font-mono text-[11px] font-semibold text-sky-200">
                {tab === "crew"
                  ? `${fleetCounts?.total ?? 5} CREW • ${(fleetCounts?.critical ?? 0) + (fleetCounts?.warning ?? 0)} ALERTS`
                  : state?.vitals
                  ? `${Math.round(state.vitals.heart_rate_bpm)} BPM | ${state.vitals.radiation_msv_h.toFixed(2)} mSv/h`
                  : "72 BPM"}
              </div>
            </div>
          </div>

          {/* Right: Iconic Navigation Dock (Crew Hub, Home Cockpit, Analytics, Settings, Return) */}
          <nav className="flex items-center gap-1.5 rounded-2xl border border-white/12 bg-[#040D1C]/75 p-1.5 shadow-[0_8px_24px_rgba(0,0,0,0.4)] backdrop-blur-md">
            <button type="button" title="All Crew (ISS & Mission)" onClick={() => setTab("crew")} className={navBtn(tab === "crew")}>
              <Users className="h-5 w-5" strokeWidth={1.8} />
              {tab === "crew" && (
                <span className="absolute -bottom-1 left-2 right-2 h-0.5 rounded-full bg-gradient-to-r from-[#34D399] via-[#38BDF8] to-[#C084FC] shadow-[0_0_8px_#34D399]" />
              )}
            </button>
            <button type="button" title="Astronaut Cockpit" onClick={() => setTab("home")} className={navBtn(tab === "home")}>
              <Home className="h-5 w-5" strokeWidth={1.8} />
              {tab === "home" && (
                <span className="absolute -bottom-1 left-2 right-2 h-0.5 rounded-full bg-gradient-to-r from-[#34D399] via-[#38BDF8] to-[#C084FC] shadow-[0_0_8px_#34D399]" />
              )}
            </button>
            <button type="button" title="Clinical Analytics" onClick={() => setTab("analytics")} className={navBtn(tab === "analytics")}>
              <BarChart3 className="h-5 w-5" strokeWidth={1.8} />
              {tab === "analytics" && (
                <span className="absolute -bottom-1 left-2 right-2 h-0.5 rounded-full bg-gradient-to-r from-[#34D399] via-[#38BDF8] to-[#C084FC] shadow-[0_0_8px_#38BDF8]" />
              )}
            </button>
            <div className="relative" ref={settingsRef}>
              <button type="button" title="Settings" onClick={() => setSettingsOpen((o) => !o)} className={navBtn(settingsOpen)}>
                <Settings className="h-5 w-5" strokeWidth={1.8} />
                {settingsOpen && (
                  <span className="absolute -bottom-1 left-2 right-2 h-0.5 rounded-full bg-gradient-to-r from-[#34D399] to-[#38BDF8]" />
                )}
              </button>
              {settingsOpen && (
                <div className="absolute right-0 top-13 z-40 w-64 overflow-hidden rounded-2xl border border-emerald-400/30 bg-[#061226]/95 p-1.5 text-sm shadow-[0_16px_40px_rgba(0,0,0,0.75)] backdrop-blur-xl">
                  {[
                    { label: "Crew & ISS Command Hub", action: () => setTab("crew") },
                    { label: "NASA DONKI Aurora & Weather", action: handleToggleWeather },
                    { label: "OCHMO Clinical Standards", action: () => setShowOchmoModal(true) },
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
                      className="block w-full rounded-xl px-3.5 py-2.5 text-left text-xs font-medium text-emerald-50 transition hover:bg-gradient-to-r hover:from-emerald-500/25 hover:to-sky-500/20 hover:text-white cursor-pointer"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              type="button"
              title="Back to Crew Hub"
              onClick={() => {
                setTab("crew");
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              className={navBtn(false)}
            >
              <LogOut className="h-5 w-5" strokeWidth={1.8} />
            </button>
          </nav>
        </div>

        {/* Dynamic Shimmering Aurora Horizon Ribbon at Bottom Border */}
        <div className="aurora-horizon-beam h-[2.5px] w-full" />

        {showWeatherDrawer && (
          <div className="relative z-10 border-t border-emerald-400/25 bg-[#041022]/90 px-4 py-2.5 backdrop-blur-xl sm:px-8">
            <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="rounded-full border border-emerald-300/40 bg-emerald-500/20 px-3 py-1 font-bold text-emerald-200">
                  DONKI AURORA FEED
                </span>
                <span className="text-[#DBEAFE]">
                  {spaceWeather?.alara_instruction ||
                    spaceWeather?.summary ||
                    state?.space_weather?.alara_instruction ||
                    "Solar activity nominal. Onboard radiation dosimeter active."}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-[11px] text-emerald-300/80">
                  Source: {spaceWeather?.source || "NASA DONKI + Onboard Dosimetry"}
                </span>
                <button type="button" onClick={handleToggleWeather} className="text-emerald-300 hover:text-white cursor-pointer">
                  ✕
                </button>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="relative z-10 mx-auto w-full max-w-[1400px] flex-1 px-4 pb-6 pt-8 sm:px-8">
        {/* Hero */}
        <section className="mb-7">
          {tab !== "crew" && (
            <button
              type="button"
              onClick={() => setTab("crew")}
              className="mb-4 inline-flex items-center gap-2 rounded-full border border-sky-300/40 bg-[#04142B]/85 px-4 py-1.5 text-xs font-semibold text-sky-100 shadow-[0_0_16px_rgba(56,189,248,0.2)] transition hover:border-emerald-300/70 hover:text-white cursor-pointer"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              All Crew (ISS &amp; Mission)
            </button>
          )}

          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[#34D399]/35 bg-[#064E3B]/40 px-3.5 py-1 text-[11px] font-semibold tracking-wide text-[#A7F3D0] backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-[#34D399]" />
            {tab === "crew"
              ? "ISS ORBITAL & DEEP SPACE MISSION CREW COMMAND"
              : "COSMOS → AURORA → STRATOSPHERE → EARTH BIOSPHERE TELEMETRY"}
          </div>

          {tab === "crew" ? (
            <>
              <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
                Crew Health &amp;{" "}
                <span className="bg-gradient-to-r from-[#C084FC] via-[#38BDF8] to-[#34D399] bg-clip-text text-transparent">
                  Spacesuit Monitor
                </span>
              </h1>
              <p className="mt-2 text-base text-[#E2E8F0]">
                Unified status across ISS Orbital stations and Deep Space vehicles — click any astronaut to zoom into their individual medical cockpit.
              </p>
            </>
          ) : (
            <>
              <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
                Welcome,{" "}
                <span className="bg-gradient-to-r from-[#C084FC] via-[#38BDF8] to-[#34D399] bg-clip-text text-transparent">
                  {state?.crew_member || "Astronaut!"}
                </span>
              </h1>
              <p className="mt-2 text-base text-[#E2E8F0]">
                Track your exams and monitor your health in real time — from deep-space orbit down to Earth biosphere vitals.
                <span className="ml-2 text-xs text-[#A7F3D0]/80">
                  {state?.crew_role || "Crew"} • {state?.location_module || "ISS"} • Mission Day {state?.mission_day ?? 142} • Latency{" "}
                  {state?.one_way_latency_seconds ?? 0}s
                </span>
              </p>
            </>
          )}
        </section>

        {error && (
          <div className="mb-4 rounded-2xl border border-[#F87171]/50 bg-[#7F1D1D]/40 px-4 py-3 text-sm font-medium text-[#FECACA]">
            {error}
          </div>
        )}

        {loading && !state && !roster ? (
          <div className="flex min-h-[420px] flex-col items-center justify-center rounded-3xl border border-[#3B82F6]/30 bg-[#0B1530]/60 p-8">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#1E3A8A] border-t-[#60A5FA]" />
            <p className="mt-4 text-sm font-semibold text-[#BFDBFE]">Initializing AstraCare telemetry...</p>
          </div>
        ) : (
          <>
            {tab !== "crew" && <EmergencyProtocol state={state} onOpenDossier={handleOpenDossier} />}

            {tab === "crew" ? (
              <CrewHub
                roster={roster}
                viewMode={viewMode}
                busyAction={busyAction}
                onSelectAstronaut={handleSelectAstronaut}
                onDispatchAlert={handleDispatchAlert}
                onAcknowledgeAlert={handleAcknowledgeAlert}
                onStabilizeCrew={handleStabilizeCrew}
                onMeasureCrew={handleMeasureCrew}
              />
            ) : tab === "home" ? (
              <HomeDashboard
                key={state?.crew_id || "active"}
                state={state}
                onTriggerMeasurement={handleTriggerMeasurement}
                onSelectSystem={setSelectedSystem}
                onStabilizeCrew={handleStabilizeCrew}
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
