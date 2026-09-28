"""Offline workflow nodes for the Chleo Lite lead-qualification fallback.

LangGraph is the planned production orchestrator, but this phase uses a local
deterministic state machine because the dependency is unavailable offline.
"""

from __future__ import annotations

import re
from typing import Sequence

from .models import LeadRequirements, Property, WorkflowState
from .rag import load_default_catalogue, normalize_text, retrieve_properties, tokenize_text
from .scoring import score_lead

MISSING_FIELD_ORDER = [
    "budget_eur",
    "preferred_locations",
    "property_type",
    "purchase_timeline",
    "financing_status",
    "consent_to_contact",
]

FOLLOW_UP_QUESTIONS = {
    "budget_eur": "What is the maximum budget for the purchase?",
    "preferred_locations": "Which area of Mallorca do you prefer?",
    "property_type": "What type of property are you looking for?",
    "purchase_timeline": "When are you planning to purchase?",
    "financing_status": (
        "Will you buy with cash, use pre-approved financing, or still need to arrange financing?"
    ),
    "consent_to_contact": (
        "Do you consent to being contacted by a human sales agent about this inquiry?"
    ),
}

ALLOWED_FOLLOW_UP_FIELDS = set(MISSING_FIELD_ORDER)


def _clone_state(state: WorkflowState) -> WorkflowState:
    return state.model_copy(deep=True)


def _append_step(state: WorkflowState, step_name: str) -> None:
    state.step_history.append(step_name)


def _ordered_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered


def _known_locations(properties: Sequence[Property]) -> list[str]:
    locations: list[str] = []
    for property_ in properties:
        if property_.location not in locations:
            locations.append(property_.location)
    if not locations:
        default_catalogue = load_default_catalogue()
        for property_ in default_catalogue:
            if property_.location not in locations:
                locations.append(property_.location)
    return locations


def _known_property_types(properties: Sequence[Property]) -> list[str]:
    property_types: list[str] = []
    for property_ in properties:
        if property_.property_type not in property_types:
            property_types.append(property_.property_type)
    if not property_types:
        default_catalogue = load_default_catalogue()
        for property_ in default_catalogue:
            if property_.property_type not in property_types:
                property_types.append(property_.property_type)
    return property_types


def _parse_budget(text: str) -> int | None:
    raw_text = text.lower()
    matches: list[int] = []

    patterns = [
        (r"€\s*([0-9][0-9,\.]*)\s*k\b", 1000),
        (r"€\s*([0-9][0-9,\.]*)", 1),
        (r"\b([0-9][0-9,\.]*)\s*k\b", 1000),
        (r"\b([0-9][0-9,\.]*)\s*(?:euros?|eur)\b", 1),
        (r"\b(?:budget|maximum|max|max budget|up to|under|less than)\b.{0,20}?([0-9][0-9,\.]*)\b", 1),
    ]

    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, raw_text):
            raw = match.group(1).replace(",", "").replace(".", "")
            if not raw.isdigit():
                continue
            value = int(raw) * multiplier
            if value not in matches:
                matches.append(value)

    if len(matches) > 1:
        raise ValueError("Budget value is ambiguous.")
    if len(matches) == 1:
        return matches[0]
    return None


def _match_known_term(
    normalized_text: str, candidates: Sequence[str], *, token_overlap: bool = False
) -> list[str]:
    query_tokens = set(tokenize_text(normalized_text))
    matched: list[str] = []
    for candidate in candidates:
        normalized_candidate = normalize_text(candidate)
        if normalized_candidate and normalized_candidate in normalized_text:
            matched.append(candidate)
            continue
        if token_overlap:
            candidate_tokens = set(tokenize_text(candidate))
            if query_tokens & candidate_tokens:
                matched.append(candidate)
    return _ordered_unique(matched)


def _parse_property_type(text: str, properties: Sequence[Property]) -> str | None:
    normalized = normalize_text(text)
    matches = _match_known_term(normalized, _known_property_types(properties))
    if len(matches) > 1:
        raise ValueError("Property type value is ambiguous.")
    return matches[0] if matches else None


