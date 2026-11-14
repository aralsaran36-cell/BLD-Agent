from app.data_processing.normalize import (
    normalize_name, normalize_phone, normalize_domain, normalize_business,
)


def test_phone_with_country_code_and_dash():
    assert normalize_phone("+91 98765-43210") == "9876543210"


def test_phone_with_and_without_91_match():
    assert normalize_phone("098765 43210") == normalize_phone("+91 9876543210")


def test_missing_phone_is_none():
    assert normalize_phone(None) is None
    assert normalize_phone("") is None


def test_garbage_phone_is_none():
    assert normalize_phone("abc") is None


def test_name_case_and_spaces():
    assert normalize_name("  VIJAY   Hospital!! ") == "vijay hospital"


def test_domain_strips_scheme_www_path():
    assert normalize_domain("https://www.VijayHospital.in/contact") == "vijayhospital.in"
    assert normalize_domain("vijayhospital.in") == "vijayhospital.in"


def test_missing_website_is_none():
    assert normalize_domain(None) is None


def test_original_fields_are_kept():
    b = normalize_business({"name": "Vijay Hospital"})
    assert b["name"] == "Vijay Hospital"
    assert b["name_norm"] == "vijay hospital"