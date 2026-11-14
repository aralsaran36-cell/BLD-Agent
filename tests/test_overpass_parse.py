from app.data_collection.overpass import tags_for_category, build_query, parse_overpass

DATA = {"elements": [
    {"type": "node", "id": 1, "lat": 11.0183, "lon": 76.9725,
     "tags": {"name": "Vijay Hospital", "amenity": "hospital", "phone": "+91 422 2456789",
              "website": "https://vijay.in", "addr:street": "Gandhipuram",
              "addr:city": "Coimbatore", "addr:postcode": "641012"}},
    {"type": "way", "id": 2, "center": {"lat": 11.0, "lon": 76.95},
     "tags": {"name": "City Clinic", "amenity": "clinic"}},
    {"type": "node", "id": 3, "lat": 11.0, "lon": 76.9, "tags": {"amenity": "hospital"}},
]}


def test_unnamed_places_are_skipped():
    assert len(parse_overpass(DATA, "2026-11-12")) == 2


def test_node_record_has_all_fields():
    r = parse_overpass(DATA, "2026-11-12")[0]
    assert r["address"] == "Gandhipuram, Coimbatore, 641012"
    assert r["source"] == "osm" and r["source_url"].endswith("node/1")
    assert r["retrieved_at"] == "2026-11-12"


def test_way_uses_center_and_missing_phone_is_none():
    r = parse_overpass(DATA, "2026-11-12")[1]
    assert r["lat"] == 11.0 and r["phone"] is None and r["address"] is None


def test_category_text_maps_to_tags():
    assert tags_for_category("Hospitals, Clinics") == [("amenity", "hospital"), ("amenity", "clinic")]


def test_unknown_category_gives_no_tags():
    assert tags_for_category("spaceship") == []


def test_query_has_radius_centre_and_tag():
    q = build_query([("amenity", "hospital")], 11.0168, 76.9558, 10)
    assert "around:10000,11.0168,76.9558" in q and '"amenity"="hospital"' in q

def test_supermarket_and_gym_map_to_osm_tags():
    assert ("shop", "supermarket") in tags_for_category("Supermarket")
    assert ("leisure", "fitness_centre") in tags_for_category("Gym")


def test_medical_shop_does_not_pull_hospitals():
    tags = tags_for_category("Medical shop")
    assert ("amenity", "pharmacy") in tags
    assert ("amenity", "hospital") not in tags