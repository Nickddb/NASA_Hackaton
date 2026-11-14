from __future__ import annotations

import re
from typing import Any

from langchain_core.tools import tool

from app.engine.clinical_rules import evaluate_clinical_rules
from app.models.schemas import ToolTraceItem
from app.state_manager import MissionStateManager, ensure_space_weather_sync

# Spaceflight-calibrated food database (per 1 unit/serving)
FOOD_DB: list[tuple[list[str], str, float, float, float, float, float, float, float]] = [
    # (keywords, label, kcal, water_ml, protein_g, carbs_g, fiber_g, sodium_mg, iron_mg)
    (["apple", "apples", "maça", "maçã", "macas", "maçãs"], "Fresh/Freeze-Dried Apple", 95, 80, 0.5, 25, 4.4, 2, 0.2),
    (["banana", "bananas"], "Banana Pouch", 105, 65, 1.3, 27, 3.1, 1, 0.3),
    (["bar", "protein bar", "barra"], "Space Nutrition Protein Bar", 240, 10, 20, 24, 4.0, 210, 2.2),
    (["glucose", "gel", "carb", "candy", "dextrose"], "Rapid Glucose Gel Pouch", 90, 25, 0, 22, 0, 45, 0.0),
    (["salad", "veggie", "spinach", "lettuce", "salada"], "Hydroponic ISS Salad", 85, 120, 4.0, 12, 4.5, 95, 1.4),
    (["chicken", "beef", "meat", "teriyaki", "meal", "dinner", "lunch", "frango", "carne", "refeição"], "Thermostabilized Entree Pouch", 460, 110, 34, 42, 4.0, 680, 2.8),
    (["soup", "broth", "sopa"], "Rehydrated Electrolyte Broth", 160, 260, 8.0, 18, 2.0, 740, 0.9),
    (["coffee", "tea", "café", "cafe", "chá"], "Space Beverage Pouch (No-Sugar)", 15, 240, 0, 2, 0, 10, 0.1),
    (["saline", "electrolyte", "isotonic", "soro"], "Isotonic Electrolyte Hydration", 45, 500, 0, 11, 0, 460, 0.0),
    (["oatmeal", "breakfast", "cereal", "aveia"], "Rehydrated Space Oatmeal", 290, 180, 10, 50, 6.0, 180, 1.8),
]


