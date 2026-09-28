from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chleo.models import LeadRequirements, Property, PropertyMatch
from chleo.rag import (
    PropertyCatalogueFileNotFoundError,
    PropertyCatalogueFormatError,
    create_property_document,
    load_default_catalogue,
    load_property_catalogue,
    normalize_text,
    retrieve_properties,
    tokenize_text,
)


def _sample_properties() -> list[dict[str, object]]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_properties.json"
    return json.loads(data_path.read_text(encoding="utf-8"))


def _sample_leads() -> list[dict[str, object]]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_leads.json"
    return json.loads(data_path.read_text(encoding="utf-8"))


def _validated_properties() -> list[Property]:
    return [Property.model_validate(item) for item in _sample_properties()]


def _lead(index: int = 0, **overrides: object) -> LeadRequirements:
    data = dict(_sample_leads()[index])
    data.update(overrides)
    return LeadRequirements.model_validate(data)


class TestRag(unittest.TestCase):
    def test_successful_loading_of_existing_property_json_file(self) -> None:
        properties = load_default_catalogue()
        self.assertEqual(len(properties), 3)
        self.assertTrue(all(isinstance(item, Property) for item in properties))

    def test_all_loaded_records_are_validated_property_models(self) -> None:
        properties = load_default_catalogue()
        self.assertTrue(all(isinstance(item, Property) for item in properties))
        self.assertEqual([item.property_id for item in properties], ["MAL-001", "MAL-002", "MAL-003"])

    def test_missing_file_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "missing.json"
            with self.assertRaises(PropertyCatalogueFileNotFoundError):
                load_property_catalogue(missing_path)

    def test_invalid_json_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            invalid_path = Path(tmp_dir) / "invalid.json"
            invalid_path.write_text("{not valid json}", encoding="utf-8")
            with self.assertRaises(PropertyCatalogueFormatError):
                load_property_catalogue(invalid_path)

    def test_root_not_a_list_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            invalid_path = Path(tmp_dir) / "invalid.json"
            invalid_path.write_text(json.dumps({"property_id": "MAL-X"}), encoding="utf-8")
            with self.assertRaises(PropertyCatalogueFormatError):
                load_property_catalogue(invalid_path)

    def test_invalid_property_record_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            invalid_path = Path(tmp_dir) / "invalid.json"
            invalid_payload = [_sample_properties()[0] | {"price_eur": 0}]
            invalid_path.write_text(json.dumps(invalid_payload), encoding="utf-8")
            with self.assertRaises(PropertyCatalogueFormatError):
                load_property_catalogue(invalid_path)

    def test_deterministic_document_text_creation(self) -> None:
        property_ = Property.model_validate(_sample_properties()[0])
        first = create_property_document(property_)
        second = create_property_document(property_)
        self.assertEqual(first, second)
        self.assertIn("Property ID: MAL-001", first)
        self.assertIn("Title: Sunlit Terrace Apartment", first)

    def test_accent_and_punctuation_normalization(self) -> None:
        self.assertEqual(normalize_text("  Côte d'Azur, Palma! "), "cote d azur palma")
        self.assertEqual(tokenize_text("  Côte d'Azur, Palma! "), ["cote", "azur", "palma"])

    def test_inactive_or_unavailable_property_filtered_out(self) -> None:
        lead = _lead(2)
        result = retrieve_properties(lead, [_validated_properties()[2]])
        self.assertEqual(result.matches, [])
        self.assertGreaterEqual(result.filtered_out_count, 1)

    def test_property_over_budget_filtered_out(self) -> None:
        lead = _lead(0, budget_eur=100000)
        result = retrieve_properties(lead, [_validated_properties()[0]])
        self.assertEqual(result.matches, [])

    def test_property_type_mismatch_filtered_out(self) -> None:
        lead = _lead(0, property_type="villa")
        result = retrieve_properties(lead, [_validated_properties()[0]])
        self.assertEqual(result.matches, [])

    def test_preferred_location_match_ranks_higher(self) -> None:
        lead = _lead(0)
        property_a = Property.model_validate(_sample_properties()[0])
        property_b = Property.model_validate(
            _sample_properties()[0] | {
                "property_id": "MAL-010",
                "location": "Andratx",
                "title": "Andratx Terrace Apartment",
            }
        )
        result = retrieve_properties(lead, [property_b, property_a], top_k=2)
        self.assertEqual([match.source_id for match in result.matches], ["MAL-001", "MAL-010"])
        self.assertGreaterEqual(result.matches[0].relevance_score, result.matches[1].relevance_score)

    def test_matching_feature_improves_relevance(self) -> None:
        lead = _lead(0)
        base = _sample_properties()[0]
        property_with_feature = Property.model_validate(base)
        property_without_feature = Property.model_validate(
            base | {"property_id": "MAL-011", "features": ["central_location"]}
        )
        result = retrieve_properties(lead, [property_without_feature, property_with_feature], top_k=2)
        self.assertEqual(result.matches[0].source_id, "MAL-001")
        self.assertGreater(result.matches[0].relevance_score, result.matches[1].relevance_score)

    def test_results_are_ordered_from_highest_to_lowest_relevance(self) -> None:
        lead = _lead(0)
        base = _sample_properties()[0]
        property_high = Property.model_validate(base)
        property_mid = Property.model_validate(base | {"property_id": "MAL-012", "features": ["terrace"]})
        property_low = Property.model_validate(base | {"property_id": "MAL-013", "features": ["central_location"]})
        result = retrieve_properties(lead, [property_low, property_high, property_mid], top_k=3)
        scores = [match.relevance_score for match in result.matches]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_top_k_limit(self) -> None:
        lead = _lead(0)
        result = retrieve_properties(lead, _validated_properties(), top_k=1)
        self.assertEqual(len(result.matches), 1)

    def test_invalid_zero_or_negative_top_k(self) -> None:
        lead = _lead(0)
        with self.assertRaises(ValueError):
            retrieve_properties(lead, _validated_properties(), top_k=0)
        with self.assertRaises(ValueError):
            retrieve_properties(lead, _validated_properties(), top_k=-1)

    def test_empty_result_when_no_property_qualifies(self) -> None:
        lead = _lead(0, budget_eur=1000, property_type="villa")
        result = retrieve_properties(lead, _validated_properties(), top_k=3)
        self.assertEqual(result.matches, [])
        self.assertGreaterEqual(result.filtered_out_count, 1)

    def test_source_property_ids_are_preserved(self) -> None:
        lead = _lead(0)
        result = retrieve_properties(lead, _validated_properties(), top_k=3)
        for match in result.matches:
            self.assertEqual(match.source_id, match.property.property_id)

    def test_scores_remain_between_zero_and_one(self) -> None:
        lead = _lead(0)
        result = retrieve_properties(lead, _validated_properties(), top_k=3)
        for match in result.matches:
            self.assertGreaterEqual(match.relevance_score, 0)
            self.assertLessEqual(match.relevance_score, 1)

    def test_repeated_retrieval_produces_identical_results(self) -> None:
        lead = _lead(0)
        properties = _validated_properties()
        first = retrieve_properties(lead, properties, top_k=3)
        second = retrieve_properties(lead, properties, top_k=3)
        self.assertEqual(first.model_dump(), second.model_dump())

    def test_no_api_key_is_required(self) -> None:
        lead = _lead(0)
        with patch.dict(os.environ, {}, clear=True):
            result = retrieve_properties(lead, _validated_properties(), top_k=3)
        self.assertTrue(result.matches)

    def test_no_network_call_occurs(self) -> None:
        lead = _lead(0)
        with patch("socket.socket", side_effect=AssertionError("network access not allowed")):
            result = retrieve_properties(lead, _validated_properties(), top_k=3)
        self.assertTrue(result.matches)

    def test_property_match_model_validation(self) -> None:
        property_ = Property.model_validate(_sample_properties()[0])
        match = PropertyMatch(
            property=property_,
            relevance_score=0.75,
            matched_terms=["palma", "terrace"],
            match_reasons=["Matches preferred location: Palma de Mallorca"],
            source_id="MAL-001",
        )
        self.assertEqual(match.source_id, "MAL-001")
        self.assertGreaterEqual(match.relevance_score, 0)
        self.assertLessEqual(match.relevance_score, 1)
