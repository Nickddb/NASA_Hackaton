"""Regenerate frontend/public/data/scenarios.json from the NASA-calibrated generator.

The browser fallback (used only when the backend is unreachable, and labelled SIMULATED DATA in the UI)
needs concrete numbers. Instead of hand-written vitals they are a snapshot of the same stochastic model
the backend runs, for the default astronaut.

    cd backend && .venv/Scripts/python.exe scripts/export_frontend_fallback.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.engine.telemetry_generator import TelemetryGenerator  # noqa: E402

catalog = json.loads((BACKEND / "data" / "scenarios.json").read_text(encoding="utf-8"))
astro = next(a for a in catalog["astronaut_profiles"] if a["astronaut_id"] == "elena_vance")

out_scenarios = []
for sc in catalog["scenarios"]:
    phase = sc.get("mission_context", {}).get("mission_phase", "chronic_microgravity_cruise")
    vitals, series = TelemetryGenerator(astro, phase).generate(sc.get("crisis_profile", sc["id"]), int(sc["mission_day"]))
    vitals["reported_symptoms"] = list(sc.get("reported_symptoms", []))
    entry = {k: v for k, v in sc.items() if k != "donki_simulation"}
    entry["vitals"] = vitals
    entry["longitudinal_series"] = series
    out_scenarios.append(entry)

out = {
    "telemetry_source": (
        "Snapshot of app/engine/telemetry_generator.py for CDR Elena Vance; regenerate with "
        "backend/scripts/export_frontend_fallback.py. Used only by the offline browser fallback."
    ),
    "scenarios": out_scenarios,
    "environments": catalog["environments"],
    "indicators_guide": catalog.get("indicators_guide", []),
    "systems_guide": catalog.get("systems_guide", {}),
}
target = BACKEND.parent / "frontend" / "public" / "data" / "scenarios.json"
target.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {target} ({len(out_scenarios)} scenarios)")
