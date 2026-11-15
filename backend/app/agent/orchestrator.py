from __future__ import annotations

import json
import re
from typing import Any

from app import config
from app.agent.mission_tools import MissionAgentTools, build_mission_tools
from app.agent.tools import (
    build_agent_tools,
    parse_followup_command_text,
    parse_nutrition_text,
    parse_sleep_mood_context_text,
)
from app.engine.cross_diagnosis import evaluate_cross_diagnosis, render_cross_diagnosis, SYMPTOM_REPORT, _norm
from app.models.schemas import ChatResponse, ToolTraceItem
from app.state_manager import MissionStateManager

SYSTEM_PROMPT = """You are AstraCare Medical Officer, an explainable, auditable, offline-first clinical decision-support AI aboard a long-duration space mission.
You MUST adhere strictly to the 5 AstraCare AI Clinical & Machine Learning Pillars:
1. ADAPTIVE INDIVIDUAL BASELINE: Always compare vitals against the astronaut's personal rolling EWMA/MAD baseline and NASA OSDR (OSD-570/571) gravitational phase offset, not just population averages. Cite individual_z_score, population_z_score, and Multivariate Mahalanobis distance.
2. CONTEXTUAL MISSION INTELLIGENCE: Relate readings to sleep, ARED/T2/CEVIS exercise recency, EVA workload, gravity phase, and cabin environment (ppCO2, O2, pressure). State explicitly that contextual correlations are observational and do NOT assume automatic causality without a confirmatory measurement.
3. CLOSED-LOOP FOLLOW-UP CYCLE: Never stop at an alert. Reference the active ClinicalFollowUpCase, required confirmation measurements, executed protocol actions, and scheduled timed reassessments (T+15m / T+30m).
4. EXPLAINABLE & AUDITABLE AI: State originating signals, sensor measurement quality (SNR %, motion artifact, NIBP verification), epistemic + aleatoric uncertainty %, 72h Bayesian forecast, and exact NASA-STD-3001 / OCHMO / OSDR references. NEVER invent treatments or make autonomous medical decisions — all actions are protocol checklists requiring Crew Medical Officer (CMO) / Flight Surgeon confirmation.
5. SPACECRAFT–EARTH CONTINUITY: Reference NASA JPL Horizons one-way light-time latency, NASA DONKI solar radiation alerts, and SHA-256 store-and-forward EarthSyncPackage bundles when discussing ground coordination.
Respond in the same language as the user (Portuguese if the user writes in Portuguese; English otherwise).
MULTI-TOOL MONITORING (tool chaining): to check a crew member, call schedule_smartwatch_exam (trigger_now) or
run_monitoring_cycle, then analyze_telemetry_and_diagnose. Read its status/category/next_tools: call
trigger_central_alert when it lists it (CRITICAL or escalated WARNING) and activate_psychological_stimuli only when the
category is PSYCHOLOGICAL (never for a physical or space-weather cause). Each tool returns JSON; base the next call on it."""

# chat intents for the multi-tool chain when no LLM is configured
EXAM_INTENT = re.compile(
    r"\b(agend\w*|schedul\w*|exame|exam|smartwatch|rel[oó]gio|ciclo de monitoramento|monitoring cycle|"
    r"verificar? (?:agora|o|a)|check (?:now|on)|analis\w+ telemetria|analy[sz]e telemetry)\b",
    re.IGNORECASE,
)
EXAM_TYPE_WORDS = {
    "cardio": ("cardio", "coração", "coracao", "heart", "pressão", "pressao"),
    "cognitive_ctb": ("cognit", "ctb", "reação", "reacao", "reaction"),
    "dosimetry": ("dosim", "radia"),
    "respiratory": ("respir", "spo2", "oxig"),
    "metabolic": ("metab", "glic", "glucose"),
}
INTERVAL = re.compile(r"(?:a cada|every)\s+(\d+(?:[.,]\d+)?)\s*(h|hora|hour|min)", re.IGNORECASE)


