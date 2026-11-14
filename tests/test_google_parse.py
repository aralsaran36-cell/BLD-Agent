from app.data_collection.google_places import parse_google

DATA = {"places": [
    {"id": "ChIJabc", "displayName": {"text": "Vijay Hospital"},
     "formattedAddress": "12 Gandhipuram, Coimbatore 641012",
     "location": {"latitude": 11.0183, "longitude": 76.9725},
     "nationalPhoneNumber": "0422 2456789", "websiteUri": "https://vijay.in",
     "googleMapsUri": "https://maps.google.com/?cid=1", "businessStatus": "OPERATIONAL",
     "primaryTypeDisplayName": {"text": "Hospital"}},
    {"id": "x2", "displayName": {"text": "Old Clinic"},
     "location": {"latitude": 11.0, "longitude": 76.9}, "businessStatus": "CLOSED_PERMANENTLY"},
]}


def test_fields_are_mapped():
    r = parse_google(DATA, "2026-11-12")[0]
    assert r["source"] == "google" and r["name"] == "Vijay Hospital"
    assert r["lat"] == 11.0183 and r["phone"] == "0422 2456789" and r["closed"] is False


def test_permanently_closed_is_flagged():
    assert parse_google(DATA, "2026-11-12")[1]["closed"] is True


def test_empty_response_gives_no_records():
    assert parse_google({}, "2026-11-12") == []