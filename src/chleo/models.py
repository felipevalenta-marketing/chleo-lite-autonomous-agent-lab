"""Validated data models for fictional properties and leads."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROPERTY_STATUSES: ClassVar[set[str]] = {
    "available",
    "under_offer",
    "reserved",
    "sold",
    "active",
}


def _trimmed_string(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected a string value.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("String values cannot be blank.")
    return cleaned


def _optional_trimmed_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("Expected a string value.")
    cleaned = value.strip()
    return cleaned or None


def _normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise TypeError("Expected a list of strings.")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError("Expected a list of strings.")
        cleaned = item.strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _classification_for_total(total: int) -> Literal["hot", "warm", "cold"]:
    if total >= 75:
        return "hot"
    if total >= 45:
        return "warm"
    return "cold"


class Property(BaseModel):
    """Fictional property listing used for retrieval and scoring."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    property_id: str
    title: str
    location: str
    property_type: str
    price_eur: int
    bedrooms: int
    bathrooms: int
    features: list[str] = Field(default_factory=list)
    status: str

    @field_validator("property_id", "title", "location", "property_type")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        return _trimmed_string(value)

    @field_validator("price_eur")
    @classmethod
    def _validate_price(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("price_eur must be greater than zero.")
        return value

    @field_validator("bedrooms", "bathrooms")
    @classmethod
    def _validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Bedrooms and bathrooms cannot be negative.")
        return value

    @field_validator("features", mode="before")
    @classmethod
    def _normalize_features(cls, value: object) -> list[str]:
        return _normalize_string_list(value)

    @field_validator("features")
    @classmethod
    def _validate_features(cls, value: list[str]) -> list[str]:
        return [_trimmed_string(item) for item in value]

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        normalized = _trimmed_string(value).lower()
        if normalized not in PROPERTY_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(PROPERTY_STATUSES)}."
            )
        return normalized


class LeadRequirements(BaseModel):
    """Fictional lead inquiry and extracted requirements."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lead_id: str | None = None
    inquiry: str
    budget_eur: int | None = None
    preferred_locations: list[str] = Field(default_factory=list)
    property_type: str | None = None
    purchase_timeline: str | None = None
    financing_status: str | None = None
    consent_to_contact: bool | None = None

    @field_validator("lead_id", "property_type", "purchase_timeline", "financing_status")
    @classmethod
    def _normalize_optional_text(cls, value: object) -> str | None:
        return _optional_trimmed_string(value)

    @field_validator("inquiry")
    @classmethod
    def _validate_inquiry(cls, value: str) -> str:
        return _trimmed_string(value)

    @field_validator("budget_eur")
    @classmethod
    def _validate_budget(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("budget_eur must be greater than zero when provided.")
        return value

    @field_validator("preferred_locations", mode="before")
    @classmethod
    def _normalize_locations(cls, value: object) -> list[str]:
        return _normalize_string_list(value)

    @field_validator("preferred_locations")
    @classmethod
    def _validate_locations(cls, value: list[str]) -> list[str]:
        return [_trimmed_string(item) for item in value]


class ScoreBreakdown(BaseModel):
    """Transparent scoring result for a lead."""

    model_config = ConfigDict(extra="forbid")

    budget_and_stock: int
    purchase_timeline: int
    financing_readiness: int
    requirements_clarity: int
    consent_and_contact: int
    total: int
    classification: Literal["hot", "warm", "cold"]
    reasons: list[str] = Field(default_factory=list)

    @field_validator(
        "budget_and_stock",
        "purchase_timeline",
        "financing_readiness",
        "requirements_clarity",
        "consent_and_contact",
        "total",
    )
    @classmethod
    def _validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Score values cannot be negative.")
        return value

    @field_validator("reasons", mode="before")
    @classmethod
    def _normalize_reasons(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("reasons must be a list of strings.")
        reasons: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("reasons must be a list of strings.")
            cleaned = item.strip()
            if cleaned:
                reasons.append(cleaned)
        return reasons

    @field_validator("reasons")
    @classmethod
    def _validate_reason_text(cls, value: list[str]) -> list[str]:
        return [_trimmed_string(item) for item in value]

    @model_validator(mode="after")
    def _validate_total_and_classification(self) -> "ScoreBreakdown":
        expected_total = (
            self.budget_and_stock
            + self.purchase_timeline
            + self.financing_readiness
            + self.requirements_clarity
            + self.consent_and_contact
        )
        if self.total != expected_total:
            raise ValueError("total must equal the sum of the category scores.")
        if not 0 <= self.total <= 100:
            raise ValueError("total must be between 0 and 100.")
        expected_classification = _classification_for_total(self.total)
        if self.classification != expected_classification:
            raise ValueError("classification does not match total.")
        return self
