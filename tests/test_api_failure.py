import asyncio

from app import pipeline
from app.data_collection import ConnectorError

SEARCH = {"radius_km": 10, "category": "Hospitals", "area": "Coimbatore"}


async def osm_ok(*args, **kwargs):
    return [{"name": "A", "source": "osm"}]


async def down(*args, **kwargs):
    raise ConnectorError("timeout")


def test_one_source_down_search_continues(monkeypatch):  # RISK 4
    monkeypatch.setattr(pipeline, "fetch_overpass", osm_ok)
    monkeypatch.setattr(pipeline, "fetch_google", down)
    monkeypatch.setattr(pipeline, "google_enabled", lambda: True)
    records, notes, worked = asyncio.run(pipeline.collect_sources(None, 11.0, 76.9, SEARCH))
    assert worked == 1 and len(records) == 1
    assert any("google unavailable" in n for n in notes)


def test_both_sources_down_is_detected(monkeypatch):
    monkeypatch.setattr(pipeline, "fetch_overpass", down)
    monkeypatch.setattr(pipeline, "fetch_google", down)
    monkeypatch.setattr(pipeline, "google_enabled", lambda: True)
    records, notes, worked = asyncio.run(pipeline.collect_sources(None, 11.0, 76.9, SEARCH))
    assert worked == 0 and records == []