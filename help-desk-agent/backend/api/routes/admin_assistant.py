from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from agents import Runner, trace
from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.api.schemas.common import ResetRequest, ResetResponse
from backend.api_internal.assistant_agents import build_admin_assistant_triage_agent
from backend.api_internal.conversation_state import (
    ADMIN_ASSISTANT_CONVERSATIONS,
    RESPONSE_LANGUAGE_CONTEXT,
    ensure_admin_assistant_state,
)
from backend.api_internal.event_serialization import event_from_item
from backend.domain.language_policy import detect_user_language

router = APIRouter()
ADMIN_ASSISTANT_TRIAGE_AGENT = build_admin_assistant_triage_agent()


async def _admin_assistant_chat_impl(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = ensure_admin_assistant_state(conversation_id, ADMIN_ASSISTANT_TRIAGE_AGENT)

    async with state.lock:
        state.response_language = detect_user_language(message, state.response_language)
        state.input_items.append({"content": message, "role": "user"})
        context_token = RESPONSE_LANGUAGE_CONTEXT.set(state.response_language)
        try:
            with trace("Help desk admin assistant chat", group_id=conversation_id):
                result = await Runner.run(state.current_agent, state.input_items)
        finally:
            RESPONSE_LANGUAGE_CONTEXT.reset(context_token)

        events = []
        for item in result.new_items:
            event = event_from_item(item, state.response_language)
            if event is not None:
                events.append(event)

        state.input_items = result.to_input_list()
        state.current_agent = result.last_agent

        return ChatResponse(
            conversation_id=conversation_id,
            current_agent=state.current_agent.name,
            events=events,
        )


async def _admin_assistant_reset_impl(request: ResetRequest) -> ResetResponse:
    deleted = ADMIN_ASSISTANT_CONVERSATIONS.pop(request.conversation_id, None) is not None
    return ResetResponse(deleted=deleted)


@router.post("/api/v2/admin/assistant/chat", response_model=ChatResponse)
async def admin_assistant_chat_v2(request: ChatRequest) -> ChatResponse:
    return await _admin_assistant_chat_impl(request)


@router.post("/api/v2/admin/assistant/reset", response_model=ResetResponse)
async def admin_assistant_reset_v2(request: ResetRequest) -> ResetResponse:
    return await _admin_assistant_reset_impl(request)
