"""
Cross-diagnosis decision tree: physical (internal) vs. space weather (external, NASA DONKI) vs. psychological.

  Layer 1  radiation-compatible signs (dosimeter rise, nausea, retinal light flashes, sudden fatigue with dose rise)
           AND an active DONKI SEP / FLR M-X / RBE event          -> external cause confirmed (space weather)
  Layer 2  otherwise, internal physiological patterns (fever + tachycardia + short sleep; hypotension + tachycardia;
           any primary vital past a NASA flight-rule threshold), onboard environment (cabin CO2, dosimeter spike
           with no DONKI event) or a benign context (post-exercise)  -> internal / onboard / contextual cause
  Layer 3  behavioural or sensory signs (mood <= 2, sleep < 5 h, CTB > 390 ms, unusual smells, irritability)
           with NO physical or external explanation               -> neurocognitive overload / isolation stress,
           PsychGuard protocol; severe signs -> immediate Earth Flight Surgeon alert.

Every branch records the evidence it used and the alternatives it ruled out. The tree never prescribes
treatment; it ranks causes and lists protocol steps for the crew medical officer.
"""

from __future__ import annotations

import re
import unicodedata

from app.engine import nasa_calibration as cal
from app.models.schemas import (
    ClinicalEvaluationResult,
    ContextualIntelligenceReport,
    CrossDiagnosisResult,
    CrossEvidence,
    MissionContext,
    PsychProtocol,
    SpaceWeatherSummary,
    VitalSigns,
)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode("ascii")


# Keyword families (PT/EN, accents stripped)
RADIATION_SYMPTOMS = re.compile(r"nause|nausea|enjo|vomit|flash|phosphen|fosfen|lampej|clarao|luz(es)? no olho|light flash")
SUDDEN_FATIGUE = re.compile(r"fadiga subita|cansaco subito|sudden fatigue|exhaust|exaust")
SENSORY_BEHAVIOURAL = re.compile(
    r"cheiro|smell|odor|irrita|ansios|anxious|panic|panico|insoni|insomnia|nao consigo dormir|can'?t sleep|"
    r"briga|conflit|tense|angry|raiva|vozes|voices|alucin|hallucin"
)
SEVERE_PSYCH = re.compile(
    r"suicid|me matar|kill myself|tirar (a )?minha vida|end (it|my life)|acabar com tudo|me machucar|hurt myself|"
    r"nao quero (mais )?viver|don'?t want to live|self[- ]harm|autoles|"
    r"nada importa|nothing matters|totalmente desconectad|completely disconnected|ninguem (se )?importa|no one cares"
)


def _symptom_text(vitals: VitalSigns, message: str | None) -> str:
    return _norm(" | ".join(vitals.reported_symptoms) + " | " + (message or ""))


