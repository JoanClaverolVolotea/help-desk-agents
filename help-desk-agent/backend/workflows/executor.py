from __future__ import annotations

import re
from collections.abc import Callable

from pydantic import BaseModel, Field

from backend.domain.language_policy import detect_user_language, translate_backend_text
from backend.domain.models import (
    PublishedUseCaseSummary,
    TicketFieldSource,
    UseCaseStep,
)

TICKET_ID_PATTERN = re.compile(r"\b[A-Z]{2,10}-\d{2,10}\b")
StepHandler = Callable[[UseCaseStep, dict[str, str], str], str]


class WorkflowResolvedField(BaseModel):
    field_name: str
    field_value: str
    source: TicketFieldSource
    is_required: bool


class WorkflowStepRecord(BaseModel):
    step_order: int
    step_id: str
    output_text: str


class WorkflowExecutionResult(BaseModel):
    step_outputs: list[str] = Field(default_factory=list)
    resolved_fields: list[WorkflowResolvedField] = Field(default_factory=list)
    step_records: list[WorkflowStepRecord] = Field(default_factory=list)
    closure_output: str = ""
    language: str = "en"
    external_ticket_id: str | None = None

    def as_text(self) -> str:
        return "\n".join(self.step_outputs)


class WorkflowExecutionInput(BaseModel):
    use_case: PublishedUseCaseSummary
    ticket_context: str
    field_values: dict[str, str] = Field(default_factory=dict)


def execute_workflow(input_data: WorkflowExecutionInput) -> WorkflowExecutionResult:
    language = detect_user_language(input_data.ticket_context, None)
    resolved_fields, field_sources = _resolve_fields(
        required_fields=input_data.use_case.definition.required_fields,
        ticket_context=input_data.ticket_context,
        field_values=input_data.field_values,
    )

    outputs: list[str] = []
    step_records: list[WorkflowStepRecord] = []
    for step_index, step in enumerate(input_data.use_case.definition.steps, start=1):
        step_output = _run_step(step=step, resolved_fields=resolved_fields, language=language)
        outputs.append(step_output)
        step_records.append(
            WorkflowStepRecord(
                step_order=step_index,
                step_id=step.step_id,
                output_text=step_output,
            )
        )

    closure_output = _closure_output(resolved_fields, language)
    outputs.append(closure_output)
    required_field_names = set(input_data.use_case.definition.required_fields)
    ordered_field_names = _ordered_field_names(
        required_fields=input_data.use_case.definition.required_fields,
        resolved_fields=resolved_fields,
    )
    resolved_field_items = [
        WorkflowResolvedField(
            field_name=field_name,
            field_value=resolved_fields[field_name],
            source=field_sources[field_name],
            is_required=field_name in required_field_names,
        )
        for field_name in ordered_field_names
    ]
    external_ticket_id = _external_ticket_id(resolved_fields)

    return WorkflowExecutionResult(
        step_outputs=outputs,
        resolved_fields=resolved_field_items,
        step_records=step_records,
        closure_output=closure_output,
        language=language,
        external_ticket_id=external_ticket_id,
    )


def _resolve_fields(
    required_fields: list[str],
    ticket_context: str,
    field_values: dict[str, str],
) -> tuple[dict[str, str], dict[str, TicketFieldSource]]:
    resolved: dict[str, str] = {}
    sources: dict[str, TicketFieldSource] = {}
    for key, value in field_values.items():
        normalized_key = key.strip()
        normalized_value = value.strip()
        if not normalized_key or not normalized_value:
            continue
        resolved[normalized_key] = normalized_value
        sources[normalized_key] = TicketFieldSource.PROVIDED

    ticket_id_match = TICKET_ID_PATTERN.search(ticket_context.upper())
    if ticket_id_match and "ticket_id" not in resolved:
        resolved["ticket_id"] = ticket_id_match.group(0)
        sources["ticket_id"] = TicketFieldSource.DERIVED

    for field_name in required_fields:
        if field_name not in resolved:
            resolved[field_name] = f"<missing:{field_name}>"
            sources[field_name] = TicketFieldSource.MISSING

    return resolved, sources


