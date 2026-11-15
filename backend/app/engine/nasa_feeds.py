from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.models.schemas import (
    HorizonsLinkStatus,
    SeverityStatus,
    SpaceWeatherEvent,
    SpaceWeatherSummary,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
STATE_DIR = Path(os.environ.get("ASTRACARE_STATE_DIR", DATA_DIR))
DONKI_CACHE_PATH = STATE_DIR / "donki_cache.json"

# TODO: Substituir DEMO_KEY pela chave oficial gerada em https://api.nasa.gov/
# DEMO_KEY allows ~10 requests/hour per IP on DONKI; set NASA_API_KEY in the environment (never commit it).
NASA_API_KEY_DEFAULT = "DEMO_KEY"
DONKI_BASE = "https://api.nasa.gov/DONKI"
DONKI_TYPES = ("SEP", "FLR", "RBE")  # Solar Energetic Particles, Solar Flares, Radiation Belt Enhancement
QUERY_WINDOW_DAYS = 7  # DONKI rejects ranges above 60 days
ACTIVE_WINDOW_HOURS = 72  # an event counts as "active" if it started within this window
CACHE_TTL_MINUTES = 30  # reuse a fresh live answer instead of spending DEMO_KEY quota
REQUEST_TIMEOUT_S = 4.0

# Field holding the event start time, per DONKI type
_TIME_FIELD = {"FLR": "beginTime", "SEP": "eventTime", "RBE": "eventTime"}
_ID_FIELD = {"FLR": "flrID", "SEP": "sepID", "RBE": "rbeID"}


def _api_key() -> str:
    return os.getenv("NASA_API_KEY", NASA_API_KEY_DEFAULT)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # DONKI uses e.g. "2026-11-14T06:05Z"
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _instruments(item: dict[str, Any]) -> str:
    inst = item.get("instruments") or []
    if isinstance(inst, list):
        return ", ".join(i.get("displayName", "") for i in inst if isinstance(i, dict))[:120]
    return str(inst)


def summarize_donki(
    raw: dict[str, list[dict[str, Any]]],
    *,
    source: str,
    fetch_status: str,
    fetched_at: str | None = None,
    now: datetime | None = None,
    simulated: dict[str, list[dict[str, Any]]] | None = None,
) -> SpaceWeatherSummary:
    """Turn DONKI SEP/FLR/RBE arrays (exact API JSON) into the onboard space-weather summary."""
    now = now or datetime.now(timezone.utc)
    active_since = now - timedelta(hours=ACTIVE_WINDOW_HOURS)
    events: list[SpaceWeatherEvent] = []

    def add(kind: str, item: dict[str, Any], origin: str) -> None:
        start = _parse_time(item.get(_TIME_FIELD[kind]))
        active = start is not None and active_since <= start <= now + timedelta(hours=1)
        if kind == "FLR":
            intensity = item.get("classType") or "Unclassified flare"
            location = item.get("sourceLocation") or "Solar disk"
        elif kind == "SEP":
            intensity = _instruments(item) or "Solar energetic particle enhancement"
            location = "Interplanetary"
        else:
            intensity = _instruments(item) or "Radiation belt electron enhancement"
            location = "Radiation belts"
        events.append(
            SpaceWeatherEvent(
                event_id=str(item.get(_ID_FIELD[kind], kind)),
                event_type=kind,  # type: ignore[arg-type]
                begin_time=str(item.get(_TIME_FIELD[kind], "")),
                peak_time=item.get("peakTime"),
                class_or_intensity=str(intensity),
                source_location=str(location),
                note=str(item.get("note") or f"NASA DONKI {kind} notification"),
                is_active=active,
                origin=origin,  # type: ignore[arg-type]
                link=item.get("link"),
            )
        )

    for kind in DONKI_TYPES:
        for item in raw.get(kind, []) or []:
            add(kind, item, "nasa_donki")
        for item in (simulated or {}).get(kind, []) or []:
            add(kind, item, "scenario_simulation")

    active = [e for e in events if e.is_active]
    sep = [e for e in active if e.event_type == "SEP"]
    rbe = [e for e in active if e.event_type == "RBE"]
    flr = [e for e in active if e.event_type == "FLR"]
    flr_mx = [e for e in flr if e.class_or_intensity[:1].upper() in ("M", "X")]
    flr_x = [e for e in flr if e.class_or_intensity[:1].upper() == "X"]

    alert: SeverityStatus = "NOMINAL"
    if sep or flr_x:
        alert = "CRITICAL"
    elif flr_mx or rbe:
        alert = "WARNING"

    if sep:
        label = "SEP alert active"
    elif flr_mx:
        top = sorted(flr_mx, key=lambda e: e.class_or_intensity, reverse=True)[0]
        label = f"Class {top.class_or_intensity} flare detected"
    elif rbe:
        label = "Radiation belt enhancement active"
    elif flr:
        label = "Minor flares only (A/B/C)"
    else:
        label = "Nominal"

    if alert == "CRITICAL":
        instruction = (
            "Active SEP / X-class flare: confirm onboard dosimeter trend, prepare storm-shelter posture, "
            "hold EVAs until dose rate returns to baseline (NASA-STD-3001: 250 mSv per SPE event limit)."
        )
    elif alert == "WARNING":
        instruction = "Elevated solar activity: watch dosimeter trend and keep the storm shelter ready (ALARA)."
    else:
        instruction = "No SEP, M/X flare or radiation-belt enhancement active: continue standard ALARA dosimetry."

    window_end = now
    window_start = now - timedelta(days=QUERY_WINDOW_DAYS)
    return SpaceWeatherSummary(
        source=source,  # type: ignore[arg-type]
        fetched_at=fetched_at or now.isoformat(),
        alert_level=alert,
        active_flare_count=len(flr),
        active_sep_count=len(sep),
        active_rbe_count=len(rbe),
        comms_degradation_risk="MODERATE_HF_SCINTILLATION" if (sep or flr_x) else "NONE",
        recommended_dose_limit_msv_h=0.50,
        alara_instruction=instruction,
        status_label=label,
        fetch_status=fetch_status,
        window_start=window_start.date().isoformat(),
        window_end=window_end.date().isoformat(),
        active_window_hours=ACTIVE_WINDOW_HOURS,
        uses_demo_key=_api_key() == NASA_API_KEY_DEFAULT,
        includes_scenario_simulation=bool(simulated and any(simulated.values())),
        events=sorted(events, key=lambda e: e.begin_time, reverse=True)[:12],
    )


# ---------------- raw sources (exact DONKI JSON) ----------------
def load_sample_donki_raw() -> dict[str, list[dict[str, Any]]]:
    with open(DATA_DIR / "nasa_donki_sample.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {k: list(raw.get(k, [])) for k in DONKI_TYPES}


def _read_cache() -> dict[str, Any] | None:
    try:
        return json.loads(DONKI_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_cache(raw: dict[str, list[dict[str, Any]]], fetched_at: str) -> None:
    try:
        DONKI_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        DONKI_CACHE_PATH.write_text(json.dumps({"fetched_at": fetched_at, "data": raw}), encoding="utf-8")
    except OSError:
        logger.exception("Could not write DONKI cache")


async def fetch_donki_raw(force: bool = False) -> tuple[dict[str, list[dict[str, Any]]], str, str, str]:
    """Returns (raw, source, fetch_status, fetched_at). Never raises: live -> cache -> curated sample."""
    now = datetime.now(timezone.utc)
    cache = _read_cache()
    if cache and not force:
        age = now - datetime.fromisoformat(cache["fetched_at"])
        if age < timedelta(minutes=CACHE_TTL_MINUTES):
            mins = int(age.total_seconds() // 60)
            return cache["data"], "cached_nasa_donki", f"cache reused ({mins} min old, TTL {CACHE_TTL_MINUTES} min)", cache["fetched_at"]

    start = (now - timedelta(days=QUERY_WINDOW_DAYS)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    key = _api_key()
    failure = ""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
            responses = await asyncio.gather(
                *(client.get(f"{DONKI_BASE}/{t}", params={"startDate": start, "endDate": end, "api_key": key}) for t in DONKI_TYPES),
                return_exceptions=True,
            )
        raw: dict[str, list[dict[str, Any]]] = {}
        for kind, resp in zip(DONKI_TYPES, responses):
            if isinstance(resp, Exception):
                failure = f"{kind}: {type(resp).__name__}"
                break
            if resp.status_code == 429:
                failure = f"{kind}: HTTP 429 rate limit"
                break
            if resp.status_code != 200:
                failure = f"{kind}: HTTP {resp.status_code}"
                break
            body = resp.json() if resp.content else []
            raw[kind] = body if isinstance(body, list) else []  # DONKI answers an empty body when there are no events
        else:
            fetched_at = now.isoformat()
            _write_cache(raw, fetched_at)
            return raw, "live_nasa_donki", "live", fetched_at
    except Exception as exc:  # network down onboard: never break the medical UI
        failure = type(exc).__name__

    if cache:
        mins = int((now - datetime.fromisoformat(cache["fetched_at"])).total_seconds() // 60)
        return cache["data"], "cached_nasa_donki", f"{failure} -> last good answer from {mins} min ago", cache["fetched_at"]
    return load_sample_donki_raw(), "curated_local_fallback", f"{failure} -> curated DONKI-format sample", now.isoformat()


def load_sample_donki(simulated: dict[str, list[dict[str, Any]]] | None = None) -> SpaceWeatherSummary:
    """Synchronous offline start-up value: last cache if any, else the curated sample."""
    cache = _read_cache()
    if cache:
        return summarize_donki(
            cache["data"], source="cached_nasa_donki", fetch_status="startup: last cached answer",
            fetched_at=cache["fetched_at"], simulated=simulated,
        )
    return summarize_donki(
        load_sample_donki_raw(), source="curated_local_fallback", fetch_status="startup: curated sample", simulated=simulated
    )


async def fetch_nasa_space_weather(
    simulated: dict[str, list[dict[str, Any]]] | None = None, force: bool = False
) -> SpaceWeatherSummary:
    raw, source, status, fetched_at = await fetch_donki_raw(force=force)
    return summarize_donki(raw, source=source, fetch_status=status, fetched_at=fetched_at, simulated=simulated)


def load_sample_horizons(environment_id: str) -> HorizonsLinkStatus:
    with open(DATA_DIR / "nasa_horizons_sample.json", "r", encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)

    ephem_map = raw.get("horizons_ephemeris", {})
    env_data = ephem_map.get(environment_id, ephem_map.get("transit", {}))

    return HorizonsLinkStatus(
        source="curated_local_fallback",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        target_body=str(env_data.get("target_body", "Deep Space Transit Corridor")),
        distance_km=float(env_data.get("distance_km", 215850600.0)),
        distance_au=float(env_data.get("distance_au", 1.4429)),
        one_way_light_time_seconds=float(env_data.get("one_way_light_time_seconds", 720.0)),
        round_trip_light_time_seconds=float(env_data.get("round_trip_light_time_seconds", 1440.0)),
        bandwidth_kbps=float(env_data.get("bandwidth_kbps", 128.0)),
        link_window_status=str(env_data.get("link_window_status", "STORE_AND_FORWARD_DELAYED")),
        comms_available=True,
    )
