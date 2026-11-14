"""OpenStreetMap (Overpass) connector. No API key. © OpenStreetMap contributors."""
import asyncio
import json

import httpx

from app.config import OVERPASS_URL
from app.data_collection import ConnectorError
from app.db import utc_now

CATEGORY_TAGS = {
    # health
    "hospital": [("amenity", "hospital")],
    "clinic": [("amenity", "clinic")],
    "doctor": [("amenity", "doctors")],
    "medical": [("amenity", "hospital"), ("amenity", "clinic"), ("amenity", "doctors")],
    "dental": [("amenity", "dentist")],
    "dentist": [("amenity", "dentist")],
    "pharmacy": [("amenity", "pharmacy")],
    "medical shop": [("amenity", "pharmacy")],
    "lab": [("healthcare", "laboratory")],
    "diagnostic": [("healthcare", "laboratory")],
    "veterinary": [("amenity", "veterinary")],
    # education
    "school": [("amenity", "school")],
    "kindergarten": [("amenity", "kindergarten")],
    "college": [("amenity", "college")],
    "university": [("amenity", "university")],
    "tuition": [("amenity", "prep_school")],
    "coaching": [("amenity", "prep_school")],
    # food and stay
    "restaurant": [("amenity", "restaurant")],
    "cafe": [("amenity", "cafe")],
    "fast food": [("amenity", "fast_food")],
    "bakery": [("shop", "bakery")],
    "sweet": [("shop", "confectionery")],
    "hotel": [("tourism", "hotel")],
    "lodge": [("tourism", "guest_house")],
    "hostel": [("tourism", "hostel")],
    # shops
    "supermarket": [("shop", "supermarket")],
    "grocery": [("shop", "convenience"), ("shop", "supermarket")],
    "mall": [("shop", "mall")],
    "textile": [("shop", "clothes"), ("shop", "fabric")],
    "clothes": [("shop", "clothes")],
    "jewellery": [("shop", "jewelry")],
    "jewelry": [("shop", "jewelry")],
    "electronics": [("shop", "electronics")],
    "mobile": [("shop", "mobile_phone")],
    "hardware": [("shop", "hardware")],
    "furniture": [("shop", "furniture")],
    "stationery": [("shop", "stationery")],
    # services
    "bank": [("amenity", "bank")],
    "salon": [("shop", "hairdresser"), ("shop", "beauty")],
    "gym": [("leisure", "fitness_centre"), ("leisure", "sports_centre"), ("sport", "fitness")],
    "petrol": [("amenity", "fuel")],
    "fuel": [("amenity", "fuel")],
    "garage": [("shop", "car_repair")],
    "car showroom": [("shop", "car")],
    "bike showroom": [("shop", "motorcycle")],
    "travel agency": [("shop", "travel_agency")],
    "real estate": [("office", "estate_agent")],
    "insurance": [("office", "insurance")],
    "wedding hall": [("amenity", "events_venue")],
    "cinema": [("amenity", "cinema")],
    "factory": [("man_made", "works")],
}


def tags_for_category(text):
    """'Hospitals, Clinics' -> [('amenity','hospital'), ('amenity','clinic')]
    If one keyword is part of a longer matching keyword ('medical' inside
    'medical shop'), only the longer one is used."""
    tags = []
    for term in text.lower().split(","):
        term = term.strip()
        matches = [k for k in CATEGORY_TAGS if k in term]
        matches = [k for k in matches
                   if not any(k != other and k in other for other in matches)]
        for keyword in matches:
            for pair in CATEGORY_TAGS[keyword]:
                if pair not in tags:
                    tags.append(pair)
    return tags


def build_query(tags, lat, lng, radius_km):
    meters = int(radius_km * 1000)
    lines = [f'  nwr["{k}"="{v}"](around:{meters},{lat},{lng});' for k, v in tags]
    return "[out:json][timeout:25];\n(\n" + "\n".join(lines) + "\n);\nout center tags;"


def _address(tags):
    street = " ".join(p for p in [tags.get("addr:housenumber"), tags.get("addr:street")] if p)
    parts = [street, tags.get("addr:suburb"), tags.get("addr:city"), tags.get("addr:postcode")]
    text = ", ".join(p for p in parts if p)
    return text or None


def parse_overpass(data, retrieved_at):
    """Pure function. Overpass JSON -> common record shape. Unnamed places are skipped."""
    records = []
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        center = el.get("center") or {}
        el_type, el_id = el.get("type"), el.get("id")
        records.append({
            "source": "osm",
            "source_id": f"{el_type}/{el_id}",
            "name": name,
            "category": (tags.get("amenity") or tags.get("healthcare")
                         or tags.get("tourism") or tags.get("shop")
                         or tags.get("leisure") or tags.get("office")
                         or tags.get("man_made")),
            "address": _address(tags),
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "email": tags.get("email") or tags.get("contact:email"),
            "website": tags.get("website") or tags.get("contact:website"),
            "lat": el.get("lat", center.get("lat")),
            "lng": el.get("lon", center.get("lon")),
            "closed": False,
            "source_url": f"https://www.openstreetmap.org/{el_type}/{el_id}",
            "retrieved_at": retrieved_at,
            "raw_json": json.dumps(el),
        })
    return records


async def fetch_overpass(client, lat, lng, radius_km, category):
    """Raises ConnectorError on any failure. The pipeline decides what to do."""
    tags = tags_for_category(category)
    if not tags:
        raise ConnectorError(f"OSM: category '{category}' is not mapped to OSM tags yet")
    query = build_query(tags, lat, lng, radius_km)
    try:
        r = await client.post(OVERPASS_URL, data={"data": query}, timeout=60)
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise ConnectorError(f"Overpass failed: {e}") from e
    return parse_overpass(data, utc_now())


if __name__ == "__main__":
    from app.lead_evaluation.website import make_client

    async def main():
        async with make_client() as client:
            records = await fetch_overpass(client, 11.0168, 76.9558, 5, "Hospitals")
            print(len(records), "records")
            for r in records[:5]:
                print(r["name"], "|", r["address"], "|", r["phone"], "|", r["email"])

    asyncio.run(main())