"""Area text -> lat/lng.
Order: Nominatim exact -> spelling variants -> Google -> nearby bigger place.
A fallback is never silent: the caller always gets a note."""
import asyncio
import time

import httpx

from app.config import NOMINATIM_URL, NOMINATIM_MIN_INTERVAL
from app.data_collection import ConnectorError
from app.data_collection.google_places import geocode_via_google

_last_call = 0.0
_lock = asyncio.Lock()
_cache = {}


def parse_nominatim(data):
    """Pure function. Nominatim JSON -> [{'id', 'label', 'lat', 'lng'}]."""
    matches = []
    for item in data or []:
        try:
            matches.append({
                "id": str(item["place_id"]),
                "label": item["display_name"],
                "lat": float(item["lat"]),
                "lng": float(item["lon"]),
            })
        except (KeyError, ValueError, TypeError):
            continue  # skip broken items, never guess
    return matches


def dedupe_matches(matches):
    """Pure function. Same id or same coordinates (4 decimals) = one match."""
    seen_ids, seen_pos, out = set(), set(), []
    for m in matches:
        pos = (round(m["lat"], 4), round(m["lng"], 4))
        if m["id"] in seen_ids or pos in seen_pos:
            continue
        seen_ids.add(m["id"])
        seen_pos.add(pos)
        out.append(m)
    return out


def spelling_variants(text):
    """Pure function. Common Tamil spelling differences (max 2)."""
    t = text.lower().strip()
    out = []
    for old, new in (("rr", "r"), ("tt", "t"), ("tty", "tti"), ("tti", "tty")):
        v = t.replace(old, new)
        if old in t and v != t and v not in out:
            out.append(v)
    return out[:2]


def parent_queries(text):
    """Pure function. 'errapatti dharmapuri' -> ['dharmapuri'] (max 2)."""
    if "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        parents = [", ".join(parts[i:]) for i in range(1, len(parts))]
    else:
        tokens = text.split()
        parents = [" ".join(tokens[i:]) for i in range(1, len(tokens))]
    return parents[:2]


def note_for(area, query, kind):
    """Pure function. Message for the user when a fallback was used."""
    if kind == "variant":
        return f"'{area}' not found. Showing results for the spelling '{query}'."
    if kind == "google":
        return (f"'{area}' not found on OpenStreetMap. Using the Google location. "
                f"Check the place before trusting the results.")
    if kind == "parent":
        return (f"'{area}' not found on the map. Using '{query}' as the center instead. "
                f"Check the location before trusting the results.")
    return None


async def _respect_rate_limit():
    global _last_call
    async with _lock:
        wait = NOMINATIM_MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call = time.monotonic()


async def _search(client, query):
    """One Nominatim query, 1 retry. Raises ConnectorError if both fail."""
    last_error = None
    for _ in range(2):
        await _respect_rate_limit()
        try:
            r = await client.get(NOMINATIM_URL, params={
                "q": query, "format": "jsonv2", "limit": 5, "countrycodes": "in"})
            r.raise_for_status()
            return parse_nominatim(r.json())
        except (httpx.HTTPError, ValueError) as e:
            last_error = e
    raise ConnectorError(f"Nominatim failed: {last_error}") from last_error


async def geocode_with_note(client, area):
    """Returns (matches, note). note is None unless a fallback was used.
    Raises ConnectorError only if Nominatim is down AND nothing else worked."""
    area = area.strip()
    key = area.lower()
    if key in _cache:
        return _cache[key]

    nominatim_error = None

    async def nominatim(query):
        nonlocal nominatim_error
        try:
            return dedupe_matches(await _search(client, query))
        except ConnectorError as e:
            nominatim_error = e
            return []

    def done(matches, kind, query):
        result = (matches, note_for(area, query, kind))
        _cache[key] = result  # cache only real results
        return result

    # 1. exact, 2. spelling variants (Nominatim)
    matches = await nominatim(area)
    if matches:
        return done(matches, "exact", area)
    for variant in spelling_variants(area):
        matches = await nominatim(variant)
        if matches:
            return done(matches, "variant", variant)

    # 3. Google area search
    try:
        matches = dedupe_matches(await geocode_via_google(client, area))
    except ConnectorError:
        matches = []
    if matches:
        return done(matches, "google", area)

    # 4. nearby bigger place (last, with a clear note)
    for parent in parent_queries(area):
        matches = await nominatim(parent)
        if matches:
            return done(matches, "parent", parent)

    if nominatim_error:
        raise nominatim_error
    return [], None


async def geocode(client, area):
    """Old interface: matches only."""
    matches, _ = await geocode_with_note(client, area)
    return matches


if __name__ == "__main__":
    from app.lead_evaluation.website import make_client

    async def main():
        async with make_client() as client:
            matches, note = await geocode_with_note(client, "errapatti dharmapuri")
            print("NOTE:", note)
            for m in matches:
                print(m)

    asyncio.run(main())