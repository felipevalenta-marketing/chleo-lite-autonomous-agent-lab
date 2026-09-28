"""Offline retrieval prototype for Chleo Lite.

This local retrieval backend is intentionally deterministic and uses only the
standard library plus the validated Chleo models. Planned OpenAI embeddings,
LangChain, and Chroma retrieval are not implemented in this phase.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from pydantic import ValidationError

from .models import (
    LeadRequirements,
    Property,
    PropertyMatch,
    RetrievalResult,
)

DEFAULT_CATALOGUE_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_properties.json"
ACTIVE_STATUSES = {"active", "available"}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "d",
    "de",
    "for",
    "from",
    "have",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "near",
    "need",
    "of",
    "on",
    "or",
    "looking",
    "please",
    "show",
    "the",
    "to",
    "want",
    "with",
    "would",
}


class PropertyCatalogueError(Exception):
    """Base error for local property catalogue problems."""


class PropertyCatalogueFileNotFoundError(PropertyCatalogueError):
    """Raised when the catalogue file cannot be found."""


class PropertyCatalogueFormatError(PropertyCatalogueError):
    """Raised when the catalogue file contents are invalid."""


def normalize_text(value: str) -> str:
    """Normalize text for deterministic offline matching."""

    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    lowered = without_accents.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", normalized).strip()


def tokenize_text(value: str) -> list[str]:
    """Tokenize normalized text and remove a small set of common stop words."""

    tokens = normalize_text(value).split()
    return [token for token in tokens if token not in STOP_WORDS]


def create_property_document(property_: Property) -> str:
    """Create a deterministic text document for future embedding pipelines."""

    features = ", ".join(property_.features) if property_.features else "none"
    return (
        f"Property ID: {property_.property_id}\n"
        f"Title: {property_.title}\n"
        f"Location: {property_.location}\n"
        f"Property type: {property_.property_type}\n"
        f"Price EUR: {property_.price_eur}\n"
        f"Bedrooms: {property_.bedrooms}\n"
        f"Bathrooms: {property_.bathrooms}\n"
        f"Features: {features}\n"
        f"Status: {property_.status}"
    )


def load_property_catalogue(path: str | Path = DEFAULT_CATALOGUE_PATH) -> list[Property]:
    """Load and validate the fictional property catalogue from JSON."""

    catalogue_path = Path(path)
    try:
        raw_text = catalogue_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PropertyCatalogueFileNotFoundError(
            f"Property catalogue not found: {catalogue_path}"
        ) from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise PropertyCatalogueFormatError(
            f"Invalid JSON in property catalogue: {catalogue_path}"
        ) from exc

    if not isinstance(payload, list):
        raise PropertyCatalogueFormatError(
            "Property catalogue root must be a JSON list."
        )

    properties: list[Property] = []
    for index, record in enumerate(payload):
        try:
            properties.append(Property.model_validate(record))
        except ValidationError as exc:
            raise PropertyCatalogueFormatError(
                f"Invalid property record at index {index}."
            ) from exc
    return properties


def _is_active_property(property_: Property) -> bool:
    return normalize_text(property_.status) in ACTIVE_STATUSES


def _lead_query_text(lead: LeadRequirements) -> str:
    parts = [lead.inquiry]
    parts.extend(lead.preferred_locations)
    if lead.property_type:
        parts.append(lead.property_type)
    return " ".join(part for part in parts if part).strip()


def _property_location_tokens(property_: Property) -> set[str]:
    return set(tokenize_text(property_.location))


def _property_title_tokens(property_: Property) -> set[str]:
    return set(tokenize_text(property_.title))


def _property_feature_tokens(property_: Property) -> set[str]:
    tokens: set[str] = set()
    for feature in property_.features:
        tokens.update(tokenize_text(feature))
    return tokens


def _property_document_tokens(property_: Property) -> set[str]:
    document = create_property_document(property_)
    return set(tokenize_text(document))


def _lead_query_tokens(lead: LeadRequirements) -> set[str]:
    return set(tokenize_text(_lead_query_text(lead)))


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _append_term(terms: list[str], term: str) -> None:
    if term not in terms:
        terms.append(term)


def _location_score_and_terms(
    lead: LeadRequirements, property_: Property
) -> tuple[float, list[str], list[str]]:
    if not lead.preferred_locations:
        return 0.0, [], []

    location_norm = normalize_text(property_.location)
    title_norm = normalize_text(property_.title)
    document_norm = normalize_text(create_property_document(property_))
    property_location_tokens = _property_location_tokens(property_)
    property_title_tokens = _property_title_tokens(property_)
    property_document_tokens = _property_document_tokens(property_)

    best_score = 0.0
    best_terms: list[str] = []
    matched_terms: list[str] = []
    for preferred_location in lead.preferred_locations:
        preferred_norm = normalize_text(preferred_location)
        if not preferred_norm:
            continue

        if (
            preferred_norm in location_norm
            or preferred_norm in title_norm
            or preferred_norm in document_norm
        ):
            return 1.0, [preferred_norm], [f"Matches preferred location: {preferred_location}"]

        preferred_tokens = set(tokenize_text(preferred_location))
        overlap = preferred_tokens & (
            property_location_tokens | property_title_tokens | property_document_tokens
        )
        if overlap:
            score = min(0.8, 0.55 + (0.25 * len(overlap) / max(len(preferred_tokens), 1)))
            if score > best_score:
                best_score = score
                best_terms = sorted(overlap)
                matched_terms = [f"Related location match: {preferred_location}"]

    return best_score, best_terms, matched_terms


def _property_type_score_and_terms(
    lead: LeadRequirements, property_: Property
) -> tuple[float, list[str], list[str]]:
    if not lead.property_type:
        return 0.0, [], []
    if normalize_text(lead.property_type) != normalize_text(property_.property_type):
        return 0.0, [], []
    normalized = normalize_text(lead.property_type)
    return 1.0, [normalized], [f"Matches property type: {lead.property_type}"]


def _feature_score_and_terms(
    lead: LeadRequirements, property_: Property
) -> tuple[float, list[str], list[str]]:
    query_tokens = _lead_query_tokens(lead)
    feature_tokens = _property_feature_tokens(property_)
    overlap = query_tokens & feature_tokens
    if not overlap:
        return 0.0, [], []
    score = min(1.0, len(overlap) / max(len(feature_tokens), 1))
    matched = sorted(overlap)
    reasons = [f"Feature match: {term}" for term in matched]
    return score, matched, reasons


def _title_score_and_terms(
    lead: LeadRequirements, property_: Property
) -> tuple[float, list[str], list[str]]:
    query_tokens = _lead_query_tokens(lead)
    title_tokens = _property_title_tokens(property_)
    overlap = query_tokens & title_tokens
    if not overlap:
        return 0.0, [], []
    score = min(1.0, len(overlap) / max(len(title_tokens), 1))
    matched = sorted(overlap)
    reasons = [f"Title match: {term}" for term in matched]
    return score, matched, reasons


def _general_overlap_score_and_terms(
    lead: LeadRequirements, property_: Property
) -> tuple[float, list[str], list[str]]:
    query_tokens = _lead_query_tokens(lead)
    document_tokens = _property_document_tokens(property_)
    overlap = query_tokens & document_tokens
    if not overlap:
        return 0.0, [], []
    score = min(1.0, len(overlap) / max(len(query_tokens), 1))
    matched = sorted(overlap)
    reasons = [f"General document match: {term}" for term in matched[:3]]
    return score, matched, reasons


def _score_property(lead: LeadRequirements, property_: Property) -> PropertyMatch:
    location_score, location_terms, location_reasons = _location_score_and_terms(
        lead, property_
    )
    type_score, type_terms, type_reasons = _property_type_score_and_terms(lead, property_)
    feature_score, feature_terms, feature_reasons = _feature_score_and_terms(
        lead, property_
    )
    title_score, title_terms, title_reasons = _title_score_and_terms(lead, property_)
    general_score, general_terms, general_reasons = _general_overlap_score_and_terms(
        lead, property_
    )

    weighted_score = (
        0.40 * location_score
        + 0.25 * type_score
        + 0.15 * feature_score
        + 0.10 * title_score
        + 0.10 * general_score
    )
    relevance_score = round(min(1.0, weighted_score), 4)

    matched_terms: list[str] = []
    for term in location_terms + type_terms + feature_terms + title_terms + general_terms:
        _append_term(matched_terms, term)

    reasons: list[str] = ["Active listing"]
    if lead.budget_eur is not None:
        _append_reason(reasons, "Within the stated budget")
    for reason in location_reasons + type_reasons + feature_reasons + title_reasons + general_reasons:
        _append_reason(reasons, reason)

    return PropertyMatch(
        property=property_,
        relevance_score=relevance_score,
        matched_terms=matched_terms,
        match_reasons=reasons,
        source_id=property_.property_id,
    )


def _passes_exact_filters(lead: LeadRequirements, property_: Property) -> bool:
    if not _is_active_property(property_):
        return False
    if lead.budget_eur is not None and property_.price_eur > lead.budget_eur:
        return False
    if lead.property_type and normalize_text(lead.property_type) != normalize_text(
        property_.property_type
    ):
        return False
    return True


def _build_retrieval_result(
    lead: LeadRequirements,
    properties: list[Property],
    top_k: int,
) -> RetrievalResult:
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    query = lead.inquiry.strip()
    total_catalogue_size = len(properties)
    filtered_properties = [
        property_ for property_ in properties if _passes_exact_filters(lead, property_)
    ]
    filtered_out_count = total_catalogue_size - len(filtered_properties)

    if not filtered_properties:
        return RetrievalResult(
            query=query,
            matches=[],
            filtered_out_count=filtered_out_count,
            total_catalogue_size=total_catalogue_size,
            warnings=["No properties matched the exact filters."],
        )

    ranked_matches = sorted(
        (_score_property(lead, property_) for property_ in filtered_properties),
        key=lambda match: (-match.relevance_score, match.property.property_id),
    )
    return RetrievalResult(
        query=query,
        matches=ranked_matches[:top_k],
        filtered_out_count=filtered_out_count,
        total_catalogue_size=total_catalogue_size,
        warnings=[],
    )


def retrieve_properties(
    lead: LeadRequirements,
    properties: list[Property],
    top_k: int = 3,
) -> RetrievalResult:
    """Return deterministic offline property matches for a validated lead."""

    return _build_retrieval_result(lead, properties, top_k)


def load_default_catalogue() -> list[Property]:
    """Convenience wrapper that loads the default fictional catalogue."""

    return load_property_catalogue(DEFAULT_CATALOGUE_PATH)


def retrieve_from_default_catalogue(
    lead: LeadRequirements,
    top_k: int = 3,
) -> RetrievalResult:
    """Load the default catalogue and run deterministic retrieval."""

    return retrieve_properties(lead, load_default_catalogue(), top_k=top_k)
