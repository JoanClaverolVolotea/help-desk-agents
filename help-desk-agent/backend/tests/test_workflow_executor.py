from __future__ import annotations

from backend.domain.models import PublishedUseCaseSummary, UseCaseDefinitionPublished
from backend.domain.templates import seed_use_case_definitions
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
