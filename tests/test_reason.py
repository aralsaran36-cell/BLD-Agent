from app.lead_evaluation.reason import build_reason


def test_missing_fields_are_listed_as_not_found():
    lead = {"category": "hospital", "distance_km": 2.4, "phone": None, "email": None,
            "website": "x.in", "sources": [{"name": "google"}]}
    text = build_reason(lead, {"category": 30}, "Hospitals")
    assert "Not found: phone, email." in text


def test_matching_category_is_mentioned():
    text = build_reason({"category": "hospital"}, {"category": 30}, "Hospitals")
    assert "matches your category" in text


def test_no_sources_means_no_source_sentence():
    assert "Found in" not in build_reason({}, {}, "Hospitals")