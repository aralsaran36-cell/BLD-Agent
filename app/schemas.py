"""Input validation. Bad input gives a 422 automatically."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SearchIn(BaseModel):
    area: str = Field(min_length=1, max_length=100)
    radius_km: Literal[1, 3, 5, 7, 10]
    product: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    exclusions: list[str] = []

    @field_validator("area", "product", "category", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("exclusions")
    @classmethod
    def clean_exclusions(cls, words):
        return [w.strip() for w in words if w.strip()]


class AreaChoice(BaseModel):
    choice_id: str