def _parse_locations(text: str, properties: Sequence[Property]) -> list[str]:
    normalized = normalize_text(text)
    matches = _match_known_term(normalized, _known_locations(properties), token_overlap=True)
    if not matches:
        return []

    generic_location_tokens = {"mallorca", "island", "islands", "balearic", "balearics", "de", "del", "la", "el"}
    filtered: list[str] = []
    for candidate in matches:
        candidate_tokens = set(tokenize_text(candidate))
        if candidate_tokens and candidate_tokens.issubset(generic_location_tokens):
            continue
        if candidate_tokens & generic_location_tokens and len(candidate_tokens & set(tokenize_text(normalized))) == 1:
            matched_token = next(iter(candidate_tokens & set(tokenize_text(normalized))))
            if matched_token in generic_location_tokens:
                continue
        filtered.append(candidate)
    return filtered


def _parse_timeline(text: str) -> str | None:
    normalized = normalize_text(text)
    patterns = [
        (r"\b(immediate|asap|urgent|right away|now|within 3 months?|1 ?-? ?3 months?|1 to 3 months?)\b", "1-3 months"),
        (r"\b(3 ?-? ?6 months?|within 3 to 6 months?|within 3 ?-? ?6 months?|three to six months?)\b", "3-6 months"),
        (r"\b(6 ?-? ?12 months?|within 6 to 12 months?|within 6 ?-? ?12 months?|six to twelve months?)\b", "6-12 months"),
        (r"\b(more than 12 months?|over 12 months?|more than a year|next year|researching|just looking|later)\b", "more than 12 months"),
    ]
    matches: list[str] = []
    for pattern, canonical in patterns:
        if re.search(pattern, normalized):
            matches.append(canonical)
    if len(set(matches)) > 1:
        raise ValueError("Purchase timeline value is ambiguous.")
    return matches[0] if matches else None


def _parse_financing(text: str) -> str | None:
    normalized = normalize_text(text)
    patterns = [
        (r"\b(cash buyer|buy with cash|cash only|cash)\b", "cash_buyer"),
        (
            r"\b(mortgage pre approved|pre approved financing|pre approved|pre approval|preapproved|mortgage preapproved)\b",
            "mortgage_preapproved",
        ),
        (
            r"\b(financing in progress|mortgage in progress|financing underway|application in progress|in progress)\b",
            "financing_in_progress",
        ),
        (
            r"\b(financing required|need financing|still need financing|not started|arrange financing)\b",
            "financing_required",
        ),
    ]
    matches: list[str] = []
    for pattern, canonical in patterns:
        if re.search(pattern, normalized):
            matches.append(canonical)
    if len(set(matches)) > 1:
        raise ValueError("Financing value is ambiguous.")
    return matches[0] if matches else None


def _parse_consent(text: str) -> bool | None:
    normalized = normalize_text(text)
    negative_patterns = [
        r"\bdo not contact me\b",
        r"\bdon'?t contact me\b",
        r"\bdo not call me\b",
        r"\bdon'?t call me\b",
        r"\bno contact\b",
        r"\bno calls\b",
        r"\bdo not email me\b",
        r"\bdo not message me\b",
        r"\bwithout contact\b",
        r"\bno\b",
        r"\bnot interested\b",
        r"\bdecline\b",
    ]
    positive_patterns = [
        r"\byou may contact me\b",
        r"\byou can contact me\b",
        r"\bplease contact me\b",
        r"\bfeel free to contact me\b",
        r"\bi consent\b",
        r"\bi agree to be contacted\b",
        r"\bi am happy to be contacted\b",
        r"\byes\b",
        r"\bokay\b",
        r"\bsure\b",
        r"\bagree\b",
    ]
    negative = any(re.search(pattern, normalized) for pattern in negative_patterns)
    positive = any(re.search(pattern, normalized) for pattern in positive_patterns)
    if negative:
        return False
    if positive:
        return True
    return None


def intake_node(lead: LeadRequirements) -> WorkflowState:
    """Create the initial workflow state."""

    state = WorkflowState(lead=lead.model_copy(deep=True))
    _append_step(state, "intake")
    return state


