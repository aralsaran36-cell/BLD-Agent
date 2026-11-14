from app.data_processing.dedupe import dedupe


def biz(name, source, lat=None, lng=None, phone=None, address=None):
    return {"name": name, "name_norm": name.lower(), "source": source,
            "lat": lat, "lng": lng, "phone_norm": phone, "address": address}


def test_same_name_close_by_is_merged():
    result = dedupe([
        biz("Vijay Hospital", "google", 11.0183, 76.9725),
        biz("Vijay Hospital", "osm", 11.0187, 76.9725),  # about 45 m
    ])
    assert len(result) == 1
    assert result[0]["found_in"] == 2


def test_same_name_far_apart_stays_separate():  # RISK 2
    result = dedupe([
        biz("City Hospital", "google", 11.0183, 76.9725, address="Gandhipuram"),
        biz("City Hospital", "osm", 11.3000, 76.9000, address="Ooty Road"),
    ])
    assert len(result) == 2
    assert not any(r["possible_duplicate"] for r in result)


def test_phone_match_merges_even_without_coordinates():
    result = dedupe([
        biz("Vijay Hospital", "google", phone="4222456789"),
        biz("Vijay Hospital", "osm", phone="4222456789"),
    ])
    assert len(result) == 1


def test_no_coordinates_no_phone_stays_separate():
    result = dedupe([biz("Vijay Hospital", "google"), biz("Vijay Hospital", "osm")])
    assert len(result) == 2


def test_doubtful_case_is_flagged_not_merged():
    result = dedupe([
        biz("Vijay Hospital", "google", 11.0183, 76.9725),
        biz("Vijay Hospital", "osm", 11.0213, 76.9725),  # about 330 m
    ])
    assert len(result) == 2
    assert all(r["possible_duplicate"] for r in result)


def test_merge_fills_missing_fields_and_keeps_both_sources():
    result = dedupe([
        biz("Vijay Hospital", "google", 11.0183, 76.9725),
        biz("Vijay Hospital", "osm", 11.0184, 76.9725, phone="4222456789"),
    ])
    assert result[0]["phone_norm"] == "4222456789"
    assert {s["name"] for s in result[0]["sources"]} == {"google", "osm"}

def _rec(source, closed):
    return {
        "name": "City Hospital", "name_norm": "city hospital",
        "lat": 11.0, "lng": 76.9, "phone_norm": None,
        "source": source, "source_url": f"http://{source}", "closed": closed,
    }


def test_closed_in_any_source_wins_after_merge():
    from app.data_processing.dedupe import dedupe
    result = dedupe([_rec("osm", False), _rec("google", True)])
    assert len(result) == 1
    assert result[0]["closed"] is True


def test_closed_wins_when_closed_record_comes_first():
    from app.data_processing.dedupe import dedupe
    result = dedupe([_rec("google", True), _rec("osm", False)])
    assert len(result) == 1
    assert result[0]["closed"] is True