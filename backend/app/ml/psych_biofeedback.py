from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.models.schemas import (
    AdaptiveBaselineProfile,
    CentralPsychAlertRecord,
    MissionContext,
    NutritionHydrationState,
    PsychBiofeedbackEvaluation,
    PsychIndicatorWeight,
    PsychStimulusItem,
    VitalSigns,
)

PSYCH_DIAGNOSIS_LABELS: dict[str, str] = {
    "acute_anxiety_hyperarousal": "Acute Anxiety & Sympathetic Autonomic Hyper-Arousal",
    "isolation_loneliness_dysphoria": "Deep-Space Isolation, Loneliness & Affective Dysphoria (Low Motivation)",
    "circadian_sleep_exhaustion": "Circadian Desynchrony & Cumulative Sleep Exhaustion (OCHMO-MTB-009)",
    "post_eva_psychophysical_strain": "Post-EVA Psychophysical Strain & Pain-Induced Tension (OCHMO-MTB-006)",
    "cognitive_overload_monotony": "Cognitive Overload, Operational Monotony & Cabin Environmental Strain",
    "nominal_resilience_flow": "Nominal Psychophysiological Resilience & Preventive Flow Maintenance",
}


class PsychBiofeedbackEngine:
    """
    Pillar 6: Individual-Baseline-Weighted Psychophysiological Countermeasure & Biofeedback Engine.
    Evaluates each astronaut's personal indicator deviations (individual_z_score) to weight 6
    psychological/autonomic diagnoses, selects personalized stimuli from the astronaut's Personal Crew Vault
    (family videos, friends audio, Earth nature/animal soundscapes, interactive games/interests),
    models closed-loop vagal biofeedback normalization (HR, BP, HRV, Stress, Mood), and dispatches
    mandatory alerts to Central (MCC-Houston BHP & Flight Surgeon).
    """

    def __init__(self) -> None:
        self.central_alerts_history: list[CentralPsychAlertRecord] = []

    def evaluate(
        self,
        astronaut_profile: dict[str, Any],
        vitals: VitalSigns,
        nutrition: NutritionHydrationState,
        context: MissionContext,
        adaptive_baseline: AdaptiveBaselineProfile,
        one_way_latency_seconds: int,
    ) -> PsychBiofeedbackEvaluation:
        astronaut_id = adaptive_baseline.astronaut_id
        astronaut_name = adaptive_baseline.astronaut_name
        m = adaptive_baseline.metrics

        hr_z = m["heart_rate_bpm"].individual_z_score
        hrv_z = m["hrv_ms"].individual_z_score
        bp_sys_z = m["bp_systolic"].individual_z_score
        bp_dia_z = m["bp_diastolic"].individual_z_score
        rr_z = m["respiration_rpm"].individual_z_score
        sleep_z = m["sleep_hours"].individual_z_score
        rem_z = m["rem_sleep_pct"].individual_z_score
        mood_z = m["mood_score"].individual_z_score
        stress_z = m["stress_index"].individual_z_score

        is_recent_workout = context.minutes_since_last_exercise <= 45.0 and context.exercise_modality != "none"
        ex_damp = 0.30 if is_recent_workout else 1.0

        weights_log: list[PsychIndicatorWeight] = []
        scores: dict[str, float] = {k: 12.0 for k in PSYCH_DIAGNOSIS_LABELS}

        def _add_weight(
            metric_key: str,
            z_val: float,
            mult: float,
            diag: str,
            rationale: str,
        ) -> None:
            pts = round(max(0.0, abs(z_val) * mult), 1)
            if pts <= 1.0:
                return
            scores[diag] = min(99.0, scores[diag] + pts)
            bm = m.get(metric_key)
            weights_log.append(
                PsychIndicatorWeight(
                    metric=metric_key,
                    label=bm.label if bm else metric_key,
                    current_value=bm.current_value if bm else 0.0,
                    personal_baseline=bm.rolling_ewma_baseline if bm else 0.0,
                    individual_z_score=round(z_val, 2),
                    weight_multiplier=round(mult, 2),
                    points_contributed=pts,
                    target_diagnosis=diag,
                    clinical_rationale=rationale,
                )
            )

        # 1. Acute Anxiety / Sympathetic Hyper-Arousal (Resting elevated HR/BP/RR + suppressed HRV + high stress)
        if hr_z > 0.8:
            _add_weight(
                "heart_rate_bpm",
                hr_z,
                10.5 * ex_damp,
                "acute_anxiety_hyperarousal",
                f"Resting HR elevated +{hr_z:.1f}σ above {astronaut_name}'s personal baseline ({m['heart_rate_bpm'].rolling_ewma_baseline} bpm).",
            )
        if hrv_z < -0.8:
            _add_weight(
                "hrv_ms",
                hrv_z,
                11.5 * ex_damp,
                "acute_anxiety_hyperarousal",
                f"Vagal HRV RMSSD suppressed {hrv_z:.1f}σ below personal baseline ({m['hrv_ms'].rolling_ewma_baseline} ms).",
            )
        if bp_sys_z > 0.8:
            _add_weight(
                "bp_systolic",
                bp_sys_z,
                9.5 * ex_damp,
                "acute_anxiety_hyperarousal",
                f"Systolic BP elevated +{bp_sys_z:.1f}σ above personal baseline ({m['bp_systolic'].rolling_ewma_baseline} mmHg).",
            )
        if bp_dia_z > 0.8:
            _add_weight(
                "bp_diastolic",
                bp_dia_z,
                7.0 * ex_damp,
                "acute_anxiety_hyperarousal",
                f"Diastolic BP elevated +{bp_dia_z:.1f}σ above personal baseline.",
            )
        if rr_z > 0.8:
            _add_weight(
                "respiration_rpm",
                rr_z,
                7.5 * ex_damp,
                "acute_anxiety_hyperarousal",
                f"Respiratory rate accelerated +{rr_z:.1f}σ above personal baseline.",
            )
        if stress_z > 1.0:
            _add_weight(
                "stress_index",
                stress_z,
                9.0 * ex_damp,
                "acute_anxiety_hyperarousal",
                f"Autonomic stress index elevated +{stress_z:.1f}σ above personal baseline.",
            )

        # 2. Isolation, Loneliness & Affective Dysphoria (Low mood, deep-space comm delay, appetite loss, REM drop)
        if mood_z < -0.8 or vitals.mood_score <= 3:
            eff_mood_z = min(mood_z, -1.5) if vitals.mood_score <= 2 else mood_z
            _add_weight(
                "mood_score",
                eff_mood_z,
                15.5,
                "isolation_loneliness_dysphoria",
                f"Subjective mood dropped ({vitals.mood_score}/5, z={mood_z:+.1f}σ vs personal baseline).",
            )
        if one_way_latency_seconds >= 180:
            lat_z = min(3.5, one_way_latency_seconds / 240.0)
            scores["isolation_loneliness_dysphoria"] = min(
                99.0, scores["isolation_loneliness_dysphoria"] + round(lat_z * 6.5, 1)
            )
            weights_log.append(
                PsychIndicatorWeight(
                    metric="one_way_latency_seconds",
                    label="Earth Comm Delay (Isolation Factor)",
                    current_value=float(one_way_latency_seconds),
                    personal_baseline=2.0,
                    individual_z_score=round(lat_z, 2),
                    weight_multiplier=6.5,
                    points_contributed=round(lat_z * 6.5, 1),
                    target_diagnosis="isolation_loneliness_dysphoria",
                    clinical_rationale=f"Deep-space communication delay ({one_way_latency_seconds}s one-way) blocks real-time family conversation.",
                )
            )
        cal_pct = (nutrition.calories_kcal / max(nutrition.goal_calories_kcal, 1.0)) * 100.0
        if cal_pct < 75.0 and vitals.mood_score <= 3:
            cal_z = (75.0 - cal_pct) / 12.0
            scores["isolation_loneliness_dysphoria"] = min(
                99.0, scores["isolation_loneliness_dysphoria"] + round(cal_z * 6.0, 1)
            )
            weights_log.append(
                PsychIndicatorWeight(
                    metric="calories_kcal",
                    label="Nutritional Appetite Intake (%)",
                    current_value=round(cal_pct, 1),
                    personal_baseline=88.0,
                    individual_z_score=round(-cal_z, 2),
                    weight_multiplier=6.0,
                    points_contributed=round(cal_z * 6.0, 1),
                    target_diagnosis="isolation_loneliness_dysphoria",
                    clinical_rationale=f"Reduced caloric intake ({cal_pct:.0f}% of goal) coupled with low mood signals isolation-related appetite suppression.",
                )
            )

        # 3. Circadian Desynchrony & Cumulative Sleep Exhaustion (OCHMO-MTB-009)
        if sleep_z < -0.8:
            _add_weight(
                "sleep_hours",
                sleep_z,
                13.0,
                "circadian_sleep_exhaustion",
                f"Sleep duration compressed ({vitals.sleep_hours:.1f}h, z={sleep_z:+.1f}σ vs personal baseline {m['sleep_hours'].rolling_ewma_baseline}h).",
            )
        if vitals.sleep_streak_low_days >= 1:
            streak_pts = round(min(38.0, vitals.sleep_streak_low_days * 11.5), 1)
            scores["circadian_sleep_exhaustion"] = min(99.0, scores["circadian_sleep_exhaustion"] + streak_pts)
            weights_log.append(
                PsychIndicatorWeight(
                    metric="sleep_streak_low_days",
                    label="Consecutive Short Sleep Nights (<5h)",
                    current_value=float(vitals.sleep_streak_low_days),
                    personal_baseline=0.0,
                    individual_z_score=float(vitals.sleep_streak_low_days),
                    weight_multiplier=11.5,
                    points_contributed=streak_pts,
                    target_diagnosis="circadian_sleep_exhaustion",
                    clinical_rationale=f"{vitals.sleep_streak_low_days} consecutive nights <5h triggers OCHMO-MTB-009 circadian fatigue protocol.",
                )
            )
        if rem_z < -0.8:
            _add_weight(
                "rem_sleep_pct",
                rem_z,
                8.5,
                "circadian_sleep_exhaustion",
                f"REM sleep architecture reduced ({vitals.rem_sleep_pct:.1f}%, z={rem_z:+.1f}σ).",
            )

        # 4. Post-EVA Psychophysical Strain & Pain Tension (OCHMO-MTB-006)
        if vitals.shoulder_pain_score >= 2 or context.eva_status != "none" or context.hours_since_last_eva <= 8.0:
            if vitals.shoulder_pain_score >= 2:
                pain_pts = round(vitals.shoulder_pain_score * 8.5, 1)
                scores["post_eva_psychophysical_strain"] = min(99.0, scores["post_eva_psychophysical_strain"] + pain_pts)
                weights_log.append(
                    PsychIndicatorWeight(
                        metric="shoulder_pain_score",
                        label="EVA Suit Shoulder Pain (VAS 0-10)",
                        current_value=float(vitals.shoulder_pain_score),
                        personal_baseline=0.0,
                        individual_z_score=float(vitals.shoulder_pain_score),
                        weight_multiplier=8.5,
                        points_contributed=pain_pts,
                        target_diagnosis="post_eva_psychophysical_strain",
                        clinical_rationale="Somatic pain from rigid EMU HUT suit bearings elevates sympathetic tension.",
                    )
                )
            if context.eva_status != "none" or context.hours_since_last_eva <= 8.0:
                scores["post_eva_psychophysical_strain"] = min(99.0, scores["post_eva_psychophysical_strain"] + 22.0)

        # 5. Cognitive Overload & Cabin Monotony/CO2 Strain
        if stress_z > 0.8:
            _add_weight(
                "stress_index",
                stress_z,
                8.0,
                "cognitive_overload_monotony",
                "Sustained cognitive/autonomic workload index above personal baseline.",
            )
        if context.cabin_co2_mmhg >= 3.2:
            co2_z = (context.cabin_co2_mmhg - 2.4) / 0.5
            co2_pts = round(co2_z * 11.0, 1)
            scores["cognitive_overload_monotony"] = min(99.0, scores["cognitive_overload_monotony"] + co2_pts)
            weights_log.append(
                PsychIndicatorWeight(
                    metric="cabin_co2_mmhg",
                    label="Cabin ppCO2 Cognitive Load Factor",
                    current_value=context.cabin_co2_mmhg,
                    personal_baseline=2.4,
                    individual_z_score=round(co2_z, 2),
                    weight_multiplier=11.0,
                    points_contributed=co2_pts,
                    target_diagnosis="cognitive_overload_monotony",
                    clinical_rationale=f"Elevated cabin CO2 ({context.cabin_co2_mmhg:.1f} mmHg) impairs executive focus and increases irritability.",
                )
            )

        # Round all scores
        for k in scores:
            scores[k] = round(scores[k], 1)

        # Pick highest non-nominal diagnosis if >= 48.0, else nominal_resilience_flow
        non_nom = {k: v for k, v in scores.items() if k != "nominal_resilience_flow"}
        best_diag = max(non_nom, key=non_nom.get)
        best_score = non_nom[best_diag]

        if best_score < 48.0:
            primary_code = "nominal_resilience_flow"
            scores["nominal_resilience_flow"] = round(100.0 - best_score * 0.6, 1)
            primary_score = scores["nominal_resilience_flow"]
        else:
            primary_code = best_diag
            primary_score = best_score

        # Operational safety & schedule window determination
        operational_block = context.eva_status == "active_eva" or vitals.radiation_msv_h >= 0.50
        if operational_block:
            schedule_win = "EVA_ACTIVE_VISUAL_BLOCK_SAFE_AUDIO"
        elif primary_code == "circadian_sleep_exhaustion":
            schedule_win = "PRE_SLEEP_CIRCADIAN_WIND_DOWN"
        elif context.eva_status == "post_eva_recovery" or context.hours_since_last_eva <= 6.0:
            schedule_win = "POST_EVA_RECOVERY_WINDOW"
        elif best_score >= 70.0:
            schedule_win = "IMMEDIATE_RESTING_INTERVENTION"
        else:
            schedule_win = "MID_SHIFT_DECOMPRESSION"

        delivery_mode = (
            "SUIT_AUDIO_ONLY_SAFE_MODE"
            if operational_block
            else ("PRIVATE_CREW_QUARTERS" if primary_code in ("isolation_loneliness_dysphoria", "circadian_sleep_exhaustion") else "CABIN_DISPLAY_AND_AUDIO")
        )

        # Select tailored stimuli from the astronaut's Personal Crew Vault
        vault = astronaut_profile.get("personal_psych_vault", {})
        fam_list = vault.get("family_videos", [])
        nat_list = vault.get("nature_animal_sounds", [])
        game_list = vault.get("games_and_interests", [])

        selected_stimuli: list[PsychStimulusItem] = []

        def _make_item(raw: dict[str, Any], cat_fallback: str) -> PsychStimulusItem:
            return PsychStimulusItem(
                stimulus_id=str(raw.get("id", f"STIM-{uuid4().hex[:4]}")),
                title=str(raw.get("title", "Personalized Crew Stimulus")),
                category=raw.get("category", cat_fallback),
                duration_min=int(raw.get("duration_min", 10)),
                description=str(raw.get("description", "")),
                target_effect=str(raw.get("target_effect", "")),
                delivery_mode=delivery_mode,
            )

        if primary_code == "acute_anxiety_hyperarousal":
            if game_list and not operational_block:
                selected_stimuli.append(_make_item(game_list[0], "interactive_game_interest"))
            if nat_list:
                selected_stimuli.append(_make_item(nat_list[0], "nature_animals_audio"))
        elif primary_code == "isolation_loneliness_dysphoria":
            for raw_fam in fam_list[:2]:
                if not (operational_block and raw_fam.get("category") == "family_video"):
                    selected_stimuli.append(_make_item(raw_fam, "family_video"))
            if game_list and not operational_block:
                selected_stimuli.append(_make_item(game_list[0], "interactive_game_interest"))
        elif primary_code == "circadian_sleep_exhaustion":
            if nat_list:
                selected_stimuli.append(_make_item(nat_list[0], "nature_animals_audio"))
            if len(fam_list) > 1:
                selected_stimuli.append(_make_item(fam_list[1], "friends_audio"))
        elif primary_code == "post_eva_psychophysical_strain":
            if nat_list:
                selected_stimuli.append(_make_item(nat_list[0], "nature_animals_audio"))
            if fam_list and not operational_block:
                selected_stimuli.append(_make_item(fam_list[0], "family_video"))
        else:
            # cognitive_overload_monotony or nominal_resilience_flow
            if game_list and not operational_block:
                selected_stimuli.append(_make_item(game_list[0], "interactive_game_interest"))
            if nat_list:
                selected_stimuli.append(_make_item(nat_list[0], "nature_animals_audio"))

        weights_log.sort(key=lambda w: w.points_contributed, reverse=True)
        auto_trigger = primary_code != "nominal_resilience_flow" and best_score >= 52.0

        last_alert = next(
            (a for a in reversed(self.central_alerts_history) if a.astronaut_id == astronaut_id),
            None,
        )

        mech_summary = (
            f"[{astronaut_name}] Weighted personal baseline analysis identifies '{PSYCH_DIAGNOSIS_LABELS[primary_code]}' "
            f"(Score: {primary_score:.1f}/100 | Window: {schedule_win}). "
            f"Selected {len(selected_stimuli)} personalized stimulus item(s) from {astronaut_name}'s Crew Vault."
        )

        return PsychBiofeedbackEvaluation(
            astronaut_id=astronaut_id,
            astronaut_name=astronaut_name,
            schedule_window=schedule_win,
            auto_trigger_recommended=auto_trigger,
            operational_block_active=operational_block,
            primary_diagnosis_code=primary_code,
            primary_diagnosis_label=PSYCH_DIAGNOSIS_LABELS[primary_code],
            primary_score_0_100=primary_score,
            diagnosis_scores=scores,
            indicator_weights=weights_log[:6],
            recommended_stimuli=selected_stimuli,
            biofeedback_mechanism_summary=mech_summary,
            last_triggered_alert=last_alert,
        )

    def trigger_and_dispatch_to_central(
        self,
        evaluation: PsychBiofeedbackEvaluation,
        vitals: VitalSigns,
        adaptive_baseline: AdaptiveBaselineProfile,
        mission_day: int,
        followup_case_id: str | None = None,
        earth_sync_package_id: str | None = None,
    ) -> CentralPsychAlertRecord:
        """
        Executes the psychological biofeedback countermeasure:
          1. Captures pre-stimulus vitals
          2. Modulates HR, BP, HRV, Stress, and Mood toward the astronaut's personal EWMA baseline
          3. Creates and stores a CentralPsychAlertRecord transmitted to MCC-Houston BHP & Flight Surgeon
        """
        pre_vitals = {
            "heart_rate_bpm": vitals.heart_rate_bpm,
            "hrv_ms": vitals.hrv_ms,
            "bp_systolic": vitals.bp_systolic,
            "bp_diastolic": vitals.bp_diastolic,
            "respiration_rpm": vitals.respiration_rpm,
            "stress_index": vitals.stress_index,
            "mood_score": float(vitals.mood_score),
        }

        m = adaptive_baseline.metrics
        pers_hr = m["heart_rate_bpm"].rolling_ewma_baseline
        pers_hrv = m["hrv_ms"].rolling_ewma_baseline
        pers_bp_sys = m["bp_systolic"].rolling_ewma_baseline
        pers_bp_dia = m["bp_diastolic"].rolling_ewma_baseline
        pers_rr = m["respiration_rpm"].rolling_ewma_baseline

        # Vagal & affective biofeedback shift toward personal baseline
        if vitals.heart_rate_bpm > pers_hr:
            vitals.heart_rate_bpm = round(vitals.heart_rate_bpm - 0.45 * (vitals.heart_rate_bpm - pers_hr), 1)
        if vitals.bp_systolic > pers_bp_sys:
            vitals.bp_systolic = round(vitals.bp_systolic - 0.42 * (vitals.bp_systolic - pers_bp_sys), 1)
        if vitals.bp_diastolic > pers_bp_dia:
            vitals.bp_diastolic = round(vitals.bp_diastolic - 0.42 * (vitals.bp_diastolic - pers_bp_dia), 1)
        if vitals.hrv_ms < pers_hrv:
            vitals.hrv_ms = round(vitals.hrv_ms + 0.45 * (pers_hrv - vitals.hrv_ms), 1)
        if vitals.respiration_rpm > pers_rr:
            vitals.respiration_rpm = round(vitals.respiration_rpm - 0.45 * (vitals.respiration_rpm - pers_rr), 1)

        vitals.stress_index = round(max(16.0, vitals.stress_index - 22.0), 1)
        if vitals.mood_score < 5:
            vitals.mood_score = min(5, vitals.mood_score + 1)

        post_vitals = {
            "heart_rate_bpm": vitals.heart_rate_bpm,
            "hrv_ms": vitals.hrv_ms,
            "bp_systolic": vitals.bp_systolic,
            "bp_diastolic": vitals.bp_diastolic,
            "respiration_rpm": vitals.respiration_rpm,
            "stress_index": vitals.stress_index,
            "mood_score": float(vitals.mood_score),
        }

        alert_rec = CentralPsychAlertRecord(
            central_alert_id=f"MCC-BHP-{evaluation.astronaut_id[:4].upper()}-D{mission_day}-{uuid4().hex[:5].upper()}",
            dispatched_at=datetime.now(timezone.utc).isoformat(),
            astronaut_id=evaluation.astronaut_id,
            astronaut_name=evaluation.astronaut_name,
            mission_day=mission_day,
            primary_psych_diagnosis=evaluation.primary_diagnosis_code,
            primary_psych_label=evaluation.primary_diagnosis_label,
            weighted_score_0_100=evaluation.primary_score_0_100,
            schedule_window=evaluation.schedule_window,
            triggering_indicator_weights=evaluation.indicator_weights,
            dispatched_stimuli=evaluation.recommended_stimuli,
            pre_stimulus_vitals=pre_vitals,
            post_stimulus_vitals=post_vitals,
            followup_case_id=followup_case_id,
            earth_sync_package_id=earth_sync_package_id,
            reassessment_scheduled_in_minutes=15,
        )
        self.central_alerts_history.append(alert_rec)
        evaluation.last_triggered_alert = alert_rec
        return alert_rec
