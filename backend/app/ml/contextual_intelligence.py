from __future__ import annotations

import math
from app.models.schemas import (
    AdaptiveBaselineProfile,
    ContextualAssociation,
    ContextualIntelligenceReport,
    MissionContext,
    NutritionHydrationState,
    VitalSigns,
)


class ContextualIntelligenceEngine:
    """
    Pillar 2: Contextual Mission Intelligence Engine.
    Correlates physiological measurements with sleep, countermeasure exercise (ARED/T2/CEVIS),
    EVA workload, gravitational phase transitions, and spacecraft cabin environment (CO2, O2, temp, pressure)
    without assuming automatic causality.
    """

    def evaluate(
        self,
        vitals: VitalSigns,
        nutrition: NutritionHydrationState,
        context: MissionContext,
        adaptive_baseline: AdaptiveBaselineProfile,
    ) -> ContextualIntelligenceReport:
        associations: list[ContextualAssociation] = []
        confounders: list[str] = []
        attenuation_pct = 0.0
        context_explains = False

        hr_z = adaptive_baseline.metrics["heart_rate_bpm"].individual_z_score
        temp_z = adaptive_baseline.metrics["temperature_c"].individual_z_score
        hrv_z = adaptive_baseline.metrics["hrv_ms"].individual_z_score

        # 1. Countermeasure Exercise Kinetics (ARED / T2 / CEVIS)
        if context.minutes_since_last_exercise <= 60.0 and context.exercise_modality != "none":
            decay_factor = math.exp(-context.minutes_since_last_exercise / 28.0)
            expected_hr_bump = 38.0 * decay_factor
            expected_temp_bump = 0.85 * decay_factor

            if vitals.heart_rate_bpm >= 90 or vitals.temperature_c >= 37.3:
                strength = round(min(0.95, 0.55 + 0.40 * decay_factor), 2)
                associations.append(
                    ContextualAssociation(
                        factor_id="CTX-EXERCISE-RECOVERY",
                        factor_name=f"Recent {context.exercise_modality} Countermeasure Workout ({context.minutes_since_last_exercise:.0f} min ago)",
                        observed_context_value=(
                            f"{context.exercise_minutes_24h:.0f} min/24h | {context.minutes_since_last_exercise:.0f} min post-workout"
                        ),
                        correlated_metrics=["heart_rate_bpm", "hrv_ms", "temperature_c", "bp_systolic", "respiration_rpm"],
                        association_strength=strength,
                        relationship_type="EXPECTED_PHYSIOLOGICAL_RESPONSE",
                        rationale=(
                            f"Post-exercise sympathetic recovery kinetics predict +{expected_hr_bump:.0f} bpm HR and "
                            f"+{expected_temp_bump:.2f} C thermal dissipation at T+{context.minutes_since_last_exercise:.0f} min. "
                            "Absence of hypotension (BP >= 100/65 mmHg) supports physiological exercise recovery as a plausible confounder, not automatic sepsis."
                        ),
                        scientific_source="NASA OSDR OSD-571 & ISS ARED/T2 Countermeasure Physiology Protocol",
                    )
                )
                if vitals.bp_systolic >= 100 and vitals.temperature_c < 38.1:
                    confounders.append(
                        f"Post-{context.exercise_modality} sympathetic and thermal recovery ({context.minutes_since_last_exercise:.0f} min post-exercise)"
                    )
                    attenuation_pct = max(attenuation_pct, 58.0)
                    context_explains = True

        # 2. Spacecraft Cabin Environment (CO2 Stagnation Pocket / Thermal / Pressure)
        if context.cabin_co2_mmhg >= 3.5:
            co2_sev = min(0.96, 0.50 + (context.cabin_co2_mmhg - 3.0) * 0.22)
            corr_metrics = ["respiration_rpm", "spo2_pct", "bp_systolic", "heart_rate_bpm", "sleep_hours", "mood_score"]
            associations.append(
                ContextualAssociation(
                    factor_id="CTX-CABIN-CO2-POCKET",
                    factor_name="Elevated Cabin Partial Pressure CO2 (ppCO2)",
                    observed_context_value=f"{context.cabin_co2_mmhg:.1f} mmHg (NASA chronic target < 2.0–3.0 mmHg)",
                    correlated_metrics=corr_metrics,
                    association_strength=round(co2_sev, 2),
                    relationship_type="ENVIRONMENTAL_EXPOSURE_CORRELATION",
                    rationale=(
                        f"In 0g, absence of buoyant convection creates localized ppCO2 pockets ({context.cabin_co2_mmhg:.1f} mmHg). "
                        "Chemoreceptor stimulation correlates with tachypnea, cerebral vasodilation (elevated IOP/headache), "
                        "mild sympathetic BP rise, and sleep fragmentation without implying primary infectious or cardiopulmonary disease."
                    ),
                    scientific_source="NASA-STD-3001 Vol. 2 Sec 6.2 (Cabin Air ppCO2 Limits) & OCHMO-TB-043",
                )
            )
            confounders.append(
                f"Localized cabin CO2 pocket ({context.cabin_co2_mmhg:.1f} mmHg) requiring ECLSS air-circulation verification"
            )
            if vitals.temperature_c < 37.8 and vitals.bp_systolic >= 95:
                attenuation_pct = max(attenuation_pct, 25.0)

        # 3. Extravehicular Activity (EVA) & Decompression / Caloric Context
        if context.eva_status != "none" or context.hours_since_last_eva <= 8.0:
            cal_pct = (nutrition.calories_kcal / max(nutrition.goal_calories_kcal, 1.0)) * 100.0
            water_pct = (nutrition.water_ml / max(nutrition.goal_water_ml, 1.0)) * 100.0

            if context.eva_status == "post_eva_recovery" or context.hours_since_last_eva <= 6.0:
                associations.append(
                    ContextualAssociation(
                        factor_id="CTX-POST-EVA-FLUID-SHIFT",
                        factor_name="Post-EVA Suit Doffing & Plasma Volume Depletion Context",
                        observed_context_value=(
                            f"Status: {context.eva_status} | {context.hours_since_last_eva:.1f}h post-EVA | "
                            f"Hydration: {water_pct:.0f}% | Cabin Pressure: {context.cabin_pressure_psia:.1f} psia"
                        ),
                        correlated_metrics=["bp_systolic", "bp_diastolic", "heart_rate_bpm", "hrv_ms", "pfo_decompression_risk"],
                        association_strength=0.88,
                        relationship_type="OPERATIONAL_WORKLOAD_CORRELATION",
                        rationale=(
                            "Suit thermal sweat losses combined with partial-gravity or post-suit vascular unloading correlate with "
                            "transient orthostatic hypotension and baroreceptor-mediated tachycardia. Must also screen for venous gas emboli (PFO/DCS)."
                        ),
                        scientific_source="NASA OCHMO-MTB-011 (PFO & EVA Decompression) & NASA-STD-3001",
                    )
                )
                confounders.append("Post-EVA hypovolemia / suit thermal dehydration and baroreceptor unloading")

            if context.eva_status == "active_eva" and (vitals.glucose_mg_dl <= 72 or cal_pct < 55.0):
                associations.append(
                    ContextualAssociation(
                        factor_id="CTX-ACTIVE-EVA-METABOLIC-DRAIN",
                        factor_name="High-Workload EVA Caloric Deficit & Suit Biomechanical Load",
                        observed_context_value=(
                            f"Active EVA | Intake: {nutrition.calories_kcal:.0f}/{nutrition.goal_calories_kcal:.0f} kcal ({cal_pct:.0f}%) | "
                            f"Shoulder VAS: {vitals.shoulder_pain_score}/10"
                        ),
                        correlated_metrics=["glucose_mg_dl", "heart_rate_bpm", "shoulder_pain_score", "stress_index"],
                        association_strength=0.91,
                        relationship_type="OPERATIONAL_WORKLOAD_CORRELATION",
                        rationale=(
                            "Pressurized EMU suit operations consume 300–450 kcal/h while rigid Hard Upper Torso (HUT) scye bearings "
                            "compress the rotator cuff. Correlates with glycemic depletion and localized shoulder pain."
                        ),
                        scientific_source="NASA OCHMO-MTB-006 (EVA Shoulder Injury) & NASA Space Food Portfolio",
                    )
                )

        # 4. Sleep Debt & Circadian Desynchrony Context
        if vitals.sleep_hours < 6.0 or vitals.sleep_streak_low_days >= 2 or context.circadian_shift_hours >= 2.0:
            associations.append(
                ContextualAssociation(
                    factor_id="CTX-CIRCADIAN-SLEEP-DEBT",
                    factor_name="Cumulative Sleep Restriction & Circadian Phase Misalignment",
                    observed_context_value=(
                        f"Sleep: {vitals.sleep_hours:.1f}h (Streak <5h: {vitals.sleep_streak_low_days}d, REM: {vitals.rem_sleep_pct:.0f}%) | "
                        f"Circadian Shift: {context.circadian_shift_hours:.1f}h"
                    ),
                    correlated_metrics=["hrv_ms", "stress_index", "mood_score", "bp_systolic", "heart_rate_bpm"],
                    association_strength=0.89 if vitals.sleep_streak_low_days >= 3 else 0.72,
                    relationship_type="OPERATIONAL_WORKLOAD_CORRELATION",
                    rationale=(
                        "Chronic sleep curtailment and slam-shift schedule misalignment suppress vagal tone (HRV RMSSD drop) "
                        "and elevate sympathetic vascular tone without implying structural cardiac disease."
                    ),
                    scientific_source="NASA OCHMO-MTB-009 (Circadian Desynchrony & Fatigue Management)",
                )
            )
            confounders.append(
                f"Circadian misalignment ({context.circadian_shift_hours:.1f}h shift) & sleep restriction ({vitals.sleep_hours:.1f}h)"
            )

        # 5. Gravitational Phase Adaptation Context (0g Cephalic Fluid Shift & Bone Unloading)
        if context.gravitational_g < 0.5 and (vitals.intraocular_pressure_mmhg >= 15.0 or vitals.urinary_calcium_mg_d >= 180.0):
            associations.append(
                ContextualAssociation(
                    factor_id="CTX-MICROGRAVITY-FLUID-BONE",
                    factor_name=f"Gravitational Unloading ({context.mission_phase}, {context.gravitational_g:.2f}g)",
                    observed_context_value=(
                        f"IOP: {vitals.intraocular_pressure_mmhg:.1f} mmHg | Urinary Ca: {vitals.urinary_calcium_mg_d:.0f} mg/d"
                    ),
                    correlated_metrics=["intraocular_pressure_mmhg", "urinary_calcium_mg_d", "bp_systolic"],
                    association_strength=0.76,
                    relationship_type="GRAVITATIONAL_PHASE_TRANSITION",
                    rationale=(
                        "Cephalic venous congestion in microgravity elevates baseline IOP (SANS risk pathway), while skeletal "
                        "unloading increases renal calcium excretion (~30–45 mg/d expected shift in OSD-570)."
                    ),
                    scientific_source="NASA OCHMO-TB-043 (Longitudinal Health Surveillance / SANS) & OSDR OSD-570",
                )
            )

        # 6. Check if significant physiological deviation is UNEXPLAINED by benign context
        if (
            (abs(hr_z) >= 2.5 or abs(temp_z) >= 2.5 or abs(hrv_z) >= 2.5)
            and context.minutes_since_last_exercise > 90.0
            and context.cabin_co2_mmhg < 3.5
            and not context_explains
        ):
            associations.append(
                ContextualAssociation(
                    factor_id="CTX-UNEXPLAINED-AT-REST",
                    factor_name="Resting Physiological Deviation Unexplained by Exercise or Cabin Environment",
                    observed_context_value=(
                        f"Rested ({context.minutes_since_last_exercise:.0f}m post-exercise) | "
                        f"Nominal ppCO2 ({context.cabin_co2_mmhg:.1f} mmHg) | "
                        f"Personal z-scores: HR {hr_z:+.1f}σ, Temp {temp_z:+.1f}σ, HRV {hrv_z:+.1f}σ"
                    ),
                    correlated_metrics=["heart_rate_bpm", "temperature_c", "hrv_ms", "bp_systolic"],
                    association_strength=0.92,
                    relationship_type="UNEXPLAINED_BY_CONTEXT",
                    rationale=(
                        "Marked deviation from the astronaut's personal baseline occurred at rest with nominal cabin air quality, "
                        "ruling out acute exercise recovery or hypercapnia as benign confounders."
                    ),
                    scientific_source="NASA OCHMO-TB-044 (Medical Operations Requirements Document)",
                )
            )

        if context_explains:
            summary = (
                f"Contextual Intelligence identifies a strong non-pathological confounder ({confounders[0]}) "
                f"that accounts for ~{attenuation_pct:.0f}% of the acute physiological deviation. "
                "Confirmatory resting re-measurement is recommended before escalating."
            )
        elif confounders:
            summary = (
                f"Contextual factors active ({'; '.join(confounders)}). Measurements are evaluated jointly with "
                "environmental and operational covariates without assuming automatic causality."
            )
        else:
            summary = (
                "No acute exercise, EVA, or cabin environmental confounders active; physiological readings reflect "
                f"resting state in {context.mission_phase} ({context.gravitational_g:.2f}g)."
            )

        return ContextualIntelligenceReport(
            mission_context=context,
            associations=associations,
            plausible_non_pathological_confounders=confounders,
            context_explains_deviation=context_explains,
            context_anomaly_attenuation_pct=round(attenuation_pct, 1),
            primary_contextual_summary=summary,
        )
