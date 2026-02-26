from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException

from agents import Agent, Runner, trace
from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.api.schemas.common import ResetRequest, ResetResponse
from backend.chats.admin_assistant.graph.snapshot import build_runtime_snapshot
from backend.chats.admin_assistant.state import (
    ADMIN_ASSISTANT_CONVERSATIONS,
    ensure_admin_assistant_state,
)
from backend.chats.shared.event_serialization import event_from_item
from backend.chats.shared.request_context import (
    CHANNEL_ADMIN_ASSISTANT,
    CONVERSATION_ID_CONTEXT,
    REQUEST_CHANNEL_CONTEXT,
)
from backend.chats.shared.state import RESPONSE_LANGUAGE_CONTEXT
from backend.domain.language_policy import detect_user_language

ADMIN_ASSISTANT_TRIAGE_AGENT_NAME = "Tech Team Assistant Triage"
ADMIN_ASSISTANT_RUNTIME_SNAPSHOT = build_runtime_snapshot()


def is_admin_assistant_triage_agent(agent: Agent[Any]) -> bool:
    return agent.name == ADMIN_ASSISTANT_TRIAGE_AGENT_NAME


async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = ensure_admin_assistant_state(conversation_id, ADMIN_ASSISTANT_RUNTIME_SNAPSHOT)

    async with state.lock:
        if (
            state.snapshot_id != ADMIN_ASSISTANT_RUNTIME_SNAPSHOT.snapshot_id
            and is_admin_assistant_triage_agent(state.current_agent)
        ):
            state.current_agent = ADMIN_ASSISTANT_RUNTIME_SNAPSHOT.triage_agent
            state.snapshot_id = ADMIN_ASSISTANT_RUNTIME_SNAPSHOT.snapshot_id

        state.response_language = detect_user_language(message, state.response_language)
        state.input_items.append({"content": message, "role": "user"})
        context_token = RESPONSE_LANGUAGE_CONTEXT.set(state.response_language)
        conversation_token = CONVERSATION_ID_CONTEXT.set(conversation_id)
        channel_token = REQUEST_CHANNEL_CONTEXT.set(CHANNEL_ADMIN_ASSISTANT)
        try:
            with trace("Help desk admin assistant chat", group_id=conversation_id):
                result = await Runner.run(state.current_agent, state.input_items)
        finally:
            REQUEST_CHANNEL_CONTEXT.reset(channel_token)
            CONVERSATION_ID_CONTEXT.reset(conversation_token)
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


async def reset(request: ResetRequest) -> ResetResponse:
    deleted = ADMIN_ASSISTANT_CONVERSATIONS.pop(request.conversation_id, None) is not None
    return ResetResponse(deleted=deleted)
