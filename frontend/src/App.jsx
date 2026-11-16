import { useCallback, useEffect, useRef, useState } from "react";
import { BellRing, FileText } from "lucide-react";
import AgentChatPanel from "./components/AgentChatPanel";
import AppSidebar, { MobileTabBar } from "./components/AppSidebar";
import ClinicalContinuity from "./components/ClinicalContinuity";
import CrewHub from "./components/CrewHub";
import CriticalAlertModal from "./components/CriticalAlertModal";
import EmergencyProtocol from "./components/EmergencyProtocol";
import { EnvironmentSectorSummary } from "./components/EnvironmentPanel";
import HomeDashboard, { MissionTelemetryBar } from "./components/HomeDashboard";
import { PsychCrewBar } from "./components/PsychRankPanel";
import SpaceBackdrop from "./components/SpaceBackdrop";
import TelemedDossier from "./components/TelemedDossier";
import {
  acknowledgeCrewAlert,
  dispatchCrewAlert,
  generateTelemedicineDossier,
  getCrewRoster,
  getEnvironmentStatuses,
  getMissionState,
  getPsychologicalReadiness,
  getSpaceWeather,
  measureCrewMember,
  nextTelemetryReading,
  reportPain,
  resolvePain,
  selectCrewMember,
  sendAgentChat,
  stabilizeCrewMember,
  subscribeConnectionMode,
  switchEnvironment,
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
  const [spaceWeather, setSpaceWeather] = useState(null);
  const [page, setPage] = useState("crew");
  const [dismissedCriticalKeys, setDismissedCriticalKeys] = useState([]);
  const [connection, setConnection] = useState("unknown");

  useEffect(() => subscribeConnectionMode(setConnection), []);

  // ---- Live readings from the backend's NASA-calibrated generator (no browser-side synthetic series) ----
  const [streaming, setStreaming] = useState(false);
  const [liveReadings, setLiveReadings] = useState([]);
  const [donkiRefreshing, setDonkiRefreshing] = useState(false);
  const live = connection === "live";

  useEffect(() => {
    if (!state?.vitals || !live) return;
    const t = new Date(state.last_updated || Date.now()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setLiveReadings((prev) => {
      if (prev.length && prev[prev.length - 1].key === state.last_updated) return prev;
      const point = { key: state.last_updated, t, hr: Math.round(state.vitals.heart_rate_bpm * 10) / 10, sys: Math.round(state.vitals.bp_systolic) };
      return [...prev, point].slice(-40);
    });
  }, [state?.last_updated, state?.vitals, live]);

  const takeReading = useCallback(async () => {
    try {
      const next = await nextTelemetryReading(0);
      setState(next);
      setRoster(await getCrewRoster(next));
    } catch (err) {
      setStreaming(false);
      setError(err?.message || "Could not read the sensor stream.");
    }
  }, []);

  useEffect(() => {
    if (!streaming || !live) return undefined;
    const id = setInterval(takeReading, 5000);
    return () => clearInterval(id);
  }, [streaming, live, takeReading]);

  const handleRefreshDonki = async () => {
    setDonkiRefreshing(true);
    try {
      setSpaceWeather(await getSpaceWeather(true));
      await loadState();
    } finally {
      setDonkiRefreshing(false);
    }
  };

  const loadState = useCallback(async (crewOverride = null) => {
    const targetCrew = typeof crewOverride === "string" ? crewOverride : activeCrewId;
    try {
      const stateData = await getMissionState(targetCrew);
      const rosterData = await getCrewRoster(stateData);
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

  const handleSelectAstronaut = async (crewId, targetPage = "vitals") => {
    setBusyAction(true);
    try {
      setStreaming(false);
      setLiveReadings([]);
      const next = await selectCrewMember(crewId);
      setActiveCrewId(crewId);
      setState(next);
      const rosterData = await getCrewRoster(next);
      setRoster(rosterData);
      setPage(targetPage);
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
      const nextRoster = await getCrewRoster(nextState?.astronaut_id ? nextState : undefined);
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
      const nextRoster = await getCrewRoster(reading?.state?.astronaut_id ? reading.state : undefined);
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

  const handleSwitchEnvironment = async (envId) => {
    setBusyAction(true);
    try {
      const next = await switchEnvironment(envId, activeCrewId);
      setState(next);
      const nextRoster = await getCrewRoster(next?.astronaut_id ? next : undefined);
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
      const nextRoster = await getCrewRoster(reading?.state?.astronaut_id ? reading.state : undefined);
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

  const [painBusy, setPainBusy] = useState(false);
  const withPain = async (fn) => {
    setPainBusy(true);
    try {
      const next = await fn();
      setState(next);
      setRoster(await getCrewRoster(next));
      setError("");
    } catch (err) {
      setError(err?.message || "Could not update the pain report.");
    } finally {
      setPainBusy(false);
    }
  };
  const handleReportPain = (payload) => withPain(() => reportPain(activeCrewId, payload));
  const handleResolvePain = (region) => withPain(() => resolvePain(activeCrewId, region));

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
  const criticalAlertEntries = (roster?.crew || [])
    .map((m) => {
      const psych = getPsychologicalReadiness(m.vitals, m.personal_baseline, {
        environmentId: m.environment_id,
      });
      const envEval = getEnvironmentStatuses(m.mission_context, m.vitals, m.personal_baseline);
      const isCrit = m.status === "CRITICAL" || psych.status === "CRITICAL" || envEval.overall === "CRITICAL";
      if (!isCrit) return null;
      const alertToken = m.active_alert?.alert_id || m.scenario_id || "CRITICAL";
      return {
        key: `${m.crew_id}:${alertToken}:${psych.status === "CRITICAL" ? "P" : ""}:${envEval.overall === "CRITICAL" ? "E" : ""}`,
        member: m,
      };
    })
    .filter(Boolean)
    .sort((a, b) => (a.member.crew_id === activeCrewId ? -1 : b.member.crew_id === activeCrewId ? 1 : 0));

  const visibleCriticalAlerts = criticalAlertEntries.filter((entry) => !dismissedCriticalKeys.includes(entry.key));
  const activeCriticalKeySignature = criticalAlertEntries.map((e) => e.key).join("|");

  useEffect(() => {
    const validKeys = new Set(activeCriticalKeySignature ? activeCriticalKeySignature.split("|") : []);
    setDismissedCriticalKeys((prev) => {
      const next = prev.filter((k) => validKeys.has(k));
      return next.length === prev.length ? prev : next;
    });
  }, [activeCriticalKeySignature]);

  // The alert opens by itself only when a NEW critical alert appears. Alerts already present at load time stay
  // collapsed in a compact button, so the dashboard is not covered on every page; the sidebar badge always shows.
  const [alertOpen, setAlertOpen] = useState(false);
  const seenAlertKeys = useRef(null);
  useEffect(() => {
    if (!roster) return;
    const keys = activeCriticalKeySignature ? activeCriticalKeySignature.split("|") : [];
    if (seenAlertKeys.current !== null && keys.some((k) => !seenAlertKeys.current.includes(k))) setAlertOpen(true);
    seenAlertKeys.current = keys;
  }, [activeCriticalKeySignature, roster]);

  const dismissCriticalKey = (key) => {
    setDismissedCriticalKeys((prev) => (prev.includes(key) ? prev : [...prev, key]));
  };

  const handleInspectCriticalCrew = async (crewId, key) => {
    dismissCriticalKey(key);
    await handleSelectAstronaut(crewId, "vitals");
  };

  const handleAcknowledgeFromPopup = async (crewId, key) => {
    await handleAcknowledgeAlert(crewId);
    dismissCriticalKey(key);
  };

  const crewList = roster?.crew || [];
  const alertCount = (fleetCounts?.critical || 0) + (fleetCounts?.warning || 0);
  const firstName = (state?.crew_member || "").replace(/\s*\(.*\)$/, "");

  const navigate = (next) => {
    setPage(next);
    window.scrollTo({ top: 0 });
  };

  const crewSwitcher = (
    <label className="flex items-center gap-2 text-xs text-slate-400 lg:hidden">
      <span className="sr-only">Astronaut</span>
      <select
        value={activeCrewId}
        onChange={(e) => handleSelectAstronaut(e.target.value, page)}
        className="min-h-[40px] rounded-lg border border-white/15 bg-[#0E1218] px-3 text-sm text-white"
      >
        {crewList.map((m) => (
          <option key={m.crew_id} value={m.crew_id}>
            {m.name.replace(/\s*\(.*\)$/, "")} · {m.status.toLowerCase()}
          </option>
        ))}
      </select>
    </label>
  );

  const astronautMeta = state && (
    <>
      {state.crew_role || "Crew"} · {state.location_module || "ISS"} · Day {state.mission_day ?? 142} · {state.one_way_latency_seconds ?? 0}s to Earth
    </>
  );

  const PAGES = {
    crew: {
      title: "Crew",
      subtitle: `${crewList.length} astronauts · ISS orbit and deep-space transit · Sol ${roster?.mission_day ?? 142}`,
      actions: (
        <div role="group" aria-label="Console" className="flex rounded-lg border border-white/12 p-0.5 text-xs">
          {[
            ["control", "Mission Control"],
            ["crew", "Crew onboard"],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-pressed={viewMode === id}
              onClick={() => setViewMode(id)}
              className={`min-h-[34px] rounded-md px-3 font-semibold cursor-pointer ${
                viewMode === id ? "bg-white text-slate-950" : "text-slate-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      ),
    },
    vitals: { title: firstName || "Vitals", subtitle: astronautMeta, astronaut: true },
    diagnosis: { title: "Diagnosis", subtitle: firstName, astronaut: true },
    mind: { title: "Mind", subtitle: `${firstName} · psychological readiness and behavioural load`, astronaut: true },
    assistant: { title: "Assistant", subtitle: `Ask about ${firstName || "the crew"}: vitals, causes, follow-up, NASA data`, astronaut: true },
    environment: { title: "Environment", subtitle: "Space weather (NASA DONKI) and cabin sensors by habitat" },
  };
  const current = PAGES[page] || PAGES.crew;

  const pageBody = () => {
    switch (page) {
      case "crew":
        return (
          <CrewHub
            roster={roster}
            viewMode={viewMode}
            busyAction={busyAction}
            onSelectAstronaut={(id) => handleSelectAstronaut(id, "vitals")}
            onDispatchAlert={handleDispatchAlert}
            onAcknowledgeAlert={handleAcknowledgeAlert}
            onStabilizeCrew={handleStabilizeCrew}
            onMeasureCrew={handleMeasureCrew}
          />
        );
      case "vitals":
        return (
          <div className="flex flex-col gap-6">
            <EmergencyProtocol state={state} onOpenDossier={handleOpenDossier} />
            <HomeDashboard key={dashboardKey} {...dashboardProps} sections={["baseline", "vitals", "body", "telemetry", "trends"]} />
          </div>
        );
      case "diagnosis":
        return <ClinicalContinuity state={state} connection={connection} onRefresh={() => loadState()} />;
      case "mind":
        return (
          <div className="flex flex-col gap-6">
            <HomeDashboard key={dashboardKey} {...dashboardProps} sections={["psych"]} />
            <section aria-labelledby="crew-mind-title" className="rounded-2xl border border-white/10 bg-[#0B0E14]/80 p-5">
              <h2 id="crew-mind-title" className="text-sm font-semibold text-white">
                Whole crew
              </h2>
              <p className="mt-1 text-xs text-slate-400">Readiness score per astronaut, against each one's own baseline.</p>
              <div className="mt-2 grid gap-x-8 sm:grid-cols-2">
                {crewList.map((m) => (
                  <div key={m.crew_id}>
                    <p className="mt-3 text-xs font-semibold text-slate-200">{m.name.replace(/\s*\(.*\)$/, "")}</p>
                    <PsychCrewBar member={m} />
                  </div>
                ))}
              </div>
            </section>
          </div>
        );
      case "assistant":
        return <AgentChatPanel state={state} onSendChat={handleSendChat} />;
      case "environment":
        return (
          <div className="flex flex-col gap-6">
            <MissionTelemetryBar
              mode="donki"
              sw={state?.space_weather}
              refreshing={donkiRefreshing}
              onRefresh={handleRefreshDonki}
              live={live}
            />
            <EnvironmentSectorSummary crew={crewList} />
            <HomeDashboard key={dashboardKey} {...dashboardProps} sections={["environment"]} />
          </div>
        );
      default:
        return null;
    }
  };

  const dashboardKey = state?.crew_id || state?.astronaut_id || "active";
  const dashboardProps = {
    state,
    busyAction,
    live,
    liveReadings,
    streaming,
    onToggleStream: () => setStreaming((s) => !s),
    onNextReading: takeReading,
    onRefreshDonki: handleRefreshDonki,
    donkiRefreshing,
    onTriggerMeasurement: handleTriggerMeasurement,
    onSelectSystem: setSelectedSystem,
    onStabilizeCrew: handleStabilizeCrew,
    onSwitchEnvironment: handleSwitchEnvironment,
    onReportPain: handleReportPain,
    onResolvePain: handleResolvePain,
    painBusy,
  };

  return (
    <div className="space-bg relative min-h-screen overflow-x-hidden text-[#F8FAFC]">
      <SpaceBackdrop />

      <AppSidebar
        page={page}
        onNavigate={navigate}
        crew={crewList}
        activeCrewId={activeCrewId}
        onSelectCrew={(id) => handleSelectAstronaut(id, current.astronaut ? page : "vitals")}
        connection={connection}
        alertCount={alertCount}
        onOpenStandards={() => setShowOchmoModal(true)}
      />
      <MobileTabBar page={page} onNavigate={navigate} alertCount={alertCount} />

      <main className="relative z-10 mx-auto w-full max-w-[1240px] px-4 pb-28 pt-8 sm:px-8 lg:pb-12 lg:pl-[calc(15rem+2rem)] xl:pl-[calc(15rem+3rem)]">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-[1.75rem] font-semibold leading-tight tracking-[-0.02em] text-white">{current.title}</h1>
            {current.subtitle && <p className="mt-1 text-sm text-slate-400">{current.subtitle}</p>}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {current.astronaut && crewSwitcher}
            {current.actions}
            {(page === "vitals" || page === "diagnosis") && (
              <button
                type="button"
                onClick={handleOpenDossier}
                className="inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-white/15 px-3 text-xs font-semibold text-slate-200 hover:border-white/35 hover:text-white cursor-pointer"
              >
                <FileText className="h-4 w-4" aria-hidden="true" /> Dossier for Earth
              </button>
            )}
          </div>
        </div>

        {connection === "simulated" && (
          <p role="status" className="mb-5 rounded-lg border border-amber-400/40 bg-amber-950/40 px-4 py-2.5 text-sm text-amber-200">
            Backend unreachable: the values on screen are simulated in the browser.
          </p>
        )}
        {error && (
          <div role="alert" className="mb-5 rounded-lg border border-red-500/60 bg-red-950/60 px-4 py-3 text-sm font-medium text-red-200">
            {error}
          </div>
        )}

        {loading && !state && !roster ? (
          <div className="flex min-h-[420px] flex-col items-center justify-center rounded-2xl border border-white/10 bg-[#0E1218] p-8">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-white/15 border-t-sky-400" />
            <p className="mt-4 text-sm font-semibold text-slate-200">Initializing AstraCare telemetry…</p>
          </div>
        ) : (
          pageBody()
        )}
      </main>

      {/* NASA standards reference */}
      {showOchmoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#030406]/75 p-4 backdrop-blur-sm">
          <div role="dialog" aria-modal="true" aria-labelledby="ochmo-title" className="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-[#CBE2D5] bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#E2EFE8] pb-4">
              <h2 id="ochmo-title" className="text-xl font-bold text-[#113D2E]">
                NASA-STD-3001 &amp; OCHMO reference
              </h2>
              <button
                type="button"
                onClick={() => setShowOchmoModal(false)}
                className="min-h-[44px] rounded-full border border-[#CBE2D5] bg-[#F7FBF9] px-4 text-sm font-semibold text-[#113D2E] hover:bg-[#EFF9F2] cursor-pointer"
              >
                Close
              </button>
            </div>
            <div className="mt-4 space-y-3">
              {OCHMO_LIBRARY.map((item) => (
                <div key={item.code} className="rounded-xl border border-[#CBE2D5] bg-[#F7FBF9] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs font-bold text-[#059669]">{item.code}</span>
                    <span className="rounded-full border border-[#CBE2D5] bg-white px-2.5 py-0.5 text-[11px] font-semibold text-[#113D2E]">
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

      <TelemedDossier
        dossier={dossier}
        loading={dossierLoading}
        onClose={() => {
          setDossier(null);
          setDossierLoading(false);
        }}
      />

      {/* Critical alerts across the crew: compact button, expands on new alerts or on click */}
      {!alertOpen && visibleCriticalAlerts.length > 0 && (
        <button
          type="button"
          onClick={() => setAlertOpen(true)}
          className="fixed bottom-20 right-4 z-40 inline-flex min-h-[44px] items-center gap-2 rounded-full border border-red-500/70 bg-[#1A080C]/95 px-4 text-sm font-semibold text-red-100 shadow-[0_8px_24px_rgba(0,0,0,0.45)] backdrop-blur-md hover:border-red-400 cursor-pointer lg:bottom-6 sm:right-6"
        >
          <BellRing className="h-4 w-4 text-red-300" aria-hidden="true" />
          {visibleCriticalAlerts.length} critical alert{visibleCriticalAlerts.length > 1 ? "s" : ""}
        </button>
      )}
      {alertOpen && (
      <CriticalAlertModal
        onMinimize={() => setAlertOpen(false)}
        alerts={visibleCriticalAlerts}
        viewMode={viewMode}
        busyAction={busyAction}
        onInspectCrew={handleInspectCriticalCrew}
        onAcknowledge={handleAcknowledgeFromPopup}
        onDismiss={dismissCriticalKey}
        onDismissAll={() => setDismissedCriticalKeys((prev) => Array.from(new Set([...prev, ...visibleCriticalAlerts.map((a) => a.key)])))}
      />
      )}
    </div>
  );
}