def _physical_findings(vitals: VitalSigns, context: MissionContext, ctx: ContextualIntelligenceReport) -> list[CrossEvidence]:
    """Primary vitals past a NASA flight-rule threshold. HRV and stress are deliberately excluded: they are
    correlates of psychological strain, not evidence of a physical cause."""
    found: list[CrossEvidence] = []
    exercise_explains = ctx.context_explains_deviation and context.minutes_since_last_exercise <= 60

    def add(signal: str, value: str, rule: str) -> None:
        found.append(CrossEvidence(signal=signal, value=value, rule=rule))

    t = vitals.temperature_c
    if t >= cal.TEMP_CRIT_HIGH or t < cal.TEMP_CRIT_LOW:
        add("Core temperature", f"{t:.1f} C", f">= {cal.TEMP_CRIT_HIGH} or < {cal.TEMP_CRIT_LOW} C")
    hr = vitals.heart_rate_bpm
    if (hr > cal.HR_WARN_HIGH or hr < cal.HR_WARN_LOW) and not exercise_explains:
        add("Resting heart rate", f"{hr:.0f} bpm", f"outside {cal.HR_WARN_LOW:.0f}-{cal.HR_WARN_HIGH:.0f} bpm at rest")
    sbp = vitals.bp_systolic
    if sbp < cal.BP_SYS_WARN_LOW or (sbp > cal.BP_SYS_CRIT_HIGH and not exercise_explains):
        add("Systolic BP", f"{sbp:.0f} mmHg", f"< {cal.BP_SYS_WARN_LOW:.0f} or > {cal.BP_SYS_CRIT_HIGH:.0f} mmHg")
    if vitals.spo2_pct < 94.0 or vitals.respiration_rpm >= 24:
        add("SpO2 / respiration", f"{vitals.spo2_pct:.1f}% / {vitals.respiration_rpm:.0f} rpm", "SpO2 < 94% or RR >= 24")
    g = vitals.glucose_mg_dl
    if g <= cal.GLUCOSE_WARN_LOW or g >= cal.GLUCOSE_CRIT_HIGH:
        add("Glucose", f"{g:.0f} mg/dL", f"<= {cal.GLUCOSE_WARN_LOW:.0f} or >= {cal.GLUCOSE_CRIT_HIGH:.0f} mg/dL")
    if vitals.radiation_msv_h >= cal.RADIATION_WARN_RATE_MSV_H:
        add("Dosimeter", f"{vitals.radiation_msv_h:.2f} mSv/h", f">= {cal.RADIATION_WARN_RATE_MSV_H} mSv/h (nominal 0.025-0.038)")
    if vitals.shoulder_pain_score >= 7:
        add("Shoulder pain", f"{vitals.shoulder_pain_score}/10", ">= 7/10 VAS")
    return found


def _behavioural_findings(vitals: VitalSigns, text: str) -> list[CrossEvidence]:
    found: list[CrossEvidence] = []
    if vitals.mood_score <= cal.MOOD_CRIT:
        found.append(CrossEvidence(signal="Mood", value=f"{vitals.mood_score}/5", rule=f"<= {cal.MOOD_CRIT}/5"))
    if vitals.sleep_hours < 5.0:
        found.append(
            CrossEvidence(
                signal="Sleep", value=f"{vitals.sleep_hours:.1f} h ({vitals.sleep_streak_low_days} nights < 4.5 h)",
                rule="< 5 h (critical: < 4.5 h for 2 nights)",
            )
        )
    if vitals.ctb_reaction_time_ms > cal.CTB_CRIT_MS:
        found.append(
            CrossEvidence(
                signal="CTB reaction time", value=f"{vitals.ctb_reaction_time_ms:.0f} ms", rule=f"> {cal.CTB_CRIT_MS:.0f} ms (+30%)"
            )
        )
    m = SENSORY_BEHAVIOURAL.search(text)
    if m:
        found.append(CrossEvidence(signal="Crew report", value=f"'{m.group(0)}'", rule="unusual sensory / behavioural report"))
    return found


def _active_donki(sw: SpaceWeatherSummary | None) -> list[str]:
    if sw is None:
        return []
    out = []
    for e in sw.events:
        if not e.is_active:
            continue
        relevant = e.event_type in ("SEP", "RBE") or (
            e.event_type == "FLR" and e.class_or_intensity[:1].upper() in ("M", "X")
        )
        if relevant:
            tag = " [scenario simulation]" if e.origin == "scenario_simulation" else ""
            out.append(f"{e.event_type} {e.class_or_intensity} @ {e.begin_time}{tag}")
    return out


