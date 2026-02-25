from __future__ import annotations

import re
from collections.abc import Callable

from language_policy import detect_user_language, translate_backend_text
from models import PublishedUseCaseSummary, UseCaseStep
from pydantic import BaseModel, Field

TICKET_ID_PATTERN = re.compile(r"\b[A-Z]{2,10}-\d{2,10}\b")
StepHandler = Callable[[UseCaseStep, dict[str, str], str], str]


class WorkflowExecutionResult(BaseModel):
    step_outputs: list[str] = Field(default_factory=list)

    def as_text(self) -> str:
        return "\n".join(self.step_outputs)


class WorkflowExecutionInput(BaseModel):
    use_case: PublishedUseCaseSummary
    ticket_context: str
    field_values: dict[str, str] = Field(default_factory=dict)


def execute_workflow(input_data: WorkflowExecutionInput) -> WorkflowExecutionResult:
    language = detect_user_language(input_data.ticket_context, None)
    resolved_fields = _resolve_fields(
        required_fields=input_data.use_case.definition.required_fields,
        ticket_context=input_data.ticket_context,
        field_values=input_data.field_values,
    )

    outputs: list[str] = []
    for step in input_data.use_case.definition.steps:
        outputs.append(_run_step(step=step, resolved_fields=resolved_fields, language=language))

    outputs.append(_closure_output(resolved_fields, language))
    return WorkflowExecutionResult(step_outputs=outputs)


def _resolve_fields(
    required_fields: list[str],
    ticket_context: str,
    field_values: dict[str, str],
) -> dict[str, str]:
    resolved = {key: value for key, value in field_values.items() if value.strip()}

    ticket_id_match = TICKET_ID_PATTERN.search(ticket_context.upper())
    if ticket_id_match and "ticket_id" not in resolved:
        resolved["ticket_id"] = ticket_id_match.group(0)

    for field_name in required_fields:
        if field_name not in resolved:
            resolved[field_name] = f"<missing:{field_name}>"

    return resolved


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
