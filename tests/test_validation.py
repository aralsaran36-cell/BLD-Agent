import pytest
from pydantic import ValidationError

from app.schemas import SearchIn

OK = {"area": "Coimbatore", "radius_km": 10, "product": "HMS", "category": "Hospitals"}


def test_valid_input_passes():
    assert SearchIn(**OK).area == "Coimbatore"


def test_radius_abc_is_rejected():
    with pytest.raises(ValidationError):
        SearchIn(**{**OK, "radius_km": "abc"})


def test_radius_not_in_list_is_rejected():
    with pytest.raises(ValidationError):
        SearchIn(**{**OK, "radius_km": 12})

                                                                    
def test_blank_area_is_rejected():
    with pytest.raises(ValidationError):
        SearchIn(**{**OK, "area": "   "})


def test_exclusions_are_cleaned():
    assert SearchIn(**OK, exclusions=["dental ", " "]).exclusions == ["dental"]