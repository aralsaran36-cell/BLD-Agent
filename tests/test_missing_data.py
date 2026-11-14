"""Risk 3: missing data is never invented. Missing stays None, and shows 'Not found'."""
import asyncio

from app.data_collection.overpass import parse_overpass
from app.data_processing.distance import filter_by_radius
from app.data_processing.normalize import normalize_business
from app.lead_evaluation.reason import build_reason
from app.lead_evaluation.scoring import score_lead
from app.lead_evaluation.verifier import decide_status
from app.lead_evaluation.website import check_website
from app.output.export import lead_to_row, COLUMNS
from app import pipeline


def test_normalize_empty_record_stays_empty():
    result = normalize_business({"name": "A Hospital"})
    assert result["phone_norm"] is None
    assert result["domain"] is None
    assert result["address_norm"] == ""


def test_osm_element_without_tags_keeps_none():
    data = {"elements": [{"type": "node", "id": 1, "lat": 11.0, "lon": 76.9,
                          "tags": {"name": "A Hospital"}}]}
    rec = parse_overpass(data, "t")[0]
    assert rec["phone"] is None
    assert rec["website"] is None
    assert rec["address"] is None
    assert rec["category"] is None


def test_business_without_lat_only_is_skipped():
    kept = filter_by_radius([{"name": "A", "lng": 76.9}], 11.0, 76.9, 10)
    assert kept == []


def test_score_of_empty_lead_is_zero():
    result = score_lead({"name": "X"}, 10, "Hospitals")
    assert result["score"] == 0
    assert result["breakdown"] == {"geographic": 0, "category": 0, "evidence": 0}


def test_reason_for_empty_lead_lists_missing_and_invents_nothing():
    text = build_reason({"name": "A"}, {"category": 0}, "Hospitals")
    assert "Category not listed." in text
    assert "Not found: phone, email, website." in text
    assert "Located" not in text
    assert "Found in" not in text


def test_csv_row_shows_not_found_for_every_missing_field():
    row = dict(zip(COLUMNS, lead_to_row({"name": "A Hospital"})))
    for column in ("category", "address", "phone", "email", "website",
                   "distance_km", "sources", "source_urls", "maps_url"):
        assert row[column] == "Not found", column


def test_no_website_means_no_network_call():
    result = asyncio.run(check_website({"name": "A"}, None))
    assert result["state"] == "no_website"
    assert result["emails"] == []


def test_no_source_is_rejected_not_guessed():
    status, rule = decide_status({"closed": False, "sources": [], "conflicts": []})
    assert status == "rejected"


def test_evidence_rows_only_for_facts_that_exist():
    lead = {"name": "A Hospital", "sources": [{"name": "osm", "url": "http://x"}]}
    rows = pipeline._evidence_rows(lead)
    assert [r[0] for r in rows] == ["name"]