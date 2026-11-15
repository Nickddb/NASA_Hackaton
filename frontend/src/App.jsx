import { useCallback, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import AgentChatPanel from "./components/AgentChatPanel";
import BodyModel3D from "./components/BodyModel3D";
import ChatBar from "./components/ChatBar";
import CrewHub from "./components/CrewHub";
import CriticalAlertModal from "./components/CriticalAlertModal";
import EmergencyProtocol from "./components/EmergencyProtocol";
import HomeDashboard from "./components/HomeDashboard";
import SmartwatchSim from "./components/SmartwatchSim";
import SpaceBackdrop from "./components/SpaceBackdrop";
import TelemedDossier from "./components/TelemedDossier";
import VitalsDashboard from "./components/VitalsDashboard";
import {
  acknowledgeCrewAlert,
  dispatchCrewAlert,
  generateTelemedicineDossier,
  getCrewRoster,
  getEnvironmentStatuses,
  getMissionState,
  getPsychologicalReadiness,
  measureCrewMember,
  selectCrewMember,
  sendAgentChat,
  stabilizeCrewMember,
  switchEnvironment,
  switchScenario,
  triggerMeasurement,
} from "./services/api";

export default function App() {
  const [state, setState] = useState(null);
  const [roster, setRoster] = useState(null);
  const [activeCrewId, setActiveCrewId] = useState("elena_vance");
  const [viewMode] = useState("control");
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState(false);
  const [error, setError] = useState("");
  const [selectedSystem, setSelectedSystem] = useState("cardiovascular");

  const [dossier, setDossier] = useState(null);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [tab, setTab] = useState("crew");
  const [dismissedCriticalKeys, setDismissedCriticalKeys] = useState([]);

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

  const dismissCriticalKey = (key) => {
    setDismissedCriticalKeys((prev) => (prev.includes(key) ? prev : [...prev, key]));
  };

  const handleInspectCriticalCrew = async (crewId, key) => {
    dismissCriticalKey(key);
    await handleSelectAstronaut(crewId);
  };

  const handleAcknowledgeFromPopup = async (crewId, key) => {
    await handleAcknowledgeAlert(crewId);
    dismissCriticalKey(key);
  };

  return (
    <div className="space-bg relative flex min-h-screen flex-col overflow-x-hidden text-[#F8FAFC]">
      <SpaceBackdrop />

      {/* Main Content */}
      <main className="relative z-10 mx-auto w-full max-w-[1400px] flex-1 px-4 pb-6 pt-8 sm:px-8">
        {/* Hero */}
        <section className="mb-7">
          {tab !== "crew" && (
            <button
              type="button"
              onClick={() => setTab("crew")}
              className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 bg-[#12161E] px-4 py-1.5 text-xs font-semibold text-slate-100 shadow-sm transition hover:border-white/40 hover:bg-[#191F2B] hover:text-white cursor-pointer"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              All Crew (ISS &amp; Mission)
            </button>
          )}

          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-white/15 bg-[#11151D] px-3.5 py-1 text-[11px] font-semibold tracking-wide text-slate-200">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#34D399]" />
            {tab === "crew"
              ? "ISS ORBITAL & DEEP SPACE MISSION CREW COMMAND"
              : "ORBITAL TO DEEP SPACE BIOMEDICAL TELEMETRY"}
          </div>

          {tab === "crew" ? (
            <>
              <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
                Crew Health &amp;{" "}
                <span className="text-sky-400">
                  Spacesuit Monitor
                </span>
              </h1>
              <p className="mt-2 text-base text-slate-300">
                Unified status across ISS Orbital stations and Deep Space vehicles — click any astronaut to zoom into their individual medical cockpit.
              </p>
            </>
          ) : (
            <>
              <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
                Welcome,{" "}
                <span className="text-sky-400">
                  {state?.crew_member || "Astronaut!"}
                </span>
              </h1>
              <p className="mt-2 text-base text-slate-300">
                Track your exams and monitor your health in real time — from deep-space orbit down to Earth biosphere vitals.
                <span className="ml-2 text-xs text-slate-400">
                  {state?.crew_role || "Crew"} • {state?.location_module || "ISS"} • Mission Day {state?.mission_day ?? 142} • Latency{" "}
                  {state?.one_way_latency_seconds ?? 0}s
                </span>
              </p>
            </>
          )}
        </section>

        {error && (
          <div className="mb-4 rounded-2xl border border-red-500/60 bg-red-950/60 px-4 py-3 text-sm font-medium text-red-200">
            {error}
          </div>
        )}

        {loading && !state && !roster ? (
          <div className="flex min-h-[420px] flex-col items-center justify-center rounded-3xl border border-white/15 bg-[#0E1218] p-8">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-white/15 border-t-sky-400" />
            <p className="mt-4 text-sm font-semibold text-slate-200">Initializing AstraCare telemetry...</p>
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
                busyAction={busyAction}
                onTriggerMeasurement={handleTriggerMeasurement}
                onSelectSystem={setSelectedSystem}
                onStabilizeCrew={handleStabilizeCrew}
                onSwitchEnvironment={handleSwitchEnvironment}
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
        <div className="sticky bottom-0 z-20 bg-gradient-to-t from-[#030406] via-[#030406]/90 to-transparent pb-4 pt-6">
          <div className="mx-auto max-w-[1400px] px-4 sm:px-8">
            <ChatBar onSendChat={handleSendChat} />
          </div>
        </div>
      )}

      <footer className="relative z-10 border-t border-white/10 bg-[#050608]/95 py-4 text-center text-[11px] text-slate-400">
        AstraCare AI • From Deep Cosmos to Earth Biosphere • Built with NASA Data • NASA-STD-3001 &amp; OCHMO Clinical Standards
      </footer>

      {/* Telemedicine Dossier Modal */}
      <TelemedDossier
        dossier={dossier}
        loading={dossierLoading}
        onClose={() => {
          setDossier(null);
          setDossierLoading(false);
        }}
      />

      {/* Global Critical Alert Pop-up (auto-opens on critical alerts across Crew Hub & Cockpit) */}
      <CriticalAlertModal
        alerts={visibleCriticalAlerts}
        viewMode={viewMode}
        busyAction={busyAction}
        onInspectCrew={handleInspectCriticalCrew}
        onAcknowledge={handleAcknowledgeFromPopup}
        onDismiss={dismissCriticalKey}
        onDismissAll={() => setDismissedCriticalKeys((prev) => Array.from(new Set([...prev, ...visibleCriticalAlerts.map((a) => a.key)])))}
      />
    </div>
  );
}