def extract_requirements(
    state: WorkflowState, properties: Sequence[Property] | None = None
) -> WorkflowState:
    """Conservatively fill missing requirements from the inquiry text."""

    catalogue = list(properties) if properties is not None else load_default_catalogue()
    new_state = _clone_state(state)
    lead = new_state.lead.model_copy(deep=True)
    inquiry_text = lead.inquiry

    if lead.budget_eur is None:
        detected_budget = _parse_budget(inquiry_text)
        if detected_budget is not None:
            lead.budget_eur = detected_budget

    if not lead.preferred_locations:
        detected_locations = _parse_locations(inquiry_text, catalogue)
        if detected_locations:
            lead.preferred_locations = detected_locations

    if lead.property_type is None:
        detected_property_type = _parse_property_type(inquiry_text, catalogue)
        if detected_property_type is not None:
            lead.property_type = detected_property_type

    if lead.purchase_timeline is None:
        detected_timeline = _parse_timeline(inquiry_text)
        if detected_timeline is not None:
            lead.purchase_timeline = detected_timeline

    if lead.financing_status is None:
        detected_financing = _parse_financing(inquiry_text)
        if detected_financing is not None:
            lead.financing_status = detected_financing

    if lead.consent_to_contact is None:
        detected_consent = _parse_consent(inquiry_text)
        if detected_consent is not None:
            lead.consent_to_contact = detected_consent

    new_state.lead = lead
    _append_step(new_state, "extract_requirements")
    return new_state


def validate_requirements(state: WorkflowState) -> WorkflowState:
    """Populate the missing-field list in stable priority order."""

    new_state = _clone_state(state)
    lead = new_state.lead
    missing_fields: list[str] = []

    if lead.budget_eur is None:
        missing_fields.append("budget_eur")
    if not lead.preferred_locations:
        missing_fields.append("preferred_locations")
    if lead.property_type is None:
        missing_fields.append("property_type")
    if lead.purchase_timeline is None:
        missing_fields.append("purchase_timeline")
    if lead.financing_status is None:
        missing_fields.append("financing_status")
    if lead.consent_to_contact is None:
        missing_fields.append("consent_to_contact")

    new_state.missing_fields = missing_fields
    _append_step(new_state, "validate_requirements")
    return new_state


def generate_follow_up_question(state: WorkflowState) -> WorkflowState:
    """Ask one deterministic follow-up question for the first missing field."""

    if not state.missing_fields:
        raise ValueError("No missing fields are available for a follow-up question.")

    new_state = _clone_state(state)
    field_name = new_state.missing_fields[0]
    new_state.follow_up_question = FOLLOW_UP_QUESTIONS[field_name]
    new_state.status = "awaiting_information"
    _append_step(new_state, "generate_follow_up")
    return new_state


def _update_lead_field_from_value(
    lead: LeadRequirements,
    field_name: str,
    value: object,
    properties: Sequence[Property] | None = None,
) -> LeadRequirements:
    if field_name not in ALLOWED_FOLLOW_UP_FIELDS:
        raise ValueError(f"Unsupported follow-up field: {field_name}")

    catalogue = list(properties) if properties is not None else load_default_catalogue()
    current = lead.model_copy(deep=True)
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"Value for {field_name} cannot be blank.")

    if field_name == "budget_eur":
        parsed_budget = _parse_budget(text)
        if parsed_budget is None:
            raise ValueError("Could not parse a numeric budget value.")
        current.budget_eur = parsed_budget
    elif field_name == "preferred_locations":
        locations = _parse_locations(text, catalogue)
        if not locations:
            raise ValueError("Could not parse a valid Mallorca location.")
        current.preferred_locations = locations
    elif field_name == "property_type":
        parsed_type = _parse_property_type(text, catalogue)
        if parsed_type is None:
            raise ValueError("Could not parse a valid property type.")
        current.property_type = parsed_type
    elif field_name == "purchase_timeline":
        parsed_timeline = _parse_timeline(text)
        if parsed_timeline is None:
            raise ValueError("Could not parse a clear purchase timeline.")
        current.purchase_timeline = parsed_timeline
    elif field_name == "financing_status":
        parsed_financing = _parse_financing(text)
        if parsed_financing is None:
            raise ValueError("Could not parse a clear financing status.")
        current.financing_status = parsed_financing
    elif field_name == "consent_to_contact":
        parsed_consent = _parse_consent(text)
        if parsed_consent is None:
            raise ValueError("Could not parse explicit consent or refusal.")
        current.consent_to_contact = parsed_consent

    return current