def _psych_protocol(physical_ok: list[str], severe_reason: str | None, mood: int, streak: int) -> PsychProtocol:
    escalate = severe_reason is not None or mood <= 1 or streak >= 3
    reason = severe_reason or (
        "Mood 1/5" if mood <= 1 else ("3+ consecutive nights under 4.5 h" if streak >= 3 else None)
    )
    return PsychProtocol(
        reassurance=(
            (
                "Your body and the spacecraft are reading safe right now: " + "; ".join(physical_ok) + ". "
                "What you are feeling is real and common on long missions, and it is not a sign that something "
                "is physically wrong. Let's slow things down together."
            )
            if physical_ok
            else "You are not alone in this. The crew medical officer and the ground team are being contacted now; "
            "stay with a crewmate while we talk."
        ),
        verified_safe_checks=physical_ok,
        grounding_steps=[
            "Box breathing: inhale 4 s, hold 4 s, exhale 4 s, hold 4 s, five rounds.",
            "5-4-3-2-1 grounding: name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste.",
            "Anchor to Earth: 5 minutes at the window or with a personal photo/video from home.",
            "Circadian reset: dim cabin light now, bright light on waking, no screens 60 min before the next sleep period.",
            "Book a private psychological conference (PPC) with the ground behavioral health team.",
        ],
        escalate_to_earth=escalate,
        escalation_reason=reason,
    )


def evaluate_cross_diagnosis(
    vitals: VitalSigns,
    context: MissionContext,
    space_weather: SpaceWeatherSummary | None,
    contextual_report: ContextualIntelligenceReport,
    clinical: ClinicalEvaluationResult,
    message: str | None = None,
) -> CrossDiagnosisResult:
    result = _evaluate(vitals, context, space_weather, contextual_report, clinical, message)
    # Self-harm / severe disconnection language escalates whatever the physical layer concluded.
    if result.layer != 3 and SEVERE_PSYCH.search(_symptom_text(vitals, message)):
        result.psych_protocol = _psych_protocol(
            [], "Crew message suggests risk of self-harm or severe disconnection", vitals.mood_score,
            vitals.sleep_streak_low_days,
        )
        result.notify_earth = True
        result.earth_priority = "IMMEDIATE"
        result.recommended_actions.insert(0, "IMMEDIATE: alert Earth Flight Surgeon and behavioral health team.")
        result.evidence.insert(0, CrossEvidence(signal="Crew message", value="severe-risk language", rule="immediate escalation"))
    return result


