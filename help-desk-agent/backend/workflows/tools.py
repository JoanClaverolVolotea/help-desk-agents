from __future__ import annotations

import json
from typing import Any

from agents import function_tool
from backend.chats.shared.request_context import (
    CHANNEL_USER_ASSISTANT,
    current_conversation_id,
    current_request_channel,
)
from backend.domain.language_policy import detect_user_language, translate_backend_text
from backend.domain.models import PublishedUseCaseSummary
from backend.storage.ticket_repository import (
    TicketEventWrite,
    TicketFieldWrite,
    TicketRepository,
    TicketStepWrite,
)
from backend.workflows.executor import (
    TICKET_ID_PATTERN,
    WorkflowExecutionInput,
    execute_workflow,
)


def build_use_case_workflow_tool(
    use_case: PublishedUseCaseSummary,
    ticket_repository: TicketRepository | None = None,
):
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
        request_channel = current_request_channel()
        should_persist_ticket = (
            request_channel == CHANNEL_USER_ASSISTANT and ticket_repository is not None
        )
        specialist_agent_name = f"{use_case.display_name} Specialist"

        ticket_id: str | None = None
        if should_persist_ticket and ticket_repository is not None:
            ticket_id = ticket_repository.start_workflow_execution(
                conversation_id=current_conversation_id(),
                use_case_id=use_case.use_case_id,
                language=detect_user_language(ticket_context, None),
                ticket_context=ticket_context,
                external_ticket_id=_infer_external_ticket_id(ticket_context, field_values),
                agent_name=specialist_agent_name,
            )

        try:
            result = execute_workflow(
                WorkflowExecutionInput(
                    use_case=use_case,
                    ticket_context=ticket_context,
                    field_values=field_values,
                )
            )
            if should_persist_ticket and ticket_id and ticket_repository is not None:
                fields = [
                    TicketFieldWrite(
                        field_name=item.field_name,
                        field_value=item.field_value,
                        is_required=item.is_required,
                        source=item.source,
                    )
                    for item in result.resolved_fields
                ]
                steps = [
                    TicketStepWrite(
                        step_order=item.step_order,
                        step_id=item.step_id,
                        output_text=item.output_text,
                    )
                    for item in result.step_records
                ]
                events = [
                    TicketEventWrite(
                        event_type="workflow_completed",
                        agent_name=specialist_agent_name,
                        payload_json=json.dumps(
                            {
                                "language": result.language,
                                "closure_output": result.closure_output,
                                "step_output_count": len(result.step_outputs),
                            },
                            ensure_ascii=True,
                        ),
                    )
                ]
                ticket_repository.complete_workflow_execution_success(
                    ticket_id=ticket_id,
                    fields=fields,
                    steps=steps,
                    events=events,
                )
            ticket_reference = result.external_ticket_id or "<missing:ticket_id>"
            pending_review_note = translate_backend_text(
                "workflow_pending_review_note",
                result.language,
                ticket_id=ticket_reference,
            )
            return f"{result.as_text()}\n{pending_review_note}"
        except Exception as exc:
            if should_persist_ticket and ticket_id and ticket_repository is not None:
                ticket_repository.complete_workflow_execution_failure(
                    ticket_id=ticket_id,
                    error_message=str(exc),
                    events=[
                        TicketEventWrite(
                            event_type="workflow_failed",
                            agent_name=specialist_agent_name,
                            payload_json=json.dumps(
                                {"error": str(exc)},
                                ensure_ascii=True,
                            ),
                        )
                    ],
                )
            raise

    return execute_use_case_workflow


def _infer_external_ticket_id(ticket_context: str, field_values: dict[str, str]) -> str | None:
    ticket_id = field_values.get("ticket_id", "").strip()
    if ticket_id:
        return ticket_id
    ticket_id_match = TICKET_ID_PATTERN.search(ticket_context.upper())
    if ticket_id_match is None:
        return None
    return ticket_id_match.group(0)


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
