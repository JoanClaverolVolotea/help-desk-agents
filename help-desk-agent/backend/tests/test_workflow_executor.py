from __future__ import annotations

from backend.domain.models import (
    PublishedUseCaseSummary,
    TicketFieldSource,
    UseCaseDefinitionPublished,
)
from backend.domain.templates import seed_category_definitions, seed_use_case_definitions
from backend.workflows.executor import WorkflowExecutionInput, execute_workflow


def _build_summary() -> PublishedUseCaseSummary:
    draft = seed_use_case_definitions()[0].definition
    published_definition = UseCaseDefinitionPublished(
        version_number=1,
        **draft.model_dump(),
    )
    return PublishedUseCaseSummary(
        use_case_id="use-case-1",
        slug="reset-access",
        display_name=draft.display_name,
        category_id="category-1",
        category_version_number=1,
        version_number=1,
        definition=published_definition,
    )


def test_workflow_executor_runs_steps_deterministically_in_english() -> None:
    summary = _build_summary()
    result = execute_workflow(
        WorkflowExecutionInput(
            use_case=summary,
            ticket_context="Please help with USDV-176285",
            field_values={"requester_name": "Francois Emeriau"},
        )
    )

    text = result.as_text()
    assert "verify_requester" in text
    assert "reset_ecrew_access" in text
    assert "USDV-176285" in text
    assert "Workflow completed with deterministic execution" in text
    assert "Flujo completado con ejecucion determinista" not in text
    assert "EN:" not in text
    assert "ES:" not in text


def test_workflow_executor_runs_steps_deterministically_in_spanish() -> None:
    summary = _build_summary()
    result = execute_workflow(
        WorkflowExecutionInput(
            use_case=summary,
            ticket_context="Necesito ayuda con USDV-176285",
            field_values={"requester_name": "Francois Emeriau"},
        )
    )

    text = result.as_text()
    assert "verify_requester" in text
    assert "reset_ecrew_access" in text
    assert "USDV-176285" in text
    assert "Flujo completado con ejecucion determinista" in text
    assert "Workflow completed with deterministic execution" not in text
    assert "EN:" not in text
    assert "ES:" not in text


def test_workflow_executor_tracks_field_sources_and_step_records() -> None:
    summary = _build_summary()
    result = execute_workflow(
        WorkflowExecutionInput(
            use_case=summary,
            ticket_context="Please help with USDV-176285",
            field_values={"requester_name": "Francois Emeriau"},
        )
    )

    fields_by_name = {field.field_name: field for field in result.resolved_fields}
    assert fields_by_name["ticket_id"].source == TicketFieldSource.DERIVED
    assert fields_by_name["requester_name"].source == TicketFieldSource.PROVIDED
    assert all(step.step_order >= 1 for step in result.step_records)
    assert result.closure_output.startswith("[closure]")


def test_seed_templates_include_case_aligned_required_fields() -> None:
    categories = dict(seed_category_definitions())
    assert categories["access-reset"].default_required_fields == [
        "ticket_id",
        "requester_name",
        "requester_id",
        "affected_platforms",
    ]
    assert categories["employee-onboarding"].default_required_fields == [
        "ticket_id",
        "requester_name",
        "employee_name",
        "employee_batch",
        "target_systems",
    ]

    use_cases = {seed.slug: seed.definition for seed in seed_use_case_definitions()}
    assert use_cases["reset-acceso-ecrew"].required_fields == [
        "ticket_id",
        "requester_name",
        "requester_id",
        "affected_platforms",
    ]
    assert use_cases["alta-email-efos-pelesys"].required_fields == [
        "ticket_id",
        "requester_name",
        "employee_name",
        "employee_batch",
        "target_systems",
    ]


def test_seed_use_case_routing_descriptions_reference_case_examples() -> None:
    use_cases = {seed.slug: seed.definition for seed in seed_use_case_definitions()}
    assert "USDV-176285" in use_cases["reset-acceso-ecrew"].routing_description
    assert "USDV-176893" in use_cases["alta-email-efos-pelesys"].routing_description
