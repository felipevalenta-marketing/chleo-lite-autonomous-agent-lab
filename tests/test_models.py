from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from pydantic import ValidationError

from chleo.models import LeadRequirements, Property, ScoreBreakdown


def _load_sample_properties() -> list[dict[str, object]]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_properties.json"
    return json.loads(data_path.read_text(encoding="utf-8"))


def _load_sample_leads() -> list[dict[str, object]]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_leads.json"
    return json.loads(data_path.read_text(encoding="utf-8"))


class TestModels(unittest.TestCase):
    def test_valid_property_model(self) -> None:
        prop = Property.model_validate(_load_sample_properties()[0])
        self.assertEqual(prop.property_id, "MAL-001")
        self.assertEqual(prop.status, "available")

    def test_invalid_zero_price_rejected(self) -> None:
        sample = _load_sample_properties()[0] | {"price_eur": 0}
        with self.assertRaises(ValidationError):
            Property.model_validate(sample)

    def test_negative_bedrooms_rejected(self) -> None:
        sample = _load_sample_properties()[0] | {"bedrooms": -1}
        with self.assertRaises(ValidationError):
            Property.model_validate(sample)

    def test_negative_bathrooms_rejected(self) -> None:
        sample = _load_sample_properties()[0] | {"bathrooms": -1}
        with self.assertRaises(ValidationError):
            Property.model_validate(sample)

    def test_valid_complete_lead(self) -> None:
        lead = LeadRequirements.model_validate(_load_sample_leads()[0])
        self.assertTrue(lead.inquiry)
        self.assertTrue(lead.consent_to_contact)

    def test_incomplete_lead_keeps_optional_fields_missing(self) -> None:
        lead = LeadRequirements.model_validate({"inquiry": "I am looking for a place."})
        self.assertIsNone(lead.lead_id)
        self.assertIsNone(lead.budget_eur)
        self.assertEqual(lead.preferred_locations, [])
        self.assertIsNone(lead.consent_to_contact)

    def test_blank_inquiry_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            LeadRequirements.model_validate({"inquiry": "   "})

    def test_negative_budget_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            LeadRequirements.model_validate({"inquiry": "Hello", "budget_eur": -1})

    def test_explicit_consent_is_preserved(self) -> None:
        lead = LeadRequirements.model_validate({"inquiry": "Hello", "consent_to_contact": False})
        self.assertFalse(lead.consent_to_contact)

    def test_score_breakdown_validation(self) -> None:
        breakdown = ScoreBreakdown.model_validate(
            {
                "budget_and_stock": 25,
                "purchase_timeline": 25,
                "financing_readiness": 20,
                "requirements_clarity": 20,
                "consent_and_contact": 10,
                "total": 100,
                "classification": "hot",
                "reasons": ["Everything is ready."],
            }
        )
        self.assertEqual(breakdown.total, 100)