def _evaluate(
    vitals: VitalSigns,
    context: MissionContext,
    space_weather: SpaceWeatherSummary | None,
    contextual_report: ContextualIntelligenceReport,
    clinical: ClinicalEvaluationResult,
    message: str | None = None,
) -> CrossDiagnosisResult:
    text = _symptom_text(vitals, message)
    physical = _physical_findings(vitals, context, contextual_report)
    behavioural = _behavioural_findings(vitals, text)
    donki = _active_donki(space_weather)
    severe = SEVERE_PSYCH.search(text)
    refs = list(cal.REFERENCES)

    dose_up = vitals.radiation_msv_h >= cal.RADIATION_WARN_RATE_MSV_H
    rad_symptom = RADIATION_SYMPTOMS.search(text)
    fatigue_with_dose = dose_up and SUDDEN_FATIGUE.search(text)
    radiation_signs: list[CrossEvidence] = []
    if dose_up:
        radiation_signs.append(
            CrossEvidence(signal="Dosimeter", value=f"{vitals.radiation_msv_h:.2f} mSv/h", rule=f">= {cal.RADIATION_WARN_RATE_MSV_H} mSv/h")
        )
    if rad_symptom:
        radiation_signs.append(CrossEvidence(signal="Crew report", value=f"'{rad_symptom.group(0)}'", rule="radiation-compatible symptom"))
    if fatigue_with_dose:
        radiation_signs.append(CrossEvidence(signal="Crew report", value="sudden fatigue", rule="with dose-rate rise"))

    donki_note = (
        f"DONKI {space_weather.status_label} ({space_weather.source}, active window {space_weather.active_window_hours} h)"
        if space_weather
        else "DONKI unavailable"
    )

    # ---------------- Layer 1: external cause (space weather) ----------------
    if radiation_signs and donki:
        shelter = vitals.radiation_msv_h > cal.RADIATION_SPE_RATE_MSV_H or any(d.startswith("SEP") for d in donki)
        return CrossDiagnosisResult(
            layer=1,
            root_cause="EXTERNAL_SPACE_WEATHER",
            title="External cause confirmed: solar storm / ionizing radiation",
            summary=(
                f"Radiation-compatible signs coincide with active NASA DONKI events ({'; '.join(donki)}). "
                "A common infection is not the leading explanation for this picture."
            ),
            evidence=radiation_signs
            + [CrossEvidence(signal="NASA DONKI", value=d, rule="active SEP / FLR M-X / RBE") for d in donki],
            donki_events_considered=donki,
            recommended_actions=[
                "RED ALERT: move to the shielded storm-shelter area of the vehicle now (ALARA).",
                "Hold all extravehicular activities (EVA) until dose rate returns to baseline.",
                "Log dosimeter readings every 15 min; event dose limit is 250 mSv per SPE (NASA-STD-3001).",
                "Notify the Earth Flight Surgeon and space weather console with the dosimeter trend.",
            ],
            shelter_recommended=shelter,
            eva_hold_recommended=True,
            notify_earth=True,
            earth_priority="IMMEDIATE",
            references=refs,
        )

    ruled_out = [CrossEvidence(signal="NASA DONKI", value=donki_note, rule="no radiation-compatible signs" if donki else "no active SEP/FLR M-X/RBE", supports=False)]

    # ---------------- Layer 2: internal / onboard / contextual ----------------
    if dose_up and not donki:
        return CrossDiagnosisResult(
            layer=2,
            root_cause="ONBOARD_ENVIRONMENT",
            title="Dosimeter spike without a DONKI event",
            summary=(
                "The onboard dose rate is elevated but NASA DONKI reports no active SEP, M/X flare or radiation-belt "
                "enhancement. Check for a local source or a dosimeter fault before assuming a solar storm."
            ),
            evidence=radiation_signs + ruled_out,
            recommended_actions=[
                "Cross-check with a second dosimeter and the cabin radiation monitor.",
                "Inspect for local sources and dosimeter placement/fault.",
                "If the rise persists 15 min, apply ALARA posture and inform the ground.",
            ],
            notify_earth=True,
            earth_priority="PRIORITY",
            references=refs,
        )

    if rad_symptom and not donki:
        # Physical symptom with no radiation source: not something to hand to the psych protocol.
        return CrossDiagnosisResult(
            layer=2,
            root_cause="INTERNAL_PHYSIOLOGICAL",
            title="Unexplained physical symptom (no radiation source found)",
            summary=(
                f"Crew reports '{rad_symptom.group(0)}' but the dosimeter is nominal and DONKI shows no active event. "
                "Light flashes without radiation can come from the retina; nausea has many internal causes."
            ),
            evidence=radiation_signs + ruled_out,
            recommended_actions=[
                "Fundoscopy / OCT check for retinal changes if light flashes persist.",
                "Re-check dosimeter placement and the cabin radiation monitor.",
                "Record symptom onset and duration; reassess in 30 min.",
            ],
            notify_earth=True,
            earth_priority="ROUTINE",
            references=refs,
        )

    if vitals.temperature_c >= cal.TEMP_CRIT_HIGH and vitals.heart_rate_bpm > 90 and vitals.sleep_hours < 6.0:
        return CrossDiagnosisResult(
            layer=2,
            root_cause="INTERNAL_PHYSIOLOGICAL",
            title="Suspected viral infection / immune reactivation in microgravity",
            summary=(
                f"Fever {vitals.temperature_c:.1f} C with heart rate {vitals.heart_rate_bpm:.0f} bpm and "
                f"{vitals.sleep_hours:.1f} h sleep, while space weather does not explain it."
            ),
            evidence=physical + ruled_out,
            recommended_actions=clinical.stabilization_checklist[:4]
            or ["Confirm tympanic temperature and NIBP after 10 min rest.", "Start hydration and isolation per HSP."],
            notify_earth=True,
            earth_priority="PRIORITY",
            references=refs,
        )

    if vitals.bp_systolic < cal.BP_SYS_CRIT_LOW and vitals.heart_rate_bpm > 100:
        return CrossDiagnosisResult(
            layer=2,
            root_cause="INTERNAL_PHYSIOLOGICAL",
            title="Orthostatic hypotension / dehydration from fluid redistribution",
            summary=(
                f"Systolic {vitals.bp_systolic:.0f} mmHg with heart rate {vitals.heart_rate_bpm:.0f} bpm: "
                "compatible with plasma-volume loss after cephalad fluid shift."
            ),
            evidence=physical + ruled_out,
            recommended_actions=clinical.stabilization_checklist[:4]
            or ["Anchored supine NIBP re-check.", "Oral fluid and salt loading per protocol."],
            notify_earth=True,
            earth_priority="PRIORITY",
            references=refs,
        )

    if context.cabin_co2_mmhg >= 3.5:
        return CrossDiagnosisResult(
            layer=2,
            root_cause="ONBOARD_ENVIRONMENT",
            title="Cabin CO2 exposure",
            summary=f"Local ppCO2 {context.cabin_co2_mmhg:.1f} mmHg can explain respiratory, sleep and mood changes.",
            evidence=physical + ruled_out,
            recommended_actions=["Increase module ventilation and inspect the CO2 scrubber.", "Re-check SpO2 and respiration in 30 min."],
            notify_earth=True,
            earth_priority="ROUTINE",
            references=refs,
        )

    if contextual_report.context_explains_deviation:
        return CrossDiagnosisResult(
            layer=2,
            root_cause="CONTEXTUAL_BENIGN",
            title="Benign context explains the readings",
            summary=contextual_report.primary_contextual_summary,
            evidence=ruled_out,
            recommended_actions=["Re-measure at rest after 20 minutes before escalating."],
            references=refs,
        )

    if physical:
        return CrossDiagnosisResult(
            layer=2,
            root_cause="INTERNAL_PHYSIOLOGICAL",
            title=clinical.primary_diagnosis,
            summary="A primary vital sign is past a NASA flight-rule threshold; space weather does not explain it.",
            evidence=physical + ruled_out,
            recommended_actions=clinical.stabilization_checklist[:4],
            notify_earth=clinical.notify_earth_flight_surgeon,
            earth_priority="PRIORITY" if clinical.overall_status == "CRITICAL" else "ROUTINE",
            references=refs,
        )

    # ---------------- Layer 3: psychological / neurocognitive ----------------
    if behavioural or severe:
        physical_ok = [
            f"temperature {vitals.temperature_c:.1f} C",
            f"heart rate {vitals.heart_rate_bpm:.0f} bpm",
            f"blood pressure {vitals.bp_systolic:.0f}/{vitals.bp_diastolic:.0f} mmHg",
            f"SpO2 {vitals.spo2_pct:.0f}%",
            f"cabin CO2 {context.cabin_co2_mmhg:.1f} mmHg",
            f"radiation {vitals.radiation_msv_h:.3f} mSv/h, no active solar storm",
        ]
        protocol = _psych_protocol(
            physical_ok, "Crew message suggests risk of self-harm or severe disconnection" if severe else None,
            vitals.mood_score, vitals.sleep_streak_low_days,
        )
        evidence = behavioural + [
            CrossEvidence(signal="Physical vitals", value="within flight rules", rule="no physical cause found", supports=False)
        ] + ruled_out
        if severe:
            evidence.insert(0, CrossEvidence(signal="Crew message", value="severe-risk language", rule="immediate escalation"))
        return CrossDiagnosisResult(
            layer=3,
            root_cause="PSYCHOLOGICAL_NEUROCOGNITIVE",
            title="Neurocognitive overload / confinement and isolation stress (no primary physical cause)",
            summary=(
                "Behavioural or sensory changes without a physical, environmental or space-weather explanation. "
                "PsychGuard protocol activated."
            ),
            evidence=evidence,
            recommended_actions=protocol.grounding_steps[:3]
            + (["IMMEDIATE: alert Earth Flight Surgeon and behavioral health team."] if protocol.escalate_to_earth else []),
            notify_earth=protocol.escalate_to_earth,
            earth_priority="IMMEDIATE" if protocol.escalate_to_earth else "ROUTINE",
            psych_protocol=protocol,
            references=refs,
        )

    return CrossDiagnosisResult(
        layer=0,
        root_cause="NOMINAL",
        title="No anomaly to attribute",
        summary="Vitals, behaviour and space weather are within nominal in-flight ranges.",
        evidence=ruled_out,
        references=refs,
    )


