from app.lead_evaluation.scoring import score_lead, category_terms

FULL = {"name": "Vijay Hospital", "category": "hospital", "distance_km": 0,
        "phone": "1", "email": "a@b.in", "website": "x.in", "address": "Gandhipuram"}


def test_perfect_lead_scores_100():
    assert score_lead(FULL, 10, "Hospitals")["score"] == 100


def test_edge_of_radius_loses_half_of_geo_points():
    lead = {**FULL, "distance_km": 10}
    assert score_lead(lead, 10, "Hospitals")["breakdown"]["geographic"] == 20


def test_wrong_category_gets_zero_category_points():
    lead = {**FULL, "name": "Smile Salon", "category": "salon"}
    assert score_lead(lead, 10, "Hospitals")["breakdown"]["category"] == 0


def test_missing_fields_lower_evidence_points():
    lead = {**FULL, "phone": None, "email": None}
    assert score_lead(lead, 10, "Hospitals")["breakdown"]["evidence"] == 15


def test_no_distance_gives_zero_geo():
    lead = {**FULL, "distance_km": None}
    assert score_lead(lead, 10, "Hospitals")["breakdown"]["geographic"] == 0


def test_category_terms_split_and_singular():
    assert category_terms("Hospitals, Clinics") == ["hospital", "clinic"]