from app.data_processing.exclusions import apply_exclusions, summarize_removed

SAMPLE = [
    {"name": "Vijay Hospital"},
    {"name": "Smile Dental Clinic"},
    {"name": "City Pharmacy"},
]


def test_matching_businesses_are_removed():
    kept, removed = apply_exclusions(SAMPLE, ["dental", "pharmacy"])
    assert [b["name"] for b in kept] == ["Vijay Hospital"]
    assert len(removed) == 2


def test_case_does_not_matter():
    kept, removed = apply_exclusions(SAMPLE, ["DENTAL"])
    assert len(removed) == 1


def test_removed_item_has_reason():
    _, removed = apply_exclusions(SAMPLE, ["dental"])
    assert removed[0]["excluded_because"] == "dental"


def test_empty_words_keeps_everything():
    kept, removed = apply_exclusions(SAMPLE, [])
    assert len(kept) == 3 and removed == []


def test_summary_text():
    _, removed = apply_exclusions(SAMPLE, ["dental", "pharmacy"])
    assert summarize_removed(removed) == "2 removed (dental: 1, pharmacy: 1)"