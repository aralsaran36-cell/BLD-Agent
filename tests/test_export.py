from app.output.export import leads_to_csv


def test_formula_is_neutralised():
    assert "'=cmd" in leads_to_csv([{"name": "=cmd"}])


def test_phone_plus_is_kept():
    assert "+91 422" in leads_to_csv([{"name": "A", "phone": "+91 422"}])


def test_missing_phone_is_not_found():
    assert "Not found" in leads_to_csv([{"name": "A"}])


def test_score_zero_is_kept():
    lines = leads_to_csv([{"name": "A", "score": 0}]).splitlines()
    assert ",0," in lines[1]


def test_source_urls_present():
    lead = {"name": "A", "sources": [{"name": "Google Places", "url": "https://x.com"}]}
    assert "https://x.com" in leads_to_csv([lead])


def test_reason_is_marked_inference():
    assert "(inference)" in leads_to_csv([{"name": "A", "reason": "Nearby"}])