class AstraCareOrchestrator:
    """
    Phase 2 Chatbot & Clinical Decision-Support Orchestrator.
    Integrates LangChain Gemini tool-calling with a 100% deterministic offline-first hybrid edge pipeline
    grounded in all 5 ML & Clinical Continuity Pillars.
    """

    def __init__(self, state_manager: MissionStateManager, mission_agent: MissionAgentTools | None = None) -> None:
        self.state_manager = state_manager
        self.mission_agent = mission_agent or MissionAgentTools(state_manager)

    async def handle_chat(self, message: str, crew_id: str | None = None) -> ChatResponse:
        if crew_id and crew_id in self.state_manager.crew_records:
            self.state_manager.select_crew_member(crew_id)
        trace_log: list[ToolTraceItem] = []
        tools = build_agent_tools(self.state_manager, trace_log) + build_mission_tools(self.mission_agent, trace_log)
        tools_by_name = {t.name: t for t in tools}

        api_key = config.GEMINI_API_KEY
        if api_key:
            try:
                import asyncio
                from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
                from langchain_google_genai import ChatGoogleGenerativeAI

                lc_tools = [t.to_langchain_tool() for t in tools]
                llm = ChatGoogleGenerativeAI(
                    model=config.LLM_MODEL,
                    google_api_key=api_key,
                    temperature=0.15,
                ).bind_tools(lc_tools)

                state = self.state_manager.get_state()
                context_msg = (
                    f"Active Crew={state.crew_member} ({state.astronaut_id}), Scenario={state.scenario_name}, "
                    f"Env={state.environment_name} ({state.mission_context.gravitational_g}g), "
                    f"Personal Drift={state.adaptive_baseline.personal_drift_score}% "
                    f"(Mahalanobis={state.adaptive_baseline.multivariate_mahalanobis_distance}), "
                    f"Context-Adjusted ML Anomaly={state.ml_prediction.anomaly_score}% "
                    f"({state.ml_prediction.predicted_syndrome_label}, {state.ml_prediction.confidence_pct}% ± "
                    f"{state.ml_prediction.uncertainty.total_uncertainty_pct}%), "
                    f"Sensor Quality={state.measurement_quality.overall_quality_pct}% ({state.measurement_quality.reliability_grade})."
                )

                messages: list[Any] = [
                    SystemMessage(content=f"{SYSTEM_PROMPT}\n{context_msg}"),
                    HumanMessage(content=message),
                ]

                # tool chaining: each round's tool results go back to the model, which decides the next call
                ai_msg = await asyncio.wait_for(llm.ainvoke(messages), timeout=config.LLM_TIMEOUT_S)
                rounds = 0
                used_tools = False
                while getattr(ai_msg, "tool_calls", None) and rounds < config.LLM_MAX_TOOL_ROUNDS:
                    used_tools = True
                    rounds += 1
                    messages.append(ai_msg)
                    for tc in ai_msg.tool_calls:
                        fn = tools_by_name.get(tc["name"])
                        result = fn.invoke(tc["args"]) if fn else json.dumps({"error": f"unknown tool {tc['name']}"})
                        messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
                    ai_msg = await asyncio.wait_for(llm.ainvoke(messages), timeout=config.LLM_TIMEOUT_S)

                if used_tools:
                    reply_text = str(ai_msg.content or "") or "\n".join(f"- {t.tool_name}: {t.summary}" for t in trace_log)
                else:
                    tools_by_name["inspect_adaptive_baseline_tool"].invoke({"astronaut_query": "current"})
                    tools_by_name["predict_calibrated_ml_and_uncertainty_tool"].invoke({"horizon": "72h"})
                    tools_by_name["audit_explainable_alerts_and_rules_tool"].invoke({"note": "sync"})
                    reply_text = str(ai_msg.content)

                return ChatResponse(
                    reply=reply_text,
                    mode="langchain_gemini",
                    tool_trace=trace_log,
                    state=self.state_manager.get_state(),
                )
            except Exception:
                trace_log.clear()

        # --- Deterministic Offline-First Hybrid Edge Pipeline (Bilingual EN/PT, Zero Network Required) ---
        lower = message.lower()
        is_pt = any(
            w in lower
            for w in [
                "como",
                "qual",
                "estou",
                "comi",
                "bebi",
                "dormi",
                "sono",
                "alerta",
                "risco",
                "astronauta",
                "confirmei",
                "executei",
                "terra",
                "relatório",
                "relatorio",
                "radiação",
                "radiacao",
                "previsão",
                "previsao",
                "exercício",
                "exercicio",
                "vejo",
                "sinto",
                "sentindo",
                "cheiro",
                "enjoo",
                "luz",
                "irritado",
                "quero",
                "nao",
                "não",
                "nada",
                "ninguem",
                "ninguém",
                "você",
                "voce",
            ]
        )

        reply_parts: list[str] = []

        # 0. Cross diagnosis first: physical vs. NASA DONKI space weather vs. psychological
        if SYMPTOM_REPORT.search(_norm(message)):
            self.state_manager.record_reported_symptom(message[:160])
        cross_state = self.state_manager.get_state()
        cross = evaluate_cross_diagnosis(
            cross_state.vitals, cross_state.mission_context, cross_state.space_weather,
            cross_state.contextual_intelligence, cross_state.clinical_evaluation, message,
        )
        trace_log.append(
            ToolTraceItem(
                tool_name="cross_diagnosis_tree",
                status="CRITICAL" if cross.earth_priority == "IMMEDIATE" else ("WARNING" if cross.layer else "OK"),
                summary=f"Layer {cross.layer}: {cross.root_cause} — {cross.title}",
                rule_or_score=cross.earth_priority,
            )
        )
        reply_parts.append(render_cross_diagnosis(cross, is_pt))
        if cross.psych_protocol and cross.psych_protocol.escalate_to_earth:
            pkg = self.state_manager.escalate_psych_priority(cross.psych_protocol.escalation_reason or "severe psychological risk")
            reply_parts.append(
                f"**Alerta imediato enviado à Terra** (pacote `{pkg.package_id}`): o cirurgião de voo e a equipe de saúde comportamental foram acionados."
                if is_pt
                else f"**Immediate alert sent to Earth** (package `{pkg.package_id}`): Flight Surgeon and behavioral health team notified."
            )

        # 0b. Multi-tool chain: smartwatch exam -> diagnosis -> central alert -> psychological stimuli
        if EXAM_INTENT.search(message):
            reply_parts.append(self._run_exam_intent(message, lower, tools_by_name, is_pt))

        # 1. Check if switching or querying astronaut baseline
        if any(
            w in lower
            for w in [
                "lucas",
                "kenji",
                "elena",
                "amara",
                "liam",
                "baseline",
                "individual",
                "mahalanobis",
                "histórico",
                "historico",
            ]
        ):
            res_base = tools_by_name["inspect_adaptive_baseline_tool"].invoke({"astronaut_query": message})
            header = "**Baseline Individual Adaptativo:**" if is_pt else "**Adaptive Individual Baseline:**"
            reply_parts.append(f"{header} {res_base}")

        # 2. Check Nutrition / Hydration logging
        nutrition_parsed = parse_nutrition_text(message)
        if nutrition_parsed["items"] or re.search(
            r"\b(ate|eat|drank|drink|meal|food|water|apple|apples|comi|bebi|agua|água|refeição|almoço|jantar)\b",
            lower,
        ):
            res_nut = tools_by_name["log_nutrition_hydration_tool"].invoke({"meal_description": message})
            header = "**Nutrição e Hidratação Registradas:**" if is_pt else "**Nutrition & Hydration Updated:**"
            reply_parts.append(f"{header} {res_nut}")

        # 3. Check Sleep / Mood / Shoulder / Exercise / Cabin CO2 context logging
        sleep_ctx_parsed = parse_sleep_mood_context_text(message)
        if sleep_ctx_parsed or re.search(
            r"\b(sleep|slept|tired|dizzy|mood|stress|shoulder|ombro|dormi|sono|exausto|treino|exercício|exercicio|ared|co2)\b",
            lower,
        ):
            res_ctx_log = tools_by_name["log_sleep_mood_context_tool"].invoke({"checkin_text": message})
            header = "**Check-In de Sono, Humor e Contexto Operacional:**" if is_pt else "**Sleep, Mood & Context Check-In:**"
            reply_parts.append(f"{header} {res_ctx_log}")

        # 4. Check Closed-Loop Follow-Up commands (confirmation measurement, action executed, reassessment)
        followup_cmd = parse_followup_command_text(message)
        if followup_cmd:
            act_type = followup_cmd["action_type"]
            if act_type == "confirm" and "metric" in followup_cmd:
                res_fu = tools_by_name["manage_closed_loop_followup_tool"].invoke(
                    {
                        "operation": "confirm",
                        "metric_or_action": followup_cmd["metric"],
                        "measured_value": followup_cmd["value"],
                    }
                )
            elif act_type == "action":
                res_fu = tools_by_name["manage_closed_loop_followup_tool"].invoke(
                    {
                        "operation": "action",
                        "metric_or_action": followup_cmd["description"],
                        "measured_value": 0.0,
                    }
                )
            else:
                res_fu = tools_by_name["manage_closed_loop_followup_tool"].invoke(
                    {
                        "operation": "reassess",
                        "metric_or_action": "resolve" if followup_cmd.get("resolve") else message,
                        "measured_value": 0.0,
                    }
                )
            header = "**Ciclo de Acompanhamento Fechado Atualizado:**" if is_pt else "**Closed-Loop Follow-Up Updated:**"
            reply_parts.append(f"{header} {res_fu}")

        # 5. Check NASA DONKI & JPL Horizons request
        if re.search(
            r"\b(solar|radiation|storm|donki|flare|proton|horizons|latency|radiação|radiacao|tempestade|atraso)\b",
            lower,
        ):
            res_nasa = tools_by_name["check_nasa_donki_and_horizons_tool"].invoke({"window_days": 14})
            header = "**Telemetria NASA DONKI & JPL Horizons:**" if is_pt else "**NASA DONKI & JPL Horizons Telemetry:**"
            reply_parts.append(f"{header} {res_nasa}")

        # 6. Check Psychophysiological Biofeedback Countermeasure trigger (explicit or automatic biometric threshold)
        psych_requested = bool(
            re.search(
                r"\b(ansioso|ansiedade|estressado|estresse|triste|sozinho|solidão|solidao|saudade|família|familia|música|musica|jogo|natureza|animais|anxious|anxiety|lonely|sad|depressed|family|video|music|game|nature|stimulus|estímulo|estimulo|psicológico|psicologico|mental)\b",
                lower,
            )
        )
        # Only an explicit request dispatches the stimulus + central alert. The biometric auto-trigger used to fire on
        # any message (even "what is the status?"); the cross-diagnosis PsychGuard protocol now covers that case.
        if psych_requested:
            res_psych = tools_by_name["trigger_psychological_biofeedback_tool"].invoke(
                {"reason": "conversational_or_biometric_auto_trigger"}
            )
            header = (
                "**Estímulo Psicofisiológico & Alerta Central (MCC-BHP) Acionados:**"
                if is_pt
                else "**Psychophysiological Biofeedback & Central MCC-BHP Alert Dispatched:**"
            )
            reply_parts.append(f"{header} {res_psych}")

        # 7. Check Spacecraft–Earth Continuity / Telemedicine Dossier / Sync request
        if re.search(
            r"\b(dossier|doctor|surgeon|telemed|earth|sync|synchronize|terra|médico|medico|sincronizar|pacote|dossiê|dossie)\b",
            lower,
        ):
            op_mode = "sync" if any(w in lower for w in ["sync", "synchronize", "sincronizar"]) else "dossier_and_queue"
            res_sync = tools_by_name["sync_spacecraft_earth_continuity_tool"].invoke({"operation": op_mode})
            header = "**Continuidade Nave–Terra (Store-and-Forward):**" if is_pt else "**Spacecraft–Earth Continuity:**"
            reply_parts.append(f"{header} {res_sync}")

        # 8. Always execute the core 5-pillar diagnostic & audit tools so the trace and reply are complete
        if not any(t.tool_name == "inspect_adaptive_baseline" for t in trace_log):
            tools_by_name["inspect_adaptive_baseline_tool"].invoke({"astronaut_query": "current"})
        tools_by_name["evaluate_contextual_intelligence_tool"].invoke({"context_note": "hybrid_triage"})
        tools_by_name["predict_calibrated_ml_and_uncertainty_tool"].invoke({"horizon": "72h"})
        tools_by_name["audit_explainable_alerts_and_rules_tool"].invoke({"note": "hybrid_triage"})
        if not any(t.tool_name == "manage_closed_loop_followup" for t in trace_log):
            tools_by_name["manage_closed_loop_followup_tool"].invoke(
                {"operation": "status", "metric_or_action": "", "measured_value": 0.0}
            )

        state = self.state_manager.get_state()
        ab = state.adaptive_baseline
        ctx = state.contextual_intelligence
        ml = state.ml_prediction
        unc = ml.uncertainty
        ev = state.clinical_evaluation
        q = state.measurement_quality

        top_drivers = ", ".join(
            f"{d.label}: {d.current_value} (base pessoal {d.personal_baseline_value}, z={d.individual_z_score:+.1f}σ, peso {d.importance:.0f}%)"
            if is_pt
            else f"{d.label}: {d.current_value} (personal base {d.personal_baseline_value}, z={d.individual_z_score:+.1f}σ, weight {d.importance:.0f}%)"
            for d in ml.feature_importances[:3]
        )

        fc_24 = ml.forecast_72h[0] if ml.forecast_72h else None
        fc_72 = ml.forecast_72h[-1] if ml.forecast_72h else None

        if is_pt:
            reply_parts.append(
                f"**1. Baseline Individual Adaptativo ({ab.astronaut_name}):** "
                f"Fase `{ab.mission_phase}` ({ab.gravitational_g:.2f}g) | Distância de Mahalanobis = **{ab.multivariate_mahalanobis_distance:.2f}** "
                f"(Drift Pessoal: **{ab.personal_drift_score:.1f}%** vs. IsoForest Populacional: **{ml.raw_population_anomaly_score:.1f}%**)."
            )
            reply_parts.append(
                f"**2. Inteligência Contextual da Missão:** {ctx.primary_contextual_summary}\n"
                f"*{ctx.causal_disclaimer}*"
            )
            reply_parts.append(
                f"**3. Machine Learning Calibrado, Qualidade & Incerteza ({ev.overall_status}):** "
                f"Classificação: **{ml.predicted_syndrome_label}** com **{ml.confidence_pct:.1f}%** de confiança "
                f"(IC 95%: `{unc.confidence_interval_95_pct[0]:.1f}%–{unc.confidence_interval_95_pct[1]:.1f}%`; "
                f"Incerteza Total: `{unc.total_uncertainty_pct:.1f}%` [Epistêmica: `{unc.epistemic_ensemble_std_pct:.1f}%`, "
                f"Aleatória/Sensor: `{unc.aleatoric_sensor_noise_pct:.1f}%`]; Qualidade do Sinal: `{q.overall_quality_pct:.0f}%` `{q.reliability_grade}`).\n"
                f"- **Sinais Originadores (Atribuição Contrafactual):** {top_drivers}."
            )
            if fc_24 and fc_72:
                reply_parts.append(
                    f"**4. Previsão Longitudinal BayesianRidge (24h–72h):** "
                    f"Em `+24h`: FC `{fc_24.predicted_hr_bpm:.0f} bpm`, HRV `{fc_24.predicted_hrv_ms:.0f} ms`, Glicemia `{fc_24.predicted_glucose_mg_dl:.0f} mg/dL`, Risco `{fc_24.predicted_anomaly_risk_pct:.0f}%` | "
                    f"Em `+72h`: FC `{fc_72.predicted_hr_bpm:.0f} bpm`, Risco `{fc_72.predicted_anomaly_risk_pct:.0f}%`."
                )
            if state.followup_cases:
                c0 = state.followup_cases[0]
                steps_pt = "\n".join(f"{i}. {s}" for i, s in enumerate(ev.stabilization_checklist[:4], start=1))
                reply_parts.append(
                    f"**5. Ciclo de Acompanhamento Fechado (`{c0.case_id}` — Status: `{c0.status}`):**\n"
                    f"- Confirmações registradas: `{len(c0.confirmations_recorded)}` | Ações executadas: `{len(c0.actions_executed)}` | "
                    f"Próxima reavaliação programada: `T+{c0.reassessments_scheduled[-1].scheduled_for_offset_minutes} min`.\n"
                    f"**Passos de Verificação e Estabilização (Protocolo NASA-STD-3001 / OCHMO):**\n{steps_pt}"
                )
            reply_parts.append(
                f"**Governança e Auditoria Médica:** *{ev.autonomy_guardrail.governance_notice}* "
                f"(Fila Nave–Terra: `{state.earth_sync_queue_count}` pacote(s) pendente(s), atraso JPL Horizons: `{state.one_way_latency_seconds}s`)."
            )
        else:
            reply_parts.append(
                f"**1. Adaptive Individual Baseline ({ab.astronaut_name}):** "
                f"Phase `{ab.mission_phase}` ({ab.gravitational_g:.2f}g) | Mahalanobis Distance = **{ab.multivariate_mahalanobis_distance:.2f}** "
                f"(Personal Drift: **{ab.personal_drift_score:.1f}%** vs. Population IsoForest: **{ml.raw_population_anomaly_score:.1f}%**)."
            )
            reply_parts.append(
                f"**2. Contextual Mission Intelligence:** {ctx.primary_contextual_summary}\n"
                f"*{ctx.causal_disclaimer}*"
            )
            reply_parts.append(
                f"**3. Calibrated ML, Signal Quality & Uncertainty ({ev.overall_status}):** "
                f"Predicted: **{ml.predicted_syndrome_label}** at **{ml.confidence_pct:.1f}%** confidence "
                f"(95% CI: `{unc.confidence_interval_95_pct[0]:.1f}%–{unc.confidence_interval_95_pct[1]:.1f}%`; "
                f"Total Uncertainty: `{unc.total_uncertainty_pct:.1f}%` [Epistemic: `{unc.epistemic_ensemble_std_pct:.1f}%`, "
                f"Aleatoric/Sensor: `{unc.aleatoric_sensor_noise_pct:.1f}%`]; Signal Quality: `{q.overall_quality_pct:.0f}%` `{q.reliability_grade}`).\n"
                f"- **Originating Signals (Counterfactual Attribution):** {top_drivers}."
            )
            if fc_24 and fc_72:
                reply_parts.append(
                    f"**4. 72h BayesianRidge Trajectory Forecast:** "
                    f"`+24h`: HR `{fc_24.predicted_hr_bpm:.0f} bpm`, HRV `{fc_24.predicted_hrv_ms:.0f} ms`, Glucose `{fc_24.predicted_glucose_mg_dl:.0f} mg/dL`, Risk `{fc_24.predicted_anomaly_risk_pct:.0f}%` | "
                    f"`+72h`: HR `{fc_72.predicted_hr_bpm:.0f} bpm`, Risk `{fc_72.predicted_anomaly_risk_pct:.0f}%`."
                )
            if state.followup_cases:
                c0 = state.followup_cases[0]
                steps_en = "\n".join(f"{i}. {s}" for i, s in enumerate(ev.stabilization_checklist[:4], start=1))
                reply_parts.append(
                    f"**5. Closed-Loop Follow-Up Case (`{c0.case_id}` — Status: `{c0.status}`):**\n"
                    f"- Confirmations recorded: `{len(c0.confirmations_recorded)}` | Actions executed: `{len(c0.actions_executed)}` | "
                    f"Next scheduled reassessment: `T+{c0.reassessments_scheduled[-1].scheduled_for_offset_minutes} min`.\n"
                    f"**Protocol Verification & Stabilization Checklist (NASA-STD-3001 / OCHMO):**\n{steps_en}"
                )
            reply_parts.append(
                f"**Medical Governance & Continuity:** *{ev.autonomy_guardrail.governance_notice}* "
                f"(Spacecraft–Earth Queue: `{state.earth_sync_queue_count}` pending package(s), JPL Horizons latency: `{state.one_way_latency_seconds}s`)."
            )

        return ChatResponse(
            reply="\n\n".join(reply_parts),
            mode="offline_hybrid_edge",
            tool_trace=trace_log,
            state=state,
        )

    def _run_exam_intent(self, message: str, lower: str, tools_by_name: dict[str, Any], is_pt: bool) -> str:
        """Offline version of the LLM's tool chain: same tools, same order, decisions read from each JSON output."""
        sm = self.state_manager
        crew = next((cid for cid in sm.crew_records if cid.split("_")[0] in lower), sm.active_crew_id)
        exam = next((ex for ex, words in EXAM_TYPE_WORDS.items() if any(w in lower for w in words)), "full_panel")
        m = INTERVAL.search(message)
        interval = 0.0
        if m:
            interval = float(m.group(1).replace(",", "."))
            interval *= 60 if m.group(2).lower().startswith("h") else 1

        exam_out = json.loads(tools_by_name["schedule_smartwatch_exam"].invoke(
            {"astronaut_id": crew, "exam_type": exam, "interval_minutes": interval, "trigger_now": True}
        ))
        if "error" in exam_out:
            return f"**Smartwatch:** {exam_out['error']}"
        report = json.loads(tools_by_name["analyze_telemetry_and_diagnose"].invoke({"astronaut_id": crew}))
        lines = []
        if exam_out.get("schedule"):
            every = exam_out["schedule"]["interval_minutes"]
            lines.append(f"Exame `{exam}` agendado a cada {every:g} min." if is_pt else f"`{exam}` exam scheduled every {every:g} min.")
        lines.append(
            (f"Leitura coletada: {exam_out['reading_summary']}" if is_pt else f"Reading collected: {exam_out['reading_summary']}")
        )
        lines.append(
            f"**Diagnóstico:** `{report['status']}` · `{report['category']}` — {report['probable_diagnosis']} "
            f"(confiança {report['confidence_score']:.0%})"
            if is_pt
            else f"**Diagnosis:** `{report['status']}` · `{report['category']}` — {report['probable_diagnosis']} "
            f"(confidence {report['confidence_score']:.0%})"
        )
        if "trigger_central_alert" in report["next_tools"]:
            alert = json.loads(tools_by_name["trigger_central_alert"].invoke({"astronaut_id": crew}))
            if alert.get("dispatched"):
                lines.append(
                    f"**Alerta central enviado** aos cirurgiões de voo (pacote `{alert['earth_package_id']}`)."
                    if is_pt
                    else f"**Central alert sent** to the Flight Surgeons (package `{alert['earth_package_id']}`)."
                )
            else:
                lines.append(f"Alerta central não reenviado: {alert.get('reason')}" if is_pt else f"Central alert not re-sent: {alert.get('reason')}")
        if "activate_psychological_stimuli" in report["next_tools"]:
            stim = json.loads(tools_by_name["activate_psychological_stimuli"].invoke({"astronaut_id": crew}))
            if stim.get("activated"):
                titles = "; ".join(s["title"] for s in stim["stimuli"][:3])
                lines.append(
                    f"**Estímulos psicológicos ativados** ({stim['central_alert_id']}): {titles}."
                    if is_pt
                    else f"**Psychological stimuli started** ({stim['central_alert_id']}): {titles}."
                )
        header = "**Agente de monitoramento (smartwatch → diagnóstico → ação):**" if is_pt else "**Monitoring agent (smartwatch → diagnosis → action):**"
        return header + "\n" + "\n".join(f"- {line}" for line in lines)
