"""Deterministic lead-scoring logic for the Chleo Lite prototype."""

from __future__ import annotations

import re
from typing import Iterable

from .models import LeadRequirements, Property, ScoreBreakdown

ACTIVE_PROPERTY_STATUSES = {"available", "active"}


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def _normalised_tokens(value: str | None) -> str:
    return re.sub(r"[\s\-_/,]+", " ", _normalize_text(value))


def score_budget_and_stock(
    lead: LeadRequirements, properties: Iterable[Property]
) -> int:
    if lead.budget_eur is None:
        return 0

    compatible_active_property = any(
        property_.status.lower() in ACTIVE_PROPERTY_STATUSES
        and property_.price_eur <= lead.budget_eur
        for property_ in properties
    )
    return 25 if compatible_active_property else 10


def score_purchase_timeline(lead: LeadRequirements) -> int:
    timeline = _normalised_tokens(lead.purchase_timeline)
    if not timeline:
        return 0

    if re.search(r"\b(immediate|asap|within 3 months?|1 3 months?|0 3 months?)\b", timeline):
        return 25
    if re.search(r"\b(3 6 months?|within 3 6 months?|three to six months?)\b", timeline):
        return 18
    if re.search(r"\b(6 12 months?|within 6 12 months?|six to twelve months?)\b", timeline):
        return 10
    if re.search(
        r"\b(more than 12 months?|over 12 months?|researching|just looking|later|more than a year)\b",
        timeline,
    ):
        return 5
    return 0


def score_financing_readiness(lead: LeadRequirements) -> int:
    financing = _normalised_tokens(lead.financing_status)
    if not financing:
        return 0

    if re.search(r"\b(cash buyer|cash buyer|cash)\b", financing):
        return 20
    if re.search(r"\b(mortgage pre approved|pre approved|pre approval|preapproved|mortgage preapproved)\b", financing):
        return 20
    if re.search(r"\b(financing in progress|mortgage in progress|in progress)\b", financing):
        return 12
    if re.search(r"\b(financing required|not started|need financing|mortgage not started)\b", financing):
        return 8
    return 0


def score_requirements_clarity(lead: LeadRequirements) -> int:
    score = 0
    if lead.preferred_locations:
        score += 10
    if lead.property_type:
        score += 10
    return score


def score_consent_and_contact(lead: LeadRequirements) -> int:
    return 10 if lead.consent_to_contact is True else 0


def classify_score(total: int) -> str:
    if total >= 75:
        return "hot"
    if total >= 45:
        return "warm"
    return "cold"


def score_lead(
    lead: LeadRequirements, properties: Iterable[Property]
) -> ScoreBreakdown:
    budget_and_stock = score_budget_and_stock(lead, properties)
    purchase_timeline = score_purchase_timeline(lead)
    financing_readiness = score_financing_readiness(lead)
    requirements_clarity = score_requirements_clarity(lead)
    consent_and_contact = score_consent_and_contact(lead)
    total = (
        budget_and_stock
        + purchase_timeline
        + financing_readiness
        + requirements_clarity
        + consent_and_contact
    )

    reasons = [
        _budget_reason(lead, budget_and_stock, properties),
        _timeline_reason(lead, purchase_timeline),
        _financing_reason(lead, financing_readiness),
        _clarity_reason(lead, requirements_clarity),
        _consent_reason(lead, consent_and_contact),
    ]

    return ScoreBreakdown(
        budget_and_stock=budget_and_stock,
        purchase_timeline=purchase_timeline,
        financing_readiness=financing_readiness,
        requirements_clarity=requirements_clarity,
        consent_and_contact=consent_and_contact,
        total=total,
        classification=classify_score(total),
        reasons=reasons,
    )


def _budget_reason(
    lead: LeadRequirements, score: int, properties: Iterable[Property]
) -> str:
    if lead.budget_eur is None:
        return "Budget is missing, so stock compatibility gets 0 points."
    if score == 25:
        return "Budget fits at least one active property, so stock compatibility gets 25 points."
    return "Budget is present, but no active property is within budget, so stock compatibility gets 10 points."


def _timeline_reason(lead: LeadRequirements, score: int) -> str:
    if score == 25:
        return "Purchase timeline looks immediate, so it gets 25 points."
    if score == 18:
        return "Purchase timeline suggests a 3-6 month window, so it gets 18 points."
    if score == 10:
        return "Purchase timeline suggests a 6-12 month window, so it gets 10 points."
    if score == 5:
        return "Purchase timeline is long term or exploratory, so it gets 5 points."
    return "Purchase timeline is missing or unrecognized, so it gets 0 points."


def _financing_reason(lead: LeadRequirements, score: int) -> str:
    if score == 20:
        return "Financing looks ready, so it gets 20 points."
    if score == 12:
        return "Financing is in progress, so it gets 12 points."
    if score == 8:
        return "Financing is required but not started, so it gets 8 points."
    return "Financing status is missing or unclear, so it gets 0 points."


def _clarity_reason(lead: LeadRequirements, score: int) -> str:
    if score == 20:
        return "Location and property type are both clear, so they get 20 points."
    if score == 10:
        return "Only one requirement is clear, so clarity gets 10 points."
    return "Location and property type are missing, so clarity gets 0 points."


def _consent_reason(lead: LeadRequirements, score: int) -> str:
    if score == 10:
        return "Consent to contact is explicit, so it gets 10 points."
    return "Consent is missing or false, so it gets 0 points."
