from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.agent.tools import build_agent_tools, parse_nutrition_text, parse_sleep_mood_text
from app.models.schemas import ChatResponse, ToolTraceItem
from app.state_manager import MissionStateManager

SYSTEM_PROMPT = """You are AstraCare Medical Officer, an autonomous offline-first spaceflight medical AI aboard a NASA/Artemis mission.
You guide non-medical astronauts clearly and concisely in English.
Always use your tools to inspect live NASA-STD-3001 clinical rules, scikit-learn anomaly/syndrome risk, NASA DONKI solar weather, or to log nutrition/sleep/mood updates.
Never hallucinate vital numbers. Cite specific OCHMO standards (MTB-006 Shoulder, MTB-009 Circadian, MTB-011 PFO/DCS, TB-043 LHS, TB-044 MORD) when relevant and give concrete, calm step-by-step actions."""


class AstraCareOrchestrator:
    """Layer 3 LangChain Tool-Calling Agent with deterministic offline-first hybrid fallback."""

    def __init__(self, state_manager: MissionStateManager) -> None:
        self.state_manager = state_manager

    async def handle_chat(self, message: str) -> ChatResponse:
        trace_log: list[ToolTraceItem] = []
        tools = build_agent_tools(self.state_manager, trace_log)
        tools_by_name = {t.name: t for t in tools}

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                import asyncio
                from langchain_google_genai import ChatGoogleGenerativeAI

                llm = ChatGoogleGenerativeAI(
                    model=os.getenv("ASTRACARE_LLM_MODEL", "gemini-2.5-flash"),
                    google_api_key=api_key,
                    temperature=0.2,
                ).bind_tools(tools)

                state = self.state_manager.get_state()
                context_msg = (
                    f"Current Mission Snapshot: Scenario={state.scenario_name}, Env={state.environment_name}, "
                    f"Status={state.clinical_evaluation.overall_status}, HR={state.vitals.heart_rate_bpm}, "
                    f"BP={state.vitals.bp_systolic}/{state.vitals.bp_diastolic}, Temp={state.vitals.temperature_c}C, "
                    f"Glucose={state.vitals.glucose_mg_dl}, Sleep={state.vitals.sleep_hours}h, "
                    f"Rad={state.vitals.radiation_msv_h} mSv/h, ML Anomaly={state.ml_prediction.anomaly_score}%."
                )

                messages: list[Any] = [
                    SystemMessage(content=f"{SYSTEM_PROMPT}\n{context_msg}"),
                    HumanMessage(content=message),
                ]

                ai_msg = await asyncio.wait_for(llm.ainvoke(messages), timeout=8.0)
                messages.append(ai_msg)

                if getattr(ai_msg, "tool_calls", None):
                    for tc in ai_msg.tool_calls:
                        fn = tools_by_name.get(tc["name"])
                        if fn:
                            result = fn.invoke(tc["args"])
                            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
                    final_msg = await asyncio.wait_for(llm.ainvoke(messages), timeout=8.0)
                    reply_text = str(final_msg.content)
                else:
                    # Ensure at least clinical + ML trace for cockpit transparency
                    tools_by_name["evaluate_clinical_rules_tool"].invoke({"note": "sync"})
                    tools_by_name["predict_ml_risk_tool"].invoke({"context": "sync"})
                    reply_text = str(ai_msg.content)

                return ChatResponse(
                    reply=reply_text,
                    mode="langchain_gemini",
                    tool_trace=trace_log,
                    state=self.state_manager.get_state(),
                )
            except Exception:
                trace_log.clear()

        # Deterministic Offline-First Hybrid Tool Pipeline (zero network dependency)
        reply_parts: list[str] = []
        lower = message.lower()

        import re
        nutrition_parsed = parse_nutrition_text(message)
        sleep_mood_parsed = parse_sleep_mood_text(message)

        did_domain_tool = False

        if nutrition_parsed["items"] or re.search(
            r"\b(ate|eat|drank|drink|meal|food|water|apple|apples|comi|bebi|agua|água)\b",
            lower,
        ):
            res = tools_by_name["log_nutrition_hydration_tool"].invoke({"meal_description": message})
            reply_parts.append(f"**Nutrition & Hydration Updated:** {res}")
            did_domain_tool = True

        if sleep_mood_parsed or re.search(
            r"\b(sleep|slept|tired|dizzy|mood|stress|shoulder|ombro|dormi|sono|exausto|eva)\b",
            lower,
        ):
            res = tools_by_name["log_sleep_mood_checkin_tool"].invoke({"checkin_text": message})
            reply_parts.append(f"**Sleep / Behavioral / EVA Check-In:** {res}")
            did_domain_tool = True

        if re.search(
            r"\b(solar|radiation|storm|donki|flare|proton|radiação|tempestade)\b",
            lower,
        ):
            res = tools_by_name["check_nasa_donki_weather_tool"].invoke({"window_days": 14})
            reply_parts.append(f"**NASA DONKI Space Weather Sync:** {res}")
            did_domain_tool = True

        if re.search(
            r"\b(dossier|doctor|surgeon|telemed|earth|terra|médico)\b",
            lower,
        ):
            res = tools_by_name["compile_telemedicine_dossier_tool"].invoke({"reason": "crew_request"})
            reply_parts.append(f"**Telemedicine Dossier Compiled:** {res}")
            did_domain_tool = True

        # Always run Layer 1 + Layer 2 triage so astronaut receives complete safety guidance
        tools_by_name["evaluate_clinical_rules_tool"].invoke({"note": "hybrid_triage"})
        tools_by_name["predict_ml_risk_tool"].invoke({"context": "hybrid_triage"})

        state = self.state_manager.get_state()
        ev = state.clinical_evaluation
        ml = state.ml_prediction

        if not did_domain_tool or any(w in lower for w in ["triage", "check", "status", "help", "diagnos", "pfo", "how", "why"]):
            top_drivers = ", ".join(f"{d.label} ({d.importance:.0f}%)" for d in ml.feature_importances[:3])
            reply_parts.append(
                f"**Clinical Triage ({ev.overall_status}):** {ev.primary_diagnosis}. "
                f"ML IsolationForest Anomaly Score is **{ml.anomaly_score:.1f}%** "
                f"(RandomForest predicts *{ml.predicted_syndrome_label}* at {ml.confidence_pct:.0f}% confidence; "
                f"key drivers: {top_drivers})."
            )

        if ev.decontamination_required:
            reply_parts.append(
                "**Planetary Surface Guardrail:** Complete the mandatory HEPA/electrostatic regolith decontamination checklist before any fingerstick or cuff exam."
            )

        steps = "\n".join(f"{idx}. {step}" for idx, step in enumerate(ev.stabilization_checklist[:4], start=1))
        reply_parts.append(f"**Recommended Action Plan:**\n{steps}")

        if "pfo" in lower or "eva" in lower:
            reply_parts.append(
                "**OCHMO-MTB-011 / MTB-006 EVA Protocol:** Maintain 4h suit O2 prebreathe (or Campout 10.2 psia / 26.5% O2) to prevent venous-to-arterial gas embolism shunting, and report any shoulder VAS >= 4 for portable ultrasound screening."
            )

        return ChatResponse(
            reply="\n\n".join(reply_parts),
            mode="offline_hybrid_edge",
            tool_trace=trace_log,
            state=state,
        )
