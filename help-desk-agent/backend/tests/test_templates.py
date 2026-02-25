from __future__ import annotations

from models import CategoryDefinitionInput, UseCaseDefinitionInput, UseCaseStep
from templates import validate_category_definition, validate_use_case_definition


def test_category_validation_rejects_unknown_step() -> None:
    definition = CategoryDefinitionInput(
        display_name="Access Category",
        description="Category for account fixes.",
        allowed_step_ids=["verify_requester", "unknown_step"],
        default_handoff_description="Handles account reset requests.",
        default_routing_description="Route account reset tickets here.",
        default_required_fields=["ticket_id", "requester_name"],
        default_steps=[UseCaseStep(step_id="verify_requester", params={})],
    )

    errors = validate_category_definition(definition)
    assert errors
    assert any("unknown step" in error.lower() for error in errors)
    assert all("bilingual" not in error.lower() for error in errors)


def test_use_case_validation_rejects_disallowed_steps() -> None:
    definition = UseCaseDefinitionInput(
        display_name="Reset Account",
        handoff_description="Handles account reset.",
        routing_description="Use for account reset tickets.",
        required_fields=["ticket_id", "employee_email"],
        steps=[
            UseCaseStep(step_id="verify_requester", params={}),
            UseCaseStep(step_id="provision_email", params={}),
        ],
    )

    errors = validate_use_case_definition(
        definition,
        allowed_step_ids={"verify_requester", "reset_ecrew_access"},
    )

    assert errors
    assert any("not allowed" in error.lower() for error in errors)
    assert all("bilingual" not in error.lower() for error in errors)


def test_use_case_validation_accepts_free_form_required_fields() -> None:
    definition = UseCaseDefinitionInput(
        display_name="Desktop onboarding",
        handoff_description="Handles desktop setup.",
        routing_description="Use for desktop setup tickets.",
        required_fields=["ticket_id", "new_hire_code", "floor_location"],
        steps=[UseCaseStep(step_id="manual_instruction", params={"instruction": "done"})],
    )

    errors = validate_use_case_definition(definition, allowed_step_ids={"manual_instruction"})
    assert errors == []
