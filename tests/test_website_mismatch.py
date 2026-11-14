from app.lead_evaluation.website import compare_page

BIZ = {"name_norm": "vijay hospital", "phone_norm": "4222456789",
       "address": "No.12, Gandhipuram, Coimbatore - 641012"}

GOOD = ("<html><body><h1>Vijay Hospital</h1><p>Call 0422 2456789 | Gandhipuram 641012 "
        "| info@VijayHospital.in</p></body></html>")


def test_correct_page_has_no_conflicts():
    result = compare_page(BIZ, GOOD)
    assert result["conflicts"] == [] and result["name_match"]


def test_wrong_website_is_detected():  # RISK 5
    page = "<html><body><h1>Green Valley School</h1></body></html>"
    assert "website name mismatch" in compare_page(BIZ, page)["conflicts"]


def test_wrong_address_is_detected():  # RISK 1
    page = "<h1>Vijay Hospital</h1><p>Ooty Road 643001</p>"
    assert "address mismatch" in compare_page(BIZ, page)["conflicts"]


def test_wrong_phone_is_detected():
    page = "<h1>Vijay Hospital</h1><p>Call 9999999999</p>"
    assert "phone mismatch" in compare_page(BIZ, page)["conflicts"]


def test_page_without_phone_is_not_a_conflict():
    assert compare_page(BIZ, "<h1>Vijay Hospital</h1>")["conflicts"] == []


def test_emails_are_collected_lowercase():
    assert compare_page(BIZ, GOOD)["emails"] == ["info@vijayhospital.in"]