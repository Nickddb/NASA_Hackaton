from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any

import httpx

from app.models.schemas import (
    HorizonsLinkStatus,
    SeverityStatus,
    SpaceWeatherEvent,
    SpaceWeatherSummary,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_sample_donki() -> SpaceWeatherSummary:
    with open(DATA_DIR / "nasa_donki_sample.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    events: list[SpaceWeatherEvent] = []
    for flr in raw.get("flr_events", []):
        events.append(
            SpaceWeatherEvent(
                event_id=flr.get("flrID", "FLR-SAMPLE"),
                event_type="FLR",
                begin_time=flr.get("beginTime", ""),
                peak_time=flr.get("peakTime"),
                class_or_intensity=flr.get("classType", "M-Class"),
                source_location=flr.get("sourceLocation", "Solar Disk"),
                note=flr.get("note", "Solar flare alert from curated NASA DONKI sample."),
            )
        )
    for sep in raw.get("sep_events", []):
        events.append(
            SpaceWeatherEvent(
                event_id=sep.get("sepID", "SEP-SAMPLE"),
                event_type="SEP",
                begin_time=sep.get("eventTime", ""),
                peak_time=sep.get("eventTime"),
                class_or_intensity=sep.get("intensity", "SEP Proton Enhancement"),
                source_location=sep.get("sourceLocation", "Interplanetary Corridor"),
                note=sep.get("note", "Solar Energetic Particle event."),
            )
        )
    for cme in raw.get("cme_events", []):
        events.append(
            SpaceWeatherEvent(
                event_id=cme.get("activityID", "CME-SAMPLE"),
                event_type="CME",
                begin_time=cme.get("startTime", ""),
                peak_time=cme.get("startTime"),
                class_or_intensity=f"{cme.get('speed_km_s', 1000)} km/s ({cme.get('type', 'CME')})",
                source_location=cme.get("sourceLocation", "Solar Corona"),
                note=cme.get("note", "Coronal Mass Ejection alert."),
            )
        )
    for gst in raw.get("gst_events", []):
        events.append(
            SpaceWeatherEvent(
                event_id=gst.get("gstID", "GST-SAMPLE"),
                event_type="GST",
                begin_time=gst.get("startTime", ""),
                peak_time=gst.get("startTime"),
                class_or_intensity=gst.get("classType", f"Kp={gst.get('kpIndex', 6)}"),
                source_location="Magnetosphere / Corridor",
                note=gst.get("note", "Geomagnetic Storm alert."),
            )
        )

    flr_count = sum(1 for e in events if e.event_type == "FLR")
    sep_count = sum(1 for e in events if e.event_type == "SEP")
    cme_count = sum(1 for e in events if e.event_type == "CME")
    gst_count = sum(1 for e in events if e.event_type == "GST")
    alert_level: SeverityStatus = "CRITICAL" if sep_count > 0 else ("WARNING" if (flr_count + cme_count) > 0 else "NOMINAL")

    return SpaceWeatherSummary(
        source="curated_local_fallback",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        alert_level=alert_level,
        active_flare_count=flr_count,
        active_sep_count=sep_count,
        active_cme_count=cme_count,
        active_gst_count=gst_count,
        comms_degradation_risk="MODERATE_HF_SCINTILLATION" if sep_count > 0 else "NONE",
        recommended_dose_limit_msv_h=0.50,
        alara_instruction=(
            "Curated NASA DONKI FLR/SEP/CME/GST feed active: X1.9 Flare + S2 SEP proton event + 1340 km/s CME on record. "
            "Maintain ALARA shielding posture and verify personal BLE dosimeter threshold (<0.50 mSv/h)."
        ),
        events=events,
    )


async def fetch_nasa_space_weather() -> SpaceWeatherSummary:
    """Query NASA DONKI FLR, SEP, CME, and GST endpoints with automatic offline-first sample fallback."""
    api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=14)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    flr_url = f"https://api.nasa.gov/DONKI/FLR?startDate={start_str}&endDate={end_str}&api_key={api_key}"
    sep_url = f"https://api.nasa.gov/DONKI/SEP?startDate={start_str}&endDate={end_str}&api_key={api_key}"
    gst_url = f"https://api.nasa.gov/DONKI/GST?startDate={start_str}&endDate={end_str}&api_key={api_key}"

    try:
        async def _query():
            async with httpx.AsyncClient(timeout=2.5) as client:
                return await asyncio.gather(
                    client.get(flr_url),
                    client.get(sep_url),
                    client.get(gst_url),
                    return_exceptions=True,
                )

        flr_resp, sep_resp, gst_resp = await asyncio.wait_for(_query(), timeout=3.0)
        if isinstance(flr_resp, Exception) or isinstance(sep_resp, Exception):
            return load_sample_donki()
        if flr_resp.status_code != 200 or sep_resp.status_code != 200:
            return load_sample_donki()

        flr_data = flr_resp.json() if isinstance(flr_resp.json(), list) else []
        sep_data = sep_resp.json() if isinstance(sep_resp.json(), list) else []
        gst_data = (
            gst_resp.json()
            if (not isinstance(gst_resp, Exception) and gst_resp.status_code == 200 and isinstance(gst_resp.json(), list))
            else []
        )

        events: list[SpaceWeatherEvent] = []
        for item in flr_data[-4:]:
            events.append(
                SpaceWeatherEvent(
                    event_id=item.get("flrID", "FLR"),
                    event_type="FLR",
                    begin_time=item.get("beginTime", ""),
                    peak_time=item.get("peakTime"),
                    class_or_intensity=item.get("classType", "Unknown"),
                    source_location=item.get("sourceLocation") or "Solar Disk",
                    note=item.get("note") or f"NASA DONKI Solar Flare {item.get('classType', '')}",
                )
            )
        for item in sep_data[-3:]:
            instruments = ", ".join(inst.get("displayName", "") for inst in item.get("instruments", [])[:2])
            events.append(
                SpaceWeatherEvent(
                    event_id=item.get("sepID", "SEP"),
                    event_type="SEP",
                    begin_time=item.get("eventTime", ""),
                    peak_time=item.get("eventTime"),
                    class_or_intensity=instruments or "SEP Event",
                    source_location="Interplanetary Corridor",
                    note=item.get("note") or "Live NASA DONKI Solar Energetic Particle alert.",
                )
            )
        for item in gst_data[-2:]:
            events.append(
                SpaceWeatherEvent(
                    event_id=item.get("gstID", "GST"),
                    event_type="GST",
                    begin_time=item.get("startTime", ""),
                    peak_time=item.get("startTime"),
                    class_or_intensity="Geomagnetic Storm",
                    source_location="Magnetosphere",
                    note="Live NASA DONKI Geomagnetic Storm notification.",
                )
            )

        if not events:
            return SpaceWeatherSummary(
                source="live_nasa_donki",
                fetched_at=datetime.now(timezone.utc).isoformat(),
                alert_level="NOMINAL",
                active_flare_count=0,
                active_sep_count=0,
                active_cme_count=0,
                active_gst_count=0,
                comms_degradation_risk="NONE",
                recommended_dose_limit_msv_h=0.50,
                alara_instruction="Live NASA DONKI feed nominal: 0 SEP/Flare alerts in window. Continue standard ALARA monitoring.",
                events=[],
            )

        flr_count = sum(1 for e in events if e.event_type == "FLR")
        sep_count = sum(1 for e in events if e.event_type == "SEP")
        gst_count = sum(1 for e in events if e.event_type == "GST")
        has_x = any(e.class_or_intensity.upper().startswith("X") for e in events if e.event_type == "FLR")
        alert_level: SeverityStatus = (
            "CRITICAL" if (sep_count > 0 or has_x) else ("WARNING" if (flr_count + gst_count) > 0 else "NOMINAL")
        )

        return SpaceWeatherSummary(
            source="live_nasa_donki",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            alert_level=alert_level,
            active_flare_count=flr_count,
            active_sep_count=sep_count,
            active_cme_count=0,
            active_gst_count=gst_count,
            comms_degradation_risk="MODERATE_HF_SCINTILLATION" if (sep_count > 0 or has_x) else "NONE",
            recommended_dose_limit_msv_h=0.50,
            alara_instruction=(
                f"Live NASA DONKI Telemetry: {flr_count} Solar Flare(s), {sep_count} SEP Event(s), {gst_count} GST Event(s). "
                "Verify BLE dosimeter (<0.50 mSv/h) and storm-shelter readiness."
            ),
            events=events,
        )
    except Exception:
        return load_sample_donki()


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
