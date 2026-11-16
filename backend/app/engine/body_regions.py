"""
Body regions the crew can report pain on (one per selectable part of the 3D anatomical model) and the clinical
category each one feeds into the rules, the cross-diagnosis tree and the ML features.

Categories:
  head             headache: cabin CO2, SANS / fluid shift, dehydration, radiation sickness
  chest            chest pain: cardiopulmonary red flag, always escalated
  abdominal        abdominal / flank: renal stones (bone demineralisation), GI, hypoglycaemic stress
  musculoskeletal  neck, back, shoulders, limbs, joints: EVA suit load, space adaptation back pain, exercise
"""

from __future__ import annotations

from typing import Literal

PainCategory = Literal["head", "chest", "abdominal", "musculoskeletal"]

# id -> (label, category). Ids match the part ids of the frontend anatomical model.
BODY_REGIONS: dict[str, tuple[str, PainCategory]] = {
    "head": ("Head", "head"),
    "neck": ("Neck", "musculoskeletal"),
    "chest": ("Chest", "chest"),
    "abdomen": ("Abdomen", "abdominal"),
    "upper_back": ("Upper back", "musculoskeletal"),
    "lower_back": ("Lower back", "musculoskeletal"),
    "pelvis": ("Hips & pelvis", "musculoskeletal"),
    "left_shoulder": ("Left shoulder", "musculoskeletal"),
    "right_shoulder": ("Right shoulder", "musculoskeletal"),
    "left_upper_arm": ("Left upper arm", "musculoskeletal"),
    "right_upper_arm": ("Right upper arm", "musculoskeletal"),
    "left_elbow": ("Left elbow", "musculoskeletal"),
    "right_elbow": ("Right elbow", "musculoskeletal"),
    "left_forearm": ("Left forearm", "musculoskeletal"),
    "right_forearm": ("Right forearm", "musculoskeletal"),
    "left_hand": ("Left hand", "musculoskeletal"),
    "right_hand": ("Right hand", "musculoskeletal"),
    "left_thigh": ("Left thigh", "musculoskeletal"),
    "right_thigh": ("Right thigh", "musculoskeletal"),
    "left_knee": ("Left knee", "musculoskeletal"),
    "right_knee": ("Right knee", "musculoskeletal"),
    "left_calf": ("Left lower leg", "musculoskeletal"),
    "right_calf": ("Right lower leg", "musculoskeletal"),
    "left_foot": ("Left foot", "musculoskeletal"),
    "right_foot": ("Right foot", "musculoskeletal"),
}

PAIN_CATEGORIES: tuple[PainCategory, ...] = ("head", "chest", "abdominal", "musculoskeletal")
SHOULDER_REGIONS = {"left_shoulder", "right_shoulder"}


def category_of(region: str) -> PainCategory:
    return BODY_REGIONS[region][1]


def pain_by_category(reports: list) -> dict[str, float]:
    """Highest reported intensity per category (0 when nothing reported)."""
    out = {c: 0.0 for c in PAIN_CATEGORIES}
    for r in reports:
        region = getattr(r, "region", None) or (r.get("region") if isinstance(r, dict) else None)
        intensity = getattr(r, "intensity", None) if not isinstance(r, dict) else r.get("intensity")
        if region in BODY_REGIONS and intensity is not None:
            cat = category_of(region)
            out[cat] = max(out[cat], float(intensity))
    return out
