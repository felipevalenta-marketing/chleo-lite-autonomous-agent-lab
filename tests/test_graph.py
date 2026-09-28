from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chleo.graph import ChleoWorkflow
from chleo.models import LeadRequirements, Property


def _load_sample_properties() -> list[Property]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_properties.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    return [Property.model_validate(item) for item in payload]


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


def _workflow() -> ChleoWorkflow:
    return ChleoWorkflow()


class TestWorkflow(unittest.TestCase):
    def test_complete_lead_reaches_awaiting_human_review(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        self.assertEqual(state.status, "awaiting_human_review")
        self.assertIsNotNone(state.score_breakdown)
        self.assertEqual(state.score_breakdown.total, 100)
        self.assertEqual(state.score_breakdown.classification, "hot")

    def test_incomplete_lead_reaches_awaiting_information(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate(
                {"inquiry": "I want an apartment in Palma with a budget of €350,000."}
            ),
            _load_sample_properties(),
        )
        self.assertEqual(state.status, "awaiting_information")

    def test_retrieval_is_not_executed_when_data_is_missing(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I want an apartment in Palma."}),
            _load_sample_properties(),
        )
        self.assertEqual(state.property_matches, [])
        self.assertEqual(state.score_breakdown, None)

    def test_scoring_is_not_executed_when_data_is_missing(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I want an apartment in Palma."}),
            _load_sample_properties(),
        )
        self.assertEqual(state.score_breakdown, None)

    def test_correct_first_follow_up_question(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate(
                {"inquiry": "I want an apartment in Palma with a budget of €350,000."}
            ),
            _load_sample_properties(),
        )
        self.assertEqual(state.follow_up_question, "When are you planning to purchase?")

    def test_stable_missing_field_priority(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I am looking for a Mallorca home."}),
            _load_sample_properties(),
        )
        self.assertEqual(
            state.missing_fields,
            [
                "budget_eur",
                "preferred_locations",
                "property_type",
                "purchase_timeline",
                "financing_status",
                "consent_to_contact",
            ],
        )

    def test_budget_extraction_from_standard_number(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate(
                {"inquiry": "I want an apartment in Palma with a budget of €350,000."}
            ),
            _load_sample_properties(),
        )
        self.assertEqual(state.lead.budget_eur, 350000)

    def test_budget_extraction_from_k_notation(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I want a villa with a budget of 350k."}),
            _load_sample_properties(),
        )
        self.assertEqual(state.lead.budget_eur, 350000)

    def test_property_type_extraction(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I want a villa in Palma."}),
            _load_sample_properties(),
        )
        self.assertEqual(state.lead.property_type, "villa")

    def test_location_extraction_from_catalogue_values(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I want a home in Palma."}),
            _load_sample_properties(),
        )
        self.assertEqual(state.lead.preferred_locations, ["Palma de Mallorca"])

    def test_timeline_extraction(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I plan to buy within 3-6 months."}),
            _load_sample_properties(),
        )
        self.assertEqual(state.lead.purchase_timeline, "3-6 months")

    def test_financing_extraction(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I am a cash buyer."}),
            _load_sample_properties(),
        )
        self.assertEqual(state.lead.financing_status, "cash_buyer")

    def test_explicit_positive_consent_extraction(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "You may contact me about this property."}),
            _load_sample_properties(),
        )
        self.assertTrue(state.lead.consent_to_contact)

    def test_explicit_negative_consent_extraction(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "Do not contact me about this inquiry."}),
            _load_sample_properties(),
        )
        self.assertFalse(state.lead.consent_to_contact)

    def test_ambiguous_consent_remains_missing(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate({"inquiry": "I am interested in a Mallorca apartment."}),
            _load_sample_properties(),
        )
        self.assertIsNone(state.lead.consent_to_contact)

    def test_existing_structured_values_are_not_overwritten(self) -> None:
        state = _workflow().run(
            LeadRequirements.model_validate(
                {
                    "inquiry": "I want an apartment in Palma with a budget of €350,000.",
                    "budget_eur": 500000,
                    "preferred_locations": ["Santa Ponsa"],
                    "property_type": "apartment",
                    "purchase_timeline": "1-3 months",
                    "financing_status": "cash_buyer",
                    "consent_to_contact": True,
                }
            ),
            _load_sample_properties(),
        )
        self.assertEqual(state.lead.budget_eur, 500000)
        self.assertEqual(state.lead.preferred_locations, ["Santa Ponsa"])

    def test_follow_up_budget_update(self) -> None:
        workflow = _workflow()
        state = workflow.run(
            LeadRequirements.model_validate({"inquiry": "I want a villa in Palma."}),
            _load_sample_properties(),
        )
        state = workflow.resume_with_follow_up(state, "budget_eur", "€400,000", _load_sample_properties())
        self.assertEqual(state.lead.budget_eur, 400000)

    def test_follow_up_location_update(self) -> None:
        workflow = _workflow()
        state = workflow.run(
            LeadRequirements.model_validate({"inquiry": "I want a home with a budget of €400,000."}),
            _load_sample_properties(),
        )
        state = workflow.resume_with_follow_up(
            state,
            "preferred_locations",
            "Palma de Mallorca",
            _load_sample_properties(),
        )
        self.assertEqual(state.lead.preferred_locations, ["Palma de Mallorca"])

    def test_follow_up_consent_update(self) -> None:
        workflow = _workflow()
        state = workflow.run(
            LeadRequirements.model_validate({"inquiry": "I want a home with a budget of €400,000."}),
            _load_sample_properties(),
        )
        state = workflow.resume_with_follow_up(
            state,
            "consent_to_contact",
            "yes",
            _load_sample_properties(),
        )
        self.assertTrue(state.lead.consent_to_contact)

    def test_invalid_follow_up_field(self) -> None:
        workflow = _workflow()
        state = workflow.run(
            LeadRequirements.model_validate({"inquiry": "I want a home with a budget of €400,000."}),
            _load_sample_properties(),
        )
        with self.assertRaises(ValueError):
            workflow.resume_with_follow_up(state, "invalid_field", "yes", _load_sample_properties())

    def test_invalid_follow_up_value(self) -> None:
        workflow = _workflow()
        state = workflow.run(
            LeadRequirements.model_validate({"inquiry": "I want a home with a budget of €400,000."}),
            _load_sample_properties(),
        )
        with self.assertRaises(ValueError):
            workflow.resume_with_follow_up(state, "purchase_timeline", "someday maybe", _load_sample_properties())

    def test_multiple_follow_up_rounds(self) -> None:
        workflow = _workflow()
        state = workflow.run(
            LeadRequirements.model_validate({"inquiry": "I want an apartment in Palma with a budget of €350,000."}),
            _load_sample_properties(),
        )
        self.assertEqual(state.status, "awaiting_information")
        self.assertEqual(state.follow_up_question, "When are you planning to purchase?")
        state = workflow.resume_with_follow_up(state, "purchase_timeline", "3-6 months", _load_sample_properties())
        self.assertEqual(state.follow_up_question, "Will you buy with cash, use pre-approved financing, or still need to arrange financing?")
        state = workflow.resume_with_follow_up(state, "financing_status", "cash buyer", _load_sample_properties())
        self.assertEqual(state.follow_up_question, "Do you consent to being contacted by a human sales agent about this inquiry?")
        state = workflow.resume_with_follow_up(state, "consent_to_contact", "yes", _load_sample_properties())
        self.assertEqual(state.status, "awaiting_human_review")

    def test_empty_property_result_handled_safely(self) -> None:
        workflow = _workflow()
        state = workflow.run(
            LeadRequirements.model_validate(
                {
                    "inquiry": "I am looking for a villa in Palma with a budget of €100,000.",
                    "budget_eur": 100000,
                    "preferred_locations": ["Palma de Mallorca"],
                    "property_type": "villa",
                    "purchase_timeline": "1-3 months",
                    "financing_status": "cash_buyer",
                    "consent_to_contact": True,
                }
            ),
            _load_sample_properties(),
        )
        self.assertEqual(state.property_matches, [])
        self.assertEqual(state.status, "awaiting_human_review")
        self.assertIsNotNone(state.recommendation)

    def test_complete_score_stored(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        self.assertIsNotNone(state.score_breakdown)
        self.assertEqual(state.score_breakdown.total, 100)

    def test_classification_stored(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        self.assertEqual(state.score_breakdown.classification, "hot")

    def test_recommendation_contains_source_ids_only_from_actual_matches(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        self.assertIn("MAL-001", state.recommendation)
        self.assertNotIn("MAL-002", state.recommendation)
        self.assertNotIn("MAL-003", state.recommendation)

    def test_human_review_gate_always_reached_before_approval(self) -> None:
        workflow = _workflow()
        state = workflow.run(_lead(), _load_sample_properties())
        self.assertEqual(state.status, "awaiting_human_review")
        self.assertIn("human_review_gate", state.step_history)
        approved = workflow.apply_human_decision(state, "approve")
        self.assertIn("human_decision", approved.step_history)
        self.assertTrue(approved.step_history.index("human_review_gate") < approved.step_history.index("human_decision"))

    def test_approval_with_consent(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        approved = _workflow().apply_human_decision(state, "approve")
        self.assertEqual(approved.status, "approved_for_follow_up")

    def test_approval_without_consent_closes_without_contact(self) -> None:
        state = _workflow().run(
            _lead(consent_to_contact=False),
            _load_sample_properties(),
        )
        approved = _workflow().apply_human_decision(state, "approve")
        self.assertEqual(approved.status, "closed_no_contact")
        self.assertTrue(any("contact" in warning.lower() for warning in approved.warnings))

    def test_edit_requires_nonblank_recommendation(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        with self.assertRaises(ValueError):
            _workflow().apply_human_decision(state, "edit", "   ")

    def test_valid_edited_recommendation(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        edited = _workflow().apply_human_decision(state, "edit", "Updated internal recommendation.")
        self.assertEqual(edited.status, "awaiting_human_review")
        self.assertEqual(edited.recommendation, "Updated internal recommendation.")

    def test_rejection(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        rejected = _workflow().apply_human_decision(state, "reject")
        self.assertEqual(rejected.status, "rejected")

    def test_invalid_decision(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        with self.assertRaises(ValueError):
            _workflow().apply_human_decision(state, "maybe")

    def test_no_external_action_is_executed(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        approved = _workflow().apply_human_decision(state, "approve")
        self.assertNotIn("sent", approved.model_dump())
        self.assertIn(approved.status, {"approved_for_follow_up", "closed_no_contact"})

    def test_ordered_step_history(self) -> None:
        state = _workflow().run(_lead(), _load_sample_properties())
        self.assertEqual(
            state.step_history,
            [
                "intake",
                "extract_requirements",
                "validate_requirements",
                "retrieve_properties",
                "score_lead",
                "prepare_recommendation",
                "human_review_gate",
            ],
        )

    def test_same_lead_produces_identical_output_on_repeated_runs(self) -> None:
        workflow = _workflow()
        first = workflow.run(_lead(), _load_sample_properties())
        second = workflow.run(_lead(), _load_sample_properties())
        self.assertEqual(first.model_dump(), second.model_dump())
