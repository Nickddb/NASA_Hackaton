"""NASA JPL Horizons: range parsing, live -> cache -> curated fallback, and latency reaching the mission state."""

import asyncio
from unittest import mock

import httpx
import pytest

from app.engine import nasa_feeds

RESULT = """*******************************************************************************
 Date__(UT)__HR:MN, , ,            delta,     deldot,
$$SOE
 2026-Nov-15 22:00, , , 1.30803681638658,-14.7835286,
 2026-Nov-15 23:00, , , 1.30768105837279,-14.7850026,
$$EOE
"""


class _Resp:
    def __init__(self, status, payload):
        self.status_code, self._payload = status, payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(nasa_feeds, "HORIZONS_CACHE_PATH", tmp_path / "horizons_cache.json")
    monkeypatch.setattr(nasa_feeds, "_horizons_live", {})


async def _ok(self, url, params=None):
    return _Resp(200, {"result": RESULT})


async def _down(self, url, params=None):
    raise httpx.ConnectTimeout("offline")


def test_parse_range_takes_first_row():
    assert nasa_feeds.parse_horizons_range_au(RESULT) == pytest.approx(1.30803681638658)


def test_live_range_becomes_light_time():
    with mock.patch.object(httpx.AsyncClient, "get", _ok):
        asyncio.run(nasa_feeds.refresh_horizons(force=True))
    link = nasa_feeds.load_horizons("transit")
    assert link.source == "live_nasa_jpl_horizons" and link.fetch_status == "live"
    assert link.distance_km == pytest.approx(1.30803681638658 * nasa_feeds.AU_KM, rel=1e-6)
    assert link.one_way_light_time_seconds == pytest.approx(652.5, abs=0.5)
    assert link.round_trip_light_time_seconds == pytest.approx(2 * link.one_way_light_time_seconds, abs=0.2)


def test_orbital_station_stays_curated():
    with mock.patch.object(httpx.AsyncClient, "get", _ok):
        asyncio.run(nasa_feeds.refresh_horizons(force=True))
    assert nasa_feeds.load_horizons("orbital_station").source == "curated_local_fallback"


def test_offline_uses_last_good_range_then_sample():
    with mock.patch.object(httpx.AsyncClient, "get", _down):
        asyncio.run(nasa_feeds.refresh_horizons(force=True))
    assert nasa_feeds.load_horizons("transit").source == "curated_local_fallback"  # nothing cached yet

    with mock.patch.object(httpx.AsyncClient, "get", _ok):
        asyncio.run(nasa_feeds.refresh_horizons(force=True))
    with mock.patch.object(httpx.AsyncClient, "get", _down):
        asyncio.run(nasa_feeds.refresh_horizons(force=True))
    link = nasa_feeds.load_horizons("transit")
    assert link.source == "cached_nasa_jpl_horizons" and "ConnectTimeout" in link.fetch_status


def test_mission_state_latency_follows_horizons(tmp_path, monkeypatch):
    from app.state_manager import MissionStateManager

    sm = MissionStateManager()
    with mock.patch.object(httpx.AsyncClient, "get", _ok):
        asyncio.run(sm.refresh_horizons(force=True))
    transit = next(cid for cid, m in sm.crew_records.items() if m.environment_id == "transit")
    assert abs(sm.get_state(transit).one_way_latency_seconds - 652.5) <= 1
    assert abs(sm.compile_dossier(transit).one_way_latency_seconds - 652.5) <= 1
