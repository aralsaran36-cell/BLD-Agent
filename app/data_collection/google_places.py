"""Google Places (New) connector. Needs GOOGLE_PLACES_API_KEY in .env."""
import httpx

from app.config import GOOGLE_PLACES_URL, GOOGLE_PLACES_API_KEY, GOOGLE_MAX_PAGES, google_enabled
from app.data_collection import ConnectorError
from app.db import utc_now

# Ask only for the fields we use (cheaper and less data to store).
FIELD_MASK = ",".join([
    "nextPageToken",
    "places.id", "places.displayName", "places.formattedAddress", "places.location",
    "places.nationalPhoneNumber", "places.websiteUri", "places.googleMapsUri",
    "places.businessStatus", "places.primaryTypeDisplayName",
    "places.primaryType", "places.types",
])


def parse_google(data, retrieved_at):
    """Pure function. Google JSON -> common record shape."""
    records = []
    for p in data.get("places", []):
        name = (p.get("displayName") or {}).get("text")
        if not name:
            continue
        loc = p.get("location") or {}
        records.append({
            "source": "google",
            "source_id": p.get("id"),
            "name": name,
            "category": (p.get("primaryTypeDisplayName") or {}).get("text"),
            "primary_type": p.get("primaryType"),
            "types": p.get("types") or [],
            "address": p.get("formattedAddress"),
            "phone": p.get("nationalPhoneNumber"),
            "website": p.get("websiteUri"),
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "closed": p.get("businessStatus") == "CLOSED_PERMANENTLY",
            "source_url": p.get("googleMapsUri"),
            "retrieved_at": retrieved_at,
            "raw_json": None,  # storage rules not final: see docs/compliance.md
        })
    return records


AREA_FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location"


def parse_google_area(data):
    """Pure function. Google Text Search JSON -> [{'id', 'label', 'lat', 'lng'}]."""
    matches = []
    for p in data.get("places", []):
        loc = p.get("location") or {}
        name = (p.get("displayName") or {}).get("text")
        if not name or loc.get("latitude") is None or loc.get("longitude") is None:
            continue  # never guess
        address = p.get("formattedAddress")
        matches.append({
            "id": "g_" + str(p.get("id")),
            "label": f"{name}, {address}" if address else name,
            "lat": float(loc["latitude"]),
            "lng": float(loc["longitude"]),
        })
    return matches


async def geocode_via_google(client, area):
    """Area text -> centers using Google Text Search. Returns [] if key not set."""
    if not google_enabled():
        return []
    body = {"textQuery": area, "pageSize": 5, "regionCode": "IN"}
    headers = {"X-Goog-Api-Key": GOOGLE_PLACES_API_KEY, "X-Goog-FieldMask": AREA_FIELD_MASK}
    try:
        r = await client.post(GOOGLE_PLACES_URL, json=body, headers=headers)
        r.raise_for_status()
        return parse_google_area(r.json())
    except httpx.HTTPStatusError as e:
        raise ConnectorError(f"Google area lookup failed: HTTP {e.response.status_code}") from e
    except (httpx.HTTPError, ValueError) as e:
        raise ConnectorError(f"Google area lookup failed: {e}") from e

    
def google_type_for(category):
    """Map free text to a Google place type. Unknown -> no filter."""
    c = (category or "").lower()
    if "hospital" in c:
        return "hospital"
    return None


async def fetch_google(client, lat, lng, radius_km, category, area):
    if not google_enabled():
        raise ConnectorError("Google Places key not set")
    body = {
        "textQuery": f"{category} in {area}",
        "pageSize": 20,
        "locationBias": {"circle": {
            "center": {"latitude": lat, "longitude": lng},
            "radius": min(radius_km * 1000.0, 50000.0),
        }},
    }
    gtype = google_type_for(category)
    if gtype:
        body["includedType"] = gtype
        body["strictTypeFiltering"] = True
    headers = {"X-Goog-Api-Key": GOOGLE_PLACES_API_KEY, "X-Goog-FieldMask": FIELD_MASK}

    records, seen = [], set()
    for _ in range(GOOGLE_MAX_PAGES):
        try:
            r = await client.post(GOOGLE_PLACES_URL, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:200].replace("\n", " ")
            raise ConnectorError(f"Google Places failed: HTTP {e.response.status_code} {detail}") from e
        except (httpx.HTTPError, ValueError) as e:
            raise ConnectorError(f"Google Places failed: {e}") from e
        for rec in parse_google(data, utc_now()):
            if rec["source_id"] not in seen:
                seen.add(rec["source_id"])
                records.append(rec)
        token = data.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
    return records


if __name__ == "__main__":
    import asyncio
    from app.lead_evaluation.website import make_client

    async def main():
        async with make_client() as client:
            records = await fetch_google(client, 11.0168, 76.9558, 5, "Hospitals", "Coimbatore")
            print(len(records), "records")
            for r in records[:5]:
                print(r["name"], "|", r["address"], "|", r["phone"], "|", r["website"], "|", r["closed"])

    asyncio.run(main())