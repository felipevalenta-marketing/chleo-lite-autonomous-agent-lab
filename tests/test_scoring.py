from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chleo.models import LeadRequirements, Property
from chleo.scoring import (
    classify_score,
    score_budget_and_stock,
    score_consent_and_contact,
    score_financing_readiness,
    score_lead,
    score_purchase_timeline,
    score_requirements_clarity,
)


def _sample_properties() -> list[Property]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_properties.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    return [Property.model_validate(item) for item in data]


def _lead(**overrides: object) -> LeadRequirements:
    base = {
        "lead_id": "LEAD-TEST",
        "inquiry": "I am looking for a Mallorca home.",
        "budget_eur": 450000,
        "preferred_locations": ["Palma de Mallorca"],
        "property_type": "apartment",
        "purchase_timeline": "1-3 months",
        "financing_status": "cash_buyer",
        "consent_to_contact": True,
    }
    base.update(overrides)
    return LeadRequirements.model_validate(base)


class TestScoring(unittest.TestCase):
    def test_budget_and_stock_with_compatible_active_property_scores_full_points(self) -> None:
        lead = _lead()
        self.assertEqual(score_budget_and_stock(lead, _sample_properties()), 25)

    def test_budget_and_stock_without_compatible_property_scores_partial_points(self) -> None:
        lead = _lead(budget_eur=100000)
        self.assertEqual(score_budget_and_stock(lead, _sample_properties()), 10)

    def test_budget_and_stock_without_budget_scores_zero(self) -> None:
        lead = _lead(budget_eur=None)
        self.assertEqual(score_budget_and_stock(lead, _sample_properties()), 0)

    def test_purchase_timeline_scoring_immediate(self) -> None:
        self.assertEqual(score_purchase_timeline(_lead(purchase_timeline="Immediate")), 25)

    def test_purchase_timeline_scoring_medium(self) -> None:
        self.assertEqual(score_purchase_timeline(_lead(purchase_timeline="3-6 months")), 18)

    def test_purchase_timeline_scoring_long(self) -> None:
        self.assertEqual(score_purchase_timeline(_lead(purchase_timeline="6-12 months")), 10)

    def test_purchase_timeline_scoring_missing(self) -> None:
        self.assertEqual(score_purchase_timeline(_lead(purchase_timeline=None)), 0)

    def test_financing_scoring_cash_buyer(self) -> None:
        self.assertEqual(score_financing_readiness(_lead(financing_status="cash buyer")), 20)

    def test_financing_scoring_preapproved(self) -> None:
        self.assertEqual(
            score_financing_readiness(_lead(financing_status="mortgage pre-approved")),
            20,
        )

    def test_financing_scoring_in_progress(self) -> None:
        self.assertEqual(
            score_financing_readiness(_lead(financing_status="financing in progress")),
            12,
        )

    def test_financing_scoring_missing(self) -> None:
        self.assertEqual(score_financing_readiness(_lead(financing_status=None)), 0)

    def test_requirements_clarity_scores_both_fields(self) -> None:
        lead = _lead(preferred_locations=["Palma de Mallorca"], property_type="apartment")
        self.assertEqual(score_requirements_clarity(lead), 20)

    def test_requirements_clarity_scores_single_field(self) -> None:
        lead = _lead(preferred_locations=["Palma de Mallorca"], property_type=None)
        self.assertEqual(score_requirements_clarity(lead), 10)

    def test_requirements_clarity_scores_no_fields(self) -> None:
        lead = _lead(preferred_locations=[], property_type=None)
        self.assertEqual(score_requirements_clarity(lead), 0)

    def test_consent_scoring(self) -> None:
        self.assertEqual(score_consent_and_contact(_lead(consent_to_contact=True)), 10)
        self.assertEqual(score_consent_and_contact(_lead(consent_to_contact=False)), 0)
        self.assertEqual(score_consent_and_contact(_lead(consent_to_contact=None)), 0)

    def test_classification_boundaries(self) -> None:
        self.assertEqual(classify_score(44), "cold")
        self.assertEqual(classify_score(45), "warm")
        self.assertEqual(classify_score(74), "warm")
        self.assertEqual(classify_score(75), "hot")

    def test_realistic_hot_lead_scoring(self) -> None:
        result = score_lead(_lead(), _sample_properties())
        self.assertEqual(result.total, 100)
        self.assertEqual(result.classification, "hot")

    def test_realistic_warm_lead_scoring(self) -> None:
        lead = _lead(
            budget_eur=420000,
            property_type="apartment",
            preferred_locations=["Palma de Mallorca"],
            purchase_timeline="6-12 months",
            financing_status="unknown",
            consent_to_contact=False,
        )
        result = score_lead(lead, _sample_properties())
        self.assertEqual(result.total, 55)
        self.assertEqual(result.classification, "warm")

    def test_realistic_cold_lead_scoring(self) -> None:
        lead = _lead(
            budget_eur=None,
            preferred_locations=[],
            property_type=None,
            purchase_timeline=None,
            financing_status=None,
            consent_to_contact=False,
        )
        result = score_lead(lead, _sample_properties())
        self.assertEqual(result.total, 0)
        self.assertEqual(result.classification, "cold")

    def test_total_equals_category_sum_and_is_bounded(self) -> None:
        result = score_lead(_lead(), _sample_properties())
        category_sum = (
            result.budget_and_stock
            + result.purchase_timeline
            + result.financing_readiness
            + result.requirements_clarity
            + result.consent_and_contact
        )
        self.assertEqual(result.total, category_sum)
        self.assertGreaterEqual(result.total, 0)
        self.assertLessEqual(result.total, 100)

    def test_score_reasons_are_human_readable(self) -> None:
        result = score_lead(_lead(), _sample_properties())
        self.assertTrue(all(isinstance(reason, str) and reason for reason in result.reasons))