# Any crew message mentioning a symptom family is kept as a reported symptom
SYMPTOM_REPORT = re.compile(
    "|".join(p.pattern for p in (RADIATION_SYMPTOMS, SUDDEN_FATIGUE, SENSORY_BEHAVIOURAL, SEVERE_PSYCH))
)

_ROOT_PT = {
    "NOMINAL": "Nominal",
    "EXTERNAL_SPACE_WEATHER": "Causa externa (clima espacial / radiação)",
    "ONBOARD_ENVIRONMENT": "Ambiente da nave",
    "CONTEXTUAL_BENIGN": "Contexto benigno",
    "INTERNAL_PHYSIOLOGICAL": "Causa física interna",
    "PSYCHOLOGICAL_NEUROCOGNITIVE": "Sobrecarga neurocognitiva / estresse de isolamento",
}


GROUNDING_PT = [
    "Respiração quadrada: inspire 4 s, segure 4 s, expire 4 s, segure 4 s, cinco ciclos.",
    "Aterramento 5-4-3-2-1: nomeie 5 coisas que vê, 4 que pode tocar, 3 que ouve, 2 cheiros, 1 sabor.",
    "Âncora na Terra: 5 minutos na janela ou com uma foto/vídeo pessoal de casa.",
    "Reajuste circadiano: luz da cabine baixa agora, luz forte ao acordar, sem telas 60 min antes de dormir.",
    "Agende uma conferência psicológica privada (PPC) com a equipe de saúde comportamental em Terra.",
]


