"""Merge the same business found in different sources. Doubtful cases are only flagged."""
from rapidfuzz import fuzz

from app.data_processing.distance import haversine_km

NAME_MATCH = 90   # name similarity (0-100) for a confident match
NAME_DOUBT = 80   # name similarity for a doubtful match
MERGE_KM = 0.1    # closer than 100 m = same place
DOUBT_KM = 0.5    # closer than 500 m = maybe same place


def _distance_km(a, b):
    """Distance between two businesses, or None if any coordinate is missing."""
    if None in (a.get("lat"), a.get("lng"), b.get("lat"), b.get("lng")):
        return None
    return haversine_km(a["lat"], a["lng"], b["lat"], b["lng"])


def _phone_match(a, b):
    pa, pb = a.get("phone_norm"), b.get("phone_norm")
    return bool(pa) and pa == pb


def compare(a, b):
    """Returns 'same', 'doubt' or 'different'."""
    sim = fuzz.token_sort_ratio(a.get("name_norm") or "", b.get("name_norm") or "")
    dist = _distance_km(a, b)
    phone = _phone_match(a, b)

    if sim >= NAME_MATCH and (phone or (dist is not None and dist < MERGE_KM)):
        return "same"
    if sim >= NAME_DOUBT and (phone or (dist is not None and dist < DOUBT_KM)):
        return "doubt"
    return "different"


def _source_entry(b):
    return {"name": b.get("source"), "url": b.get("source_url")}


def _merge_into(base, other):
    """Fill missing fields of base from other, and add other's source."""
    for key, value in other.items():
        if base.get(key) in (None, "") and value not in (None, ""):
            base[key] = value
    # closed=False is not "missing", so the loop above never copies closed=True.
    # A permanent closure in any source must win.
    base["closed"] = bool(base.get("closed") or other.get("closed"))
    names = {s["name"] for s in base["sources"]}
    entry = _source_entry(other)
    if entry["name"] not in names:
        base["sources"].append(entry)
    base["found_in"] = len({s["name"] for s in base["sources"]})


def dedupe(businesses):
    """Returns a list of unique businesses. Each has sources, found_in, possible_duplicate."""
    result = []
    for b in businesses:
        new = {**b, "sources": [_source_entry(b)], "found_in": 1, "possible_duplicate": False}

        merged = False
        for existing in result:
            verdict = compare(existing, new)
            if verdict == "same":
                _merge_into(existing, new)
                merged = True
                break
            if verdict == "doubt":
                existing["possible_duplicate"] = True
                new["possible_duplicate"] = True
        if not merged:
            result.append(new)
    return result