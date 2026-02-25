from __future__ import annotations

import asyncio
import json

from backend.api_internal.request_context import (
    CHANNEL_ADMIN_ASSISTANT,
    CHANNEL_USER_CHAT,
    CONVERSATION_ID_CONTEXT,
    REQUEST_CHANNEL_CONTEXT,
)
from backend.domain.models import TicketStatus
from backend.runtime.bootstrap import initialize_repositories
from backend.storage import CategoryRepository, TicketRepository, UseCaseRepository
from backend.workflows.tools import build_use_case_workflow_tool


def _build_repositories(tmp_path):
    db_path = tmp_path / "ticket-tool.db"
    category_repository = CategoryRepository(db_path=db_path)
    use_case_repository = UseCaseRepository(db_path=db_path)
    ticket_repository = TicketRepository(db_path=db_path)
    initialize_repositories(category_repository, use_case_repository, ticket_repository)
    return use_case_repository, ticket_repository


def _invoke_tool(tool, payload: dict[str, str]) -> str:
    raw_output = asyncio.run(tool.on_invoke_tool(None, json.dumps(payload, ensure_ascii=True)))
    return str(raw_output)


def test_use_case_workflow_tool_persists_ticket_in_user_chat_channel(tmp_path) -> None:
    use_case_repository, ticket_repository = _build_repositories(tmp_path)
    published_use_case = use_case_repository.list_published_use_cases()[0]
    tool = build_use_case_workflow_tool(published_use_case, ticket_repository=ticket_repository)

    conversation_token = CONVERSATION_ID_CONTEXT.set("ticket-tool-conversation")
    channel_token = REQUEST_CHANNEL_CONTEXT.set(CHANNEL_USER_CHAT)
    try:
        output = _invoke_tool(
            tool,
            {
                "ticket_context": "Please help with USDV-176285",
                "field_values_json": '{"requester_name":"Francois Emeriau"}',
            },
        )
    finally:
        REQUEST_CHANNEL_CONTEXT.reset(channel_token)
        CONVERSATION_ID_CONTEXT.reset(conversation_token)

    assert "USDV-176285" in output
    tickets = ticket_repository.list_tickets()
    assert len(tickets) == 1
    assert tickets[0].status == TicketStatus.RESOLVED
    detail = ticket_repository.get_ticket_detail(tickets[0].ticket_id)
    assert detail.conversation_id == "ticket-tool-conversation"
    assert any(field.field_name == "ticket_id" for field in detail.fields)


def test_use_case_workflow_tool_skips_ticket_persistence_outside_user_chat_channel(
    tmp_path,
) -> None:
    use_case_repository, ticket_repository = _build_repositories(tmp_path)
    published_use_case = use_case_repository.list_published_use_cases()[0]
    tool = build_use_case_workflow_tool(published_use_case, ticket_repository=ticket_repository)

    conversation_token = CONVERSATION_ID_CONTEXT.set("admin-assistant-conversation")
    channel_token = REQUEST_CHANNEL_CONTEXT.set(CHANNEL_ADMIN_ASSISTANT)
    try:
        _invoke_tool(
            tool,
            {
                "ticket_context": "Need help with USDV-176893",
                "field_values_json": '{"employee_name":"Ana Lopez"}',
            },
        )
    finally:
        REQUEST_CHANNEL_CONTEXT.reset(channel_token)
        CONVERSATION_ID_CONTEXT.reset(conversation_token)

    assert ticket_repository.list_tickets() == []
