from app.lead_evaluation.verifier import decide_status


def test_closed_is_rejected():
    assert decide_status({"closed": True, "sources": ["google", "osm"]})[0] == "rejected"


def test_no_sources_is_rejected():
    assert decide_status({"sources": []})[0] == "rejected"


def test_unknown_source_does_not_count():
    assert decide_status({"sources": ["manual"]})[0] == "rejected"


def test_conflict_beats_two_sources():  # rule order
    facts = {"sources": ["google", "osm"], "conflicts": ["address"]}
    assert decide_status(facts)[0] == "unverified"


def test_two_sources_is_verified():
    assert decide_status({"sources": ["google", "osm"]})[0] == "verified"


def test_website_counts_as_independent_source():
    assert decide_status({"sources": ["google", "website"]})[0] == "verified"


def test_one_source_is_partially_verified():
    assert decide_status({"sources": ["osm"]})[0] == "partially_verified"