def render_cross_diagnosis(c: CrossDiagnosisResult, pt: bool) -> str:
    """Chat text for the cross-diagnosis result (the dashboard renders the structured fields itself)."""
    head = (
        f"**Diagnóstico cruzado — Camada {c.layer}: {_ROOT_PT[c.root_cause]}**\n{c.title}. {c.summary}"
        if pt
        else f"**Cross diagnosis — Layer {c.layer}: {c.root_cause.replace('_', ' ').title()}**\n{c.title}. {c.summary}"
    )
    lines = [head]
    supports = [e for e in c.evidence if e.supports]
    ruled = [e for e in c.evidence if not e.supports]
    if supports:
        lines.append(("Evidências: " if pt else "Evidence: ") + "; ".join(f"{e.signal} {e.value} ({e.rule})" for e in supports[:5]))
    if ruled:
        lines.append(("Descartado: " if pt else "Ruled out: ") + "; ".join(f"{e.signal}: {e.value}" for e in ruled[:3]))
    if c.psych_protocol:
        pp = c.psych_protocol
        if pt:
            reassurance = (
                "Seu corpo e a nave estão com leituras seguras agora: " + "; ".join(pp.verified_safe_checks) + ". "
                "O que você está sentindo é real e comum em missões longas, e não indica um problema físico. "
                "Vamos desacelerar juntos."
                if pp.verified_safe_checks
                else "Você não está sozinho. O médico da tripulação e a equipe em Terra estão sendo acionados; "
                "fique com um colega de tripulação enquanto conversamos."
            )
            steps = GROUNDING_PT
        else:
            reassurance, steps = pp.reassurance, pp.grounding_steps
        lines.append(f"**{pp.name}:** {reassurance}")
        lines.append("\n".join(f"{i}. {s}" for i, s in enumerate(steps, start=1)))
    elif c.recommended_actions:
        lines.append(("Ações sugeridas: " if pt else "Suggested actions: ") + " | ".join(c.recommended_actions[:4]))
    lines.append(f"*{c.disclaimer}*")
    return "\n".join(lines)