def apply_follow_up_value(
    lead: LeadRequirements,
    field_name: str,
    value: object,
    properties: Sequence[Property] | None = None,
) -> LeadRequirements:
    """Deterministically fill one missing field from the user response."""

    return _update_lead_field_from_value(lead, field_name, value, properties)


def retrieve_properties_node(
    state: WorkflowState,
    properties: Sequence[Property],
    top_k: int = 3,
) -> WorkflowState:
    """Run the offline property retrieval backend and store the matches."""

    new_state = _clone_state(state)
    result = retrieve_properties(new_state.lead, list(properties), top_k=top_k)
    new_state.property_matches = list(result.matches)
    if result.warnings:
        for warning in result.warnings:
            if warning not in new_state.warnings:
                new_state.warnings.append(warning)
    _append_step(new_state, "retrieve_properties")
    return new_state


def score_lead_node(state: WorkflowState, properties: Sequence[Property]) -> WorkflowState:
    """Calculate and store the deterministic score breakdown."""

    new_state = _clone_state(state)
    breakdown = score_lead(new_state.lead, list(properties))
    new_state.score_breakdown = breakdown
    _append_step(new_state, "score_lead")
    return new_state


def prepare_recommendation_node(state: WorkflowState) -> WorkflowState:
    """Create the internal-only recommendation summary."""

    if state.score_breakdown is None:
        raise ValueError("score_breakdown must be available before recommendation.")

    new_state = _clone_state(state)
    matched_ids = [match.source_id for match in new_state.property_matches[:3]]
    matched_label = ", ".join(matched_ids) if matched_ids else "none"
    consent_text = "yes" if new_state.lead.consent_to_contact is True else "no"
    confidence = max(
        [match.relevance_score for match in new_state.property_matches] or [0.0]
    )
    new_state.confidence = confidence
    new_state.recommendation = (
        f"Lead classification: {new_state.score_breakdown.classification}. "
        f"Total score: {new_state.score_breakdown.total}/100. "
        f"Matched properties: {matched_label}. "
        f"Contact consent available: {consent_text}. "
        "Human review is required before any follow-up."
    )
    _append_step(new_state, "prepare_recommendation")
    return new_state


def human_review_gate(state: WorkflowState) -> WorkflowState:
    """Pause the workflow for mandatory human review."""

    new_state = _clone_state(state)
    new_state.status = "awaiting_human_review"
    _append_step(new_state, "human_review_gate")
    return new_state


def handle_human_decision(
    state: WorkflowState,
    decision: str,
    edited_recommendation: str | None = None,
) -> WorkflowState:
    """Apply a human decision to the current workflow state."""

    normalized_decision = decision.strip().lower()
    new_state = _clone_state(state)

    if normalized_decision == "approve":
        if new_state.lead.consent_to_contact is True:
            new_state.status = "approved_for_follow_up"
        else:
            new_state.status = "closed_no_contact"
            warning = "Customer contact is not allowed because consent is missing or false."
            if warning not in new_state.warnings:
                new_state.warnings.append(warning)
    elif normalized_decision == "edit":
        if edited_recommendation is None or not edited_recommendation.strip():
            raise ValueError("An edited recommendation is required for edit decisions.")
        new_state.recommendation = edited_recommendation.strip()
        new_state.status = "awaiting_human_review"
    elif normalized_decision == "reject":
        new_state.status = "rejected"
    else:
        raise ValueError(f"Unknown human decision: {decision}")

    new_state.human_decision = normalized_decision  # type: ignore[assignment]
    _append_step(new_state, "human_decision")
    return new_state