def _ordered_field_names(required_fields: list[str], resolved_fields: dict[str, str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for field_name in required_fields:
        if field_name in resolved_fields and field_name not in seen:
            ordered.append(field_name)
            seen.add(field_name)
    for field_name in sorted(resolved_fields.keys()):
        if field_name not in seen:
            ordered.append(field_name)
            seen.add(field_name)
    return ordered


def _external_ticket_id(resolved_fields: dict[str, str]) -> str | None:
    ticket_id = resolved_fields.get("ticket_id")
    if ticket_id is None:
        return None
    if ticket_id.startswith("<missing:") and ticket_id.endswith(">"):
        return None
    return ticket_id


def _run_step(step: UseCaseStep, resolved_fields: dict[str, str], language: str) -> str:
    handler = STEP_HANDLERS.get(step.step_id)
    if handler is None:
        return translate_backend_text("workflow_unsupported_step", language, step_id=step.step_id)
    return handler(step, resolved_fields, language)


def _closure_output(resolved_fields: dict[str, str], language: str) -> str:
    ticket_id = resolved_fields.get("ticket_id", "<missing:ticket_id>")
    return translate_backend_text("workflow_closure", language, ticket_id=ticket_id)


def _ticket_id(resolved_fields: dict[str, str]) -> str:
    return resolved_fields.get("ticket_id", "<missing:ticket_id>")


def _requester_name(resolved_fields: dict[str, str]) -> str:
    return resolved_fields.get("requester_name", "<missing:requester_name>")


def _employee_name(resolved_fields: dict[str, str]) -> str:
    return resolved_fields.get("employee_name", "<missing:employee_name>")


def _handle_verify_requester(
    step: UseCaseStep,
    resolved_fields: dict[str, str],
    language: str,
) -> str:
    del step
    return translate_backend_text(
        "workflow_verify_requester",
        language,
        ticket_id=_ticket_id(resolved_fields),
        requester_name=_requester_name(resolved_fields),
    )


def _handle_reset_ecrew_access(
    step: UseCaseStep,
    resolved_fields: dict[str, str],
    language: str,
) -> str:
    del step
    return translate_backend_text(
        "workflow_reset_ecrew_access",
        language,
        ticket_id=_ticket_id(resolved_fields),
    )


def _handle_provision_email(
    step: UseCaseStep,
    resolved_fields: dict[str, str],
    language: str,
) -> str:
    del step
    mailbox = _employee_name(resolved_fields).lower().replace(" ", ".")
    return translate_backend_text(
        "workflow_provision_email",
        language,
        mailbox=mailbox,
        ticket_id=_ticket_id(resolved_fields),
    )


def _handle_provision_efos(
    step: UseCaseStep,
    resolved_fields: dict[str, str],
    language: str,
) -> str:
    del step
    return translate_backend_text(
        "workflow_provision_efos",
        language,
        employee_name=_employee_name(resolved_fields),
        ticket_id=_ticket_id(resolved_fields),
    )


def _handle_provision_pelesys(
    step: UseCaseStep,
    resolved_fields: dict[str, str],
    language: str,
) -> str:
    del step
    return translate_backend_text(
        "workflow_provision_pelesys",
        language,
        employee_name=_employee_name(resolved_fields),
        ticket_id=_ticket_id(resolved_fields),
    )


def _handle_append_resolution_note(
    step: UseCaseStep,
    resolved_fields: dict[str, str],
    language: str,
) -> str:
    del resolved_fields
    note = step.params.get(
        "note",
        translate_backend_text("workflow_default_resolution_note", language),
    ).strip()
    return f"[append_resolution_note] {note}"


def _handle_manual_instruction(
    step: UseCaseStep,
    resolved_fields: dict[str, str],
    language: str,
) -> str:
    del resolved_fields
    instruction = step.params.get(
        "instruction",
        translate_backend_text("workflow_default_manual_instruction", language),
    ).strip()
    return f"[manual_instruction] {instruction}"


STEP_HANDLERS: dict[str, StepHandler] = {
    "verify_requester": _handle_verify_requester,
    "reset_ecrew_access": _handle_reset_ecrew_access,
    "provision_email": _handle_provision_email,
    "provision_efos": _handle_provision_efos,
    "provision_pelesys": _handle_provision_pelesys,
    "append_resolution_note": _handle_append_resolution_note,
    "manual_instruction": _handle_manual_instruction,
}
