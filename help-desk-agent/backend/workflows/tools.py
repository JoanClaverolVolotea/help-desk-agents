from __future__ import annotations

import json
from typing import Any

from agents import function_tool
from backend.domain.models import PublishedUseCaseSummary
from backend.workflows.executor import WorkflowExecutionInput, execute_workflow


def build_use_case_workflow_tool(use_case: PublishedUseCaseSummary):
    description = (
        "Execute deterministic workflow steps for this use case. "
        "Always call this tool once after collecting required fields."
    )

    @function_tool(
        name_override="execute_use_case_workflow",
        description_override=description,
    )
    def execute_use_case_workflow(
        ticket_context: str,
        field_values_json: str = "{}",
    ) -> str:
        field_values = _parse_field_values(field_values_json)
        result = execute_workflow(
            WorkflowExecutionInput(
                use_case=use_case,
                ticket_context=ticket_context,
                field_values=field_values,
            )
        )
        return result.as_text()

    return execute_use_case_workflow


def _parse_field_values(raw_json: str) -> dict[str, str]:
    raw_value: Any
    try:
        raw_value = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}

    if not isinstance(raw_value, dict):
        return {}

    parsed: dict[str, str] = {}
    for key, value in raw_value.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            cleaned_value = value.strip()
        else:
            cleaned_value = str(value)
        if cleaned_value:
            parsed[key.strip()] = cleaned_value
    return parsed
