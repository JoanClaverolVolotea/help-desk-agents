from __future__ import annotations

from backend.chats.user_assistant.bootstrap import initialize_repositories
from backend.domain.models import TicketFieldSource, TicketStatus
from backend.storage import CategoryRepository, TicketRepository, UseCaseRepository
from backend.storage.ticket_repository import TicketEventWrite, TicketFieldWrite, TicketStepWrite


def _build_repositories(tmp_path):
    db_path = tmp_path / "ticket-repository.db"
    category_repository = CategoryRepository(db_path=db_path)
    use_case_repository = UseCaseRepository(db_path=db_path)
    ticket_repository = TicketRepository(db_path=db_path)
    initialize_repositories(category_repository, use_case_repository, ticket_repository)
    return category_repository, use_case_repository, ticket_repository


def test_ticket_repository_records_successful_workflow_execution(tmp_path) -> None:
    _, use_case_repository, ticket_repository = _build_repositories(tmp_path)
    use_case = use_case_repository.list_use_cases(include_archived=False)[0]

    ticket_id = ticket_repository.start_workflow_execution(
        conversation_id="conversation-success",
        use_case_id=use_case.use_case_id,
        language="en",
        ticket_context="Please help with USDV-176285",
        external_ticket_id="USDV-176285",
        agent_name="Reset de acceso eCrew Specialist",
    )
    ticket_repository.complete_workflow_execution_success(
        ticket_id=ticket_id,
        fields=[
            TicketFieldWrite(
                field_name="ticket_id",
                field_value="USDV-176285",
                is_required=True,
                source=TicketFieldSource.PROVIDED,
            ),
            TicketFieldWrite(
                field_name="requester_name",
                field_value="Francois Emeriau",
                is_required=True,
                source=TicketFieldSource.PROVIDED,
            ),
        ],
        steps=[
            TicketStepWrite(
                step_order=1,
                step_id="verify_requester",
                output_text="Requester verified.",
            ),
            TicketStepWrite(
                step_order=2,
                step_id="reset_ecrew_access",
                output_text="Account reset complete.",
            ),
        ],
        events=[
            TicketEventWrite(
                event_type="workflow_completed",
                agent_name="Reset de acceso eCrew Specialist",
                payload_json='{"result":"ok"}',
            )
        ],
    )

    detail = ticket_repository.get_ticket_detail(ticket_id)
    assert detail.status == TicketStatus.RESOLVED
    assert detail.external_ticket_id == "USDV-176285"
    assert [item.status for item in detail.status_history] == [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
    ]
    assert len(detail.fields) == 2
    assert len(detail.steps) == 2
    assert any(item.event_type == "workflow_completed" for item in detail.events)

    listed = ticket_repository.list_tickets(status=TicketStatus.RESOLVED)
    assert any(item.ticket_id == ticket_id for item in listed)


def test_ticket_repository_keeps_in_progress_after_failure(tmp_path) -> None:
    _, use_case_repository, ticket_repository = _build_repositories(tmp_path)
    use_case = use_case_repository.list_use_cases(include_archived=False)[0]

    ticket_id = ticket_repository.start_workflow_execution(
        conversation_id="conversation-failure",
        use_case_id=use_case.use_case_id,
        language="en",
        ticket_context="Please help with USDV-176893",
        external_ticket_id="USDV-176893",
    )
    ticket_repository.complete_workflow_execution_failure(
        ticket_id=ticket_id,
        error_message="Workflow failed on a deterministic step.",
        events=[
            TicketEventWrite(
                event_type="workflow_failed",
                payload_json='{"error":"step failure"}',
            )
        ],
    )

    detail = ticket_repository.get_ticket_detail(ticket_id)
    assert detail.status == TicketStatus.IN_PROGRESS
    assert detail.error_message == "Workflow failed on a deterministic step."
    assert detail.status_history[-1].status == TicketStatus.IN_PROGRESS
    assert any(item.event_type == "workflow_failed" for item in detail.events)