def parse_nutrition_text(text: str) -> dict[str, Any]:
    lower = text.lower()
    total = {
        "items": [],
        "calories_kcal": 0.0,
        "water_ml": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fiber_g": 0.0,
        "sodium_mg": 0.0,
        "iron_mg": 0.0,
    }

    # Parse explicit water volumes (e.g., "500ml", "500 ml", "1.5 l", "1 liter")
    water_ml_matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(ml|mL|l|liter|liters|litro|litros)\b", lower)
    for num_str, unit in water_ml_matches:
        val = float(num_str.replace(",", "."))
        ml = val * 1000.0 if unit.startswith("l") else val
        total["water_ml"] += ml
        total["items"].append(f"{ml:.0f}ml Potable Water (PWD)")

    if not water_ml_matches and any(w in lower for w in ["water", "agua", "água", "hydrate", "drank", "bebi"]):
        total["water_ml"] += 300.0
        total["items"].append("300ml Potable Water (PWD)")

    # Parse food keywords with optional leading integer multiplier ("2 apples")
    for keywords, label, kcal, w_ml, prot, carbs, fiber, na, fe in FOOD_DB:
        matched_kw = next((kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", lower)), None)
        if matched_kw:
            qty_match = re.search(rf"(\d+)\s+{re.escape(matched_kw)}\b", lower)
            qty = min(int(qty_match.group(1)), 10) if qty_match else 1
            total["calories_kcal"] += kcal * qty
            total["water_ml"] += w_ml * qty
            total["protein_g"] += prot * qty
            total["carbs_g"] += carbs * qty
            total["fiber_g"] += fiber * qty
            total["sodium_mg"] += na * qty
            total["iron_mg"] += fe * qty
            total["items"].append(f"{qty}x {label}")

    # Explicit kcal mention fallback
    kcal_match = re.search(r"(\d+)\s*(kcal|cal|calories)\b", lower)
    if kcal_match and total["calories_kcal"] == 0:
        kcal_val = float(kcal_match.group(1))
        total["calories_kcal"] += kcal_val
        total["carbs_g"] += round(kcal_val * 0.12, 1)
        total["protein_g"] += round(kcal_val * 0.04, 1)
        total["items"].append(f"Custom Meal ({kcal_val:.0f} kcal)")

    return total


def parse_sleep_mood_text(text: str) -> dict[str, Any]:
    lower = text.lower()
    updates: dict[str, Any] = {}

    sleep_match = re.search(r"(?:slept|sleep|dormi|sono)[^\d]{0,12}(\d+(?:[.,]\d+)?)\s*(?:h|hr|hrs|hours|horas)?", lower)
    if not sleep_match:
        sleep_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:h|hr|hrs|hours|horas)\b", lower)
    if sleep_match:
        updates["sleep_hours"] = float(sleep_match.group(1).replace(",", "."))

    mood_match = re.search(r"(?:mood|humor)[^\d]{0,8}([1-5])", lower)
    if mood_match:
        updates["mood_score"] = int(mood_match.group(1))
    elif any(w in lower for w in ["exhausted", "dizzy", "anxious", "stressed", "terrible", "depressed", "cansado", "exausto", "tonto"]):
        updates["mood_score"] = 2
        updates["stress_index"] = 78.0
    elif any(w in lower for w in ["great", "good", "energized", "calm", "nominal", "bem", "ótimo"]):
        updates["mood_score"] = 5
        updates["stress_index"] = 22.0

    pain_match = re.search(r"(?:pain|dor)[^\d]{0,8}(\d{1,2})\s*(?:/\s*10)?", lower)
    if pain_match:
        updates["shoulder_pain_score"] = min(10, int(pain_match.group(1)))
    elif any(w in lower for w in ["shoulder", "ombro", "rotator", "hut", "arm pain"]):
        updates["shoulder_pain_score"] = 6

    return updates


def build_agent_tools(state_manager: MissionStateManager, trace_log: list[ToolTraceItem]) -> list[Any]:
    """Create the 6 LangChain @tool functions bound to the live MissionStateManager."""

    @tool
    def evaluate_clinical_rules_tool(note: str = "standard") -> str:
        """Evaluate all 8 astronaut indicators and 6 anatomical systems against NASA-STD-3001 and OCHMO clinical rules."""
        state = state_manager.get_state()
        ev = state.clinical_evaluation
        trace_log.append(
            ToolTraceItem(
                tool_name="evaluate_clinical_rules",
                status="OK" if ev.overall_status == "NOMINAL" else ev.overall_status,
                summary=f"{ev.overall_status}: {ev.primary_diagnosis}",
                rule_or_score=", ".join(ev.matched_rules[:2]),
            )
        )
        return (
            f"Overall: {ev.overall_status} | Diagnosis: {ev.primary_diagnosis} | "
            f"Rules: {', '.join(ev.matched_rules)} | "
            f"Checklist: {'; '.join(ev.stabilization_checklist)}"
        )

    @tool
    def predict_ml_risk_tool(context: str = "full_vector") -> str:
        """Run Layer 2 scikit-learn IsolationForest anomaly scoring and RandomForest syndrome classification."""
        state = state_manager.get_state()
        ml = state.ml_prediction
        drivers = ", ".join(f"{f.label} ({f.importance:.0f}%)" for f in ml.feature_importances[:3])
        trace_log.append(
            ToolTraceItem(
                tool_name="predict_ml_risk",
                status="CRITICAL" if ml.anomaly_score >= 70 else ("WARNING" if ml.anomaly_score >= 45 else "OK"),
                summary=f"Anomaly {ml.anomaly_score:.1f}% -> {ml.predicted_syndrome_label} ({ml.confidence_pct:.0f}%)",
                rule_or_score=f"IsolationForest {ml.anomaly_score:.1f}%",
            )
        )
        return (
            f"Anomaly Score: {ml.anomaly_score:.1f}% | Predicted: {ml.predicted_syndrome_label} "
            f"({ml.confidence_pct:.1f}% confidence) | Top Feature Drivers: {drivers}"
        )

    @tool
    def check_nasa_donki_weather_tool(window_days: int = 14) -> str:
        """Check NASA DONKI FLR (Solar Flares) and SEP (Solar Energetic Particle) radiation alerts."""
        sw = ensure_space_weather_sync(state_manager)
        trace_log.append(
            ToolTraceItem(
                tool_name="check_nasa_donki_weather",
                status="OK" if sw.alert_level == "NOMINAL" else sw.alert_level,
                summary=f"{sw.active_flare_count} FLR, {sw.active_sep_count} SEP ({sw.source})",
                rule_or_score=f"ALARA {sw.alert_level}",
            )
        )
        return (
            f"Source: {sw.source} | Alert: {sw.alert_level} | FLR: {sw.active_flare_count} | "
            f"SEP: {sw.active_sep_count} | Guidance: {sw.alara_instruction}"
        )

    @tool
    def log_nutrition_hydration_tool(meal_description: str) -> str:
        """Parse natural language food/hydration logs, update daily calorie/water/macro goals, and check NASA Na/Fe limits."""
        parsed = parse_nutrition_text(meal_description)
        if not parsed["items"]:
            parsed["items"] = ["Space Snack (150 kcal)"]
            parsed["calories_kcal"] = 150.0
            parsed["carbs_g"] = 28.0
            parsed["water_ml"] = 200.0

        state = state_manager.add_nutrition_entry(
            item_label=", ".join(parsed["items"]),
            calories=parsed["calories_kcal"],
            water_ml=parsed["water_ml"],
            protein_g=parsed["protein_g"],
            carbs_g=parsed["carbs_g"],
            fiber_g=parsed["fiber_g"],
            sodium_mg=parsed["sodium_mg"],
            iron_mg=parsed["iron_mg"],
        )
        n = state.nutrition
        trace_log.append(
            ToolTraceItem(
                tool_name="log_nutrition_hydration",
                status="OK" if n.sodium_mg <= n.max_sodium_mg and n.iron_mg <= n.max_iron_mg else "WARNING",
                summary=f"+{parsed['calories_kcal']:.0f} kcal, +{parsed['water_ml']:.0f} ml H2O logged",
                rule_or_score=f"Na {n.sodium_mg:.0f}/{n.max_sodium_mg:.0f}mg | Fe {n.iron_mg:.1f}/{n.max_iron_mg:.0f}mg",
            )
        )
        return (
            f"Logged: {', '.join(parsed['items'])}. Daily totals: {n.calories_kcal:.0f}/{n.goal_calories_kcal:.0f} kcal, "
            f"{n.water_ml:.0f}/{n.goal_water_ml:.0f} ml H2O, Sodium {n.sodium_mg:.0f}/{n.max_sodium_mg:.0f} mg, "
            f"Iron {n.iron_mg:.1f}/{n.max_iron_mg:.1f} mg. Glucose now {state.vitals.glucose_mg_dl:.0f} mg/dL."
        )

    @tool
    def log_sleep_mood_checkin_tool(checkin_text: str) -> str:
        """Update sleep hours, mood score, stress, or EVA shoulder pain and return OCHMO-MTB-009 / OCHMO-MTB-006 clinical guidance."""
        updates = parse_sleep_mood_text(checkin_text)
        state = state_manager.update_sleep_mood(
            sleep_hours=updates.get("sleep_hours"),
            mood_score=updates.get("mood_score"),
            shoulder_pain_score=updates.get("shoulder_pain_score"),
            stress_index=updates.get("stress_index"),
        )
        v = state.vitals
        ev = state.clinical_evaluation
        trace_log.append(
            ToolTraceItem(
                tool_name="log_sleep_mood_checkin",
                status="OK" if ev.systems["nervous_sleep"].status == "NOMINAL" and ev.systems["musculoskeletal"].status == "NOMINAL" else ev.overall_status,
                summary=f"Sleep {v.sleep_hours:.1f}h | Mood {v.mood_score}/5 | Shoulder {v.shoulder_pain_score}/10",
                rule_or_score="OCHMO-MTB-009 / MTB-006",
            )
        )
        return (
            f"Updated check-in: Sleep {v.sleep_hours:.1f}h (REM {v.rem_sleep_pct:.0f}%), Mood {v.mood_score}/5, "
            f"Stress {v.stress_index:.0f}%, Shoulder VAS {v.shoulder_pain_score}/10. "
            f"Nervous/Sleep action: {ev.systems['nervous_sleep'].recommended_action} | "
            f"Musculoskeletal action: {ev.systems['musculoskeletal'].recommended_action}"
        )

    @tool
    def compile_telemedicine_dossier_tool(reason: str = "flight_surgeon_review") -> str:
        """Compile a structured OCHMO-TB-044 MORD telemedicine dossier for Earth Flight Surgeons."""
        dossier = state_manager.compile_dossier()
        trace_log.append(
            ToolTraceItem(
                tool_name="compile_telemedicine_dossier",
                status="OK" if dossier.urgency == "NOMINAL" else dossier.urgency,
                summary=f"Dossier {dossier.dossier_id} ready ({dossier.one_way_latency_seconds}s delay)",
                rule_or_score="OCHMO-TB-044 MORD",
            )
        )
        return (
            f"Compiled Telemedicine Dossier {dossier.dossier_id} for {', '.join(dossier.recipient_roles)}. "
            f"Summary: {dossier.executive_summary}"
        )

    return [
        evaluate_clinical_rules_tool,
        predict_ml_risk_tool,
        check_nasa_donki_weather_tool,
        log_nutrition_hydration_tool,
        log_sleep_mood_checkin_tool,
        compile_telemedicine_dossier_tool,
    ]
