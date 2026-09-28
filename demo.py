"""Command-line demo for the offline Chleo Lite prototype."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chleo.graph import ChleoWorkflow
from chleo.models import LeadRequirements, Property


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_properties() -> list[Property]:
    payload = _load_json(ROOT / "data" / "sample_properties.json")
    return [Property.model_validate(item) for item in payload]


def _load_leads() -> list[LeadRequirements]:
    payload = _load_json(ROOT / "data" / "sample_leads.json")
    return [LeadRequirements.model_validate(item) for item in payload]


def _build_lead_from_inquiry(inquiry: str) -> LeadRequirements:
    return LeadRequirements.model_validate(
        {
            "lead_id": "DEMO-CUSTOM",
            "inquiry": inquiry,
        }
    )


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def _print_block(label: str, value: str) -> None:
    print(f"{label}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline Chleo Lite demo.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--lead-id", default="LEAD-001", help="Load a fictional sample lead by ID.")
    group.add_argument("--inquiry", help="Process a custom fictional inquiry.")
    parser.add_argument(
        "--decision",
        choices=("approve", "reject"),
        help="Apply an explicit human decision after the workflow reaches review.",
    )
    args = parser.parse_args()

    properties = _load_properties()
    leads = _load_leads()

    if args.inquiry:
        lead = _build_lead_from_inquiry(args.inquiry)
    else:
        lead = next((item for item in leads if item.lead_id == args.lead_id), None)
        if lead is None:
            print(f"Error: unknown lead ID '{args.lead_id}'.", file=sys.stderr)
            return 1

    workflow = ChleoWorkflow()
    state = workflow.run(lead, properties)

    if args.decision:
        if state.status != "awaiting_human_review":
            print("Error: a human decision can only be applied after review.", file=sys.stderr)
            return 1
        state = workflow.apply_human_decision(state, args.decision)

    print("Chleo Lite offline demo")
    _print_block("Lead ID", state.lead.lead_id)
    _print_block("Workflow status", state.status)
    print("Extracted requirements:")
    print(f"  budget_eur: {state.lead.budget_eur}")
    print(f"  preferred_locations: {_format_list(state.lead.preferred_locations)}")
    print(f"  property_type: {state.lead.property_type}")
    print(f"  purchase_timeline: {state.lead.purchase_timeline}")
    print(f"  financing_status: {state.lead.financing_status}")
    print(f"  consent_to_contact: {state.lead.consent_to_contact}")
    _print_block("Missing fields", _format_list(state.missing_fields))
    if state.follow_up_question:
        _print_block("Follow-up question", state.follow_up_question)
    matched_ids = [match.source_id for match in state.property_matches]
    _print_block("Matched property IDs", _format_list(matched_ids))
    if state.score_breakdown is not None:
        _print_block(
            "Lead score and classification",
            f"{state.score_breakdown.total}/100 ({state.score_breakdown.classification})",
        )
    else:
        _print_block("Lead score and classification", "not available")
    _print_block("Internal recommendation", state.recommendation or "not available")
    _print_block("Human-review requirement", "mandatory before any customer contact")
    _print_block("Customer message sent", "no")
    _print_block("Step history", " -> ".join(state.step_history))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
