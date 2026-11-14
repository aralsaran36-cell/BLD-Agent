"""Distance helpers: how far is each business from the search centre?"""
import math

EARTH_RADIUS_KM = 6371


def haversine_km(lat1, lng1, lat2, lng2):
    """Straight-line distance in km between two lat/lng points."""
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def filter_by_radius(businesses, center_lat, center_lng, radius_km):
    """Keep only businesses inside the radius. Adds distance_km to each one.
    Businesses with no coordinates are skipped (we never guess a location)."""
    kept = []
    for b in businesses:
        lat = b.get("lat")
        lng = b.get("lng")
        if lat is None or lng is None:
            continue
        d = haversine_km(center_lat, center_lng, lat, lng)
        if d <= radius_km:
            kept.append({**b, "distance_km": round(d, 2)})
    return kept


if __name__ == "__main__":
    print(haversine_km(0, 0, 1, 0))  # about 111.19
    print(haversine_km(0, 0, 0, 0))  # 0.0
    sample = [
        {"name": "A", "lat": 11.0268, "lng": 76.9558},  # about 1.1 km from centre
        {"name": "B", "lat": 11.4668, "lng": 76.9558},  # about 50 km from centre
        {"name": "No coordinates"},
    ]
    print(filter_by_radius(sample, 11.0168, 76.9558, 10))