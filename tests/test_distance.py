import pytest

from app.data_processing.distance import haversine_km, filter_by_radius

CENTER = (11.0168, 76.9558)  # Coimbatore


def test_same_point_is_zero():
    assert haversine_km(11.0, 76.9, 11.0, 76.9) == 0


def test_one_degree_of_latitude_is_about_111_km():
    assert 110 < haversine_km(0, 0, 1, 0) < 112


def test_distance_is_same_both_directions():
    a = haversine_km(11.0, 76.9, 11.5, 77.2)
    b = haversine_km(11.5, 77.2, 11.0, 76.9)
    assert a == pytest.approx(b)


def test_business_inside_radius_is_kept_with_distance():
    businesses = [{"name": "A", "lat": 11.0268, "lng": 76.9558}]
    kept = filter_by_radius(businesses, *CENTER, 10)
    assert len(kept) == 1
    assert kept[0]["distance_km"] == 1.11
    assert kept[0]["name"] == "A"


def test_business_outside_radius_is_removed():
    businesses = [{"name": "Far", "lat": 11.4668, "lng": 76.9558}]
    assert filter_by_radius(businesses, *CENTER, 10) == []


def test_business_without_coordinates_is_skipped():
    assert filter_by_radius([{"name": "X"}], *CENTER, 10) == []


def test_zero_coordinates_are_not_treated_as_missing():
    kept = filter_by_radius([{"name": "Equator", "lat": 0, "lng": 0}], 0, 0, 5)
    assert len(kept) == 1


def test_input_list_is_not_changed():
    businesses = [{"name": "A", "lat": 11.0268, "lng": 76.9558}]
    filter_by_radius(businesses, *CENTER, 10)
    assert "distance_km" not in businesses[0]


def test_mixed_list_keeps_only_valid_ones():
    businesses = [
        {"name": "A", "lat": 11.0268, "lng": 76.9558},
        {"name": "B", "lat": 11.4668, "lng": 76.9558},
        {"name": "No coordinates"},
    ]
    kept = filter_by_radius(businesses, *CENTER, 10)
    assert [b["name"] for b in kept] == ["A"]