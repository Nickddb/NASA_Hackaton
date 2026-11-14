from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.models.schemas import SeverityStatus, SpaceWeatherEvent, SpaceWeatherSummary

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_sample_donki() -> SpaceWeatherSummary:
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
                source_location=flr.get("sourceLocation", "Unknown"),
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
                source_location=sep.get("sourceLocation", "Solar Disk"),
                note=sep.get("note", "Solar Energetic Particle event."),
            )
        )

    flr_count = sum(1 for e in events if e.event_type == "FLR")
    sep_count = sum(1 for e in events if e.event_type == "SEP")
    alert_level: SeverityStatus = "CRITICAL" if sep_count > 0 else ("WARNING" if flr_count > 0 else "NOMINAL")

    return SpaceWeatherSummary(
        source="curated_local_fallback",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        alert_level=alert_level,
        active_flare_count=flr_count,
        active_sep_count=sep_count,
        recommended_dose_limit_msv_h=0.50,
        alara_instruction=(
            "Curated NASA DONKI FLR/SEP feed active: X1.9 Flare + S2 SEP proton event on record. "
            "Maintain ALARA shielding posture and verify personal BLE dosimeter threshold (<0.50 mSv/h)."
        ),
        events=events,
    )


async def fetch_nasa_space_weather() -> SpaceWeatherSummary:
    """Query NASA DONKI FLR and SEP endpoints with automatic offline-first sample fallback."""
    api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=14)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    flr_url = f"https://api.nasa.gov/DONKI/FLR?startDate={start_str}&endDate={end_str}&api_key={api_key}"
    sep_url = f"https://api.nasa.gov/DONKI/SEP?startDate={start_str}&endDate={end_str}&api_key={api_key}"

    try:
        import asyncio

        async def _query():
            async with httpx.AsyncClient(timeout=2.5) as client:
                return await asyncio.gather(client.get(flr_url), client.get(sep_url))

        flr_resp, sep_resp = await asyncio.wait_for(_query(), timeout=3.0)

        if flr_resp.status_code != 200 or sep_resp.status_code != 200:
            return _load_sample_donki()

        flr_data = flr_resp.json() if isinstance(flr_resp.json(), list) else []
        sep_data = sep_resp.json() if isinstance(sep_resp.json(), list) else []

        events: list[SpaceWeatherEvent] = []
        for item in flr_data[-5:]:
            events.append(
                SpaceWeatherEvent(
                    event_id=item.get("flrID", "FLR"),
                    event_type="FLR",
                    begin_time=item.get("beginTime", ""),
                    peak_time=item.get("peakTime"),
                    class_or_intensity=item.get("classType", "Unknown"),
                    source_location=item.get("sourceLocation", "Solar Disk") or "Solar Disk",
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

        if not events:
            # No events in the last 14 days from live NASA DONKI — still return live status cleanly
            return SpaceWeatherSummary(
                source="live_nasa_donki",
                fetched_at=datetime.now(timezone.utc).isoformat(),
                alert_level="NOMINAL",
                active_flare_count=0,
                active_sep_count=0,
                recommended_dose_limit_msv_h=0.50,
                alara_instruction="Live NASA DONKI telemetry nominal: 0 FLR/SEP events detected in past 14 days.",
                events=[],
            )

        has_x_flare = any(e.event_type == "FLR" and e.class_or_intensity.startswith("X") for e in events)
        sep_count = sum(1 for e in events if e.event_type == "SEP")
        flr_count = sum(1 for e in events if e.event_type == "FLR")

        alert_level: SeverityStatus = "CRITICAL" if (sep_count > 0 or has_x_flare) else "WARNING"
        instruction = (
            "Live NASA DONKI alert: High-energy flare or SEP detected. Keep crew near storm shelter and enforce ALARA."
            if alert_level == "CRITICAL"
            else "Live NASA DONKI flare activity detected. Continue passive BLE dosimetry and monitor proton flux."
        )

        return SpaceWeatherSummary(
            source="live_nasa_donki",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            alert_level=alert_level,
            active_flare_count=flr_count,
            active_sep_count=sep_count,
            recommended_dose_limit_msv_h=0.50,
            alara_instruction=instruction,
            events=list(reversed(events)),
        )
    except Exception:
        return _load_sample_donki()
