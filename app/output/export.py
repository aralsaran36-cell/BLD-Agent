"""Leads -> CSV text, with source URLs and status."""
import csv
import io

COLUMNS = ["name", "category", "address", "phone", "email", "website", "distance_km",
           "status", "score", "last_verified", "possible_duplicate", "reason",
           "sources", "source_urls", "maps_url"]


def _safe(value, column):
    """Missing -> 'Not found'. Text that Excel could run as a formula gets a leading quote."""
    if value is None or value == "":
        return "Not found"
    text = str(value)
    risky = "=@\t\r" if column == "phone" else "=+-@\t\r"
    return "'" + text if text[0] in risky else text


def _reason_text(reason):
    """Reason is an inference, so the CSV must say so (same as the UI card)."""
    if not reason:
        return None
    return reason if reason.endswith("(inference)") else reason + " (inference)"


def lead_to_row(lead):
    sources = lead.get("sources") or []
    maps_url = None
    if lead.get("lat") is not None and lead.get("lng") is not None:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lead['lat']},{lead['lng']}"
    values = {
        **lead,
        "possible_duplicate": "yes" if lead.get("possible_duplicate") else "no",
        "reason": _reason_text(lead.get("reason")),
        "sources": "; ".join(s["name"] for s in sources if s.get("name")),
        "source_urls": "; ".join(s["url"] for s in sources if s.get("url")),
        "maps_url": maps_url,
    }
    return [_safe(values.get(c), c) for c in COLUMNS]


def leads_to_csv(leads):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    for lead in leads:
        writer.writerow(lead_to_row(lead))
    return buffer.getvalue()


if __name__ == "__main__":
    demo = [{
        "name": "Vijay Hospital", "category": "Hospital", "address": "Gandhipuram, Coimbatore",
        "phone": "+91 422 245 6789", "website": "https://www.vijayhospital.in",
        "distance_km": 2.4, "status": "verified", "score": 95, "last_verified": "2026-11-11",
        "reason": "Matches your product and is located nearby.",
        "lat": 11.0183, "lng": 76.9725,
        "sources": [{"name": "Google Places", "url": "https://maps.google.com/?cid=1"},
                    {"name": "OSM", "url": "https://www.openstreetmap.org/node/1"}],
    }]
    print(leads_to_csv(demo))