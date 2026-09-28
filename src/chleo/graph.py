"""Offline orchestration for the Chleo Lite lead-qualification workflow.

LangGraph is the planned production orchestration framework, but this phase
uses a local state-machine fallback because the dependency is unavailable
offline. The workflow remains deterministic, testable, and free of side
effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import LeadRequirements, Property, WorkflowState
from .nodes import (
    apply_follow_up_value,
    extract_requirements,
    generate_follow_up_question,
    handle_human_decision,
    human_review_gate,
    intake_node,
    prepare_recommendation_node,
    retrieve_properties_node,
    score_lead_node,
    validate_requirements,
)


@dataclass(frozen=True)
class ChleoWorkflow:
    """Deterministic local fallback for the planned agent workflow."""

    default_top_k: int = 3

    def run(
        self,
        lead: LeadRequirements,
        properties: Sequence[Property],
    ) -> WorkflowState:
        """Run intake, extraction, validation and the conditional offline flow."""

        catalogue = list(properties)
        state = intake_node(lead)
        state = extract_requirements(state, catalogue)
        state = validate_requirements(state)
        if state.missing_fields:
            return generate_follow_up_question(state)
        return self._complete_after_validation(state, catalogue)

    def resume_with_follow_up(
        self,
        state: WorkflowState,
        field: str,
        value: object,
        properties: Sequence[Property],
    ) -> WorkflowState:
        """Apply one user response and continue the offline workflow."""

        catalogue = list(properties)
        normalized_field = field.strip()
        if normalized_field not in state.missing_fields:
            raise ValueError(f"Field is not currently missing: {field}")

        updated_lead = apply_follow_up_value(state.lead, normalized_field, value, catalogue)
        next_state = state.model_copy(deep=True, update={"lead": updated_lead})
        next_state = extract_requirements(next_state, catalogue)
        next_state = validate_requirements(next_state)
        if next_state.missing_fields:
            return generate_follow_up_question(next_state)
        return self._complete_after_validation(next_state, catalogue)

    def apply_human_decision(
        self,
        state: WorkflowState,
        decision: str,
        edited_recommendation: str | None = None,
    ) -> WorkflowState:
        """Apply a human review decision without performing any external action."""

        return handle_human_decision(state, decision, edited_recommendation)

    def _complete_after_validation(
        self,
        state: WorkflowState,
        properties: Sequence[Property],
    ) -> WorkflowState:
        """Execute retrieval, scoring, recommendation and human review pause."""

        catalogue = list(properties)
        next_state = retrieve_properties_node(state, catalogue, top_k=self.default_top_k)
        next_state = score_lead_node(next_state, catalogue)
        next_state = prepare_recommendation_node(next_state)
        next_state = human_review_gate(next_state)
        return next_state
