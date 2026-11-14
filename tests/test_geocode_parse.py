from app.data_collection.geocode import parse_nominatim

DATA = [
    {"place_id": 1, "display_name": "Coimbatore, Tamil Nadu, India", "lat": "11.0018", "lon": "76.9629"},
    {"place_id": 2, "display_name": "Coimbatore North, India", "lat": "11.05", "lon": "76.99"},
]


def test_many_matches_are_returned_with_float_coordinates():
    result = parse_nominatim(DATA)
    assert len(result) == 2
    assert result[0]["lat"] == 11.0018 and result[0]["id"] == "1"


def test_empty_response_means_no_match():
    assert parse_nominatim([]) == []


def test_item_without_coordinates_is_skipped():
    assert parse_nominatim([{"place_id": 3, "display_name": "X"}]) == []