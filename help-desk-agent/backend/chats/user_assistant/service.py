from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

import backend.api.deps as deps
from agents import Agent, Runner, trace
from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.api.schemas.common import ResetRequest, ResetResponse
from backend.chats.shared.event_serialization import event_from_item, ndjson_line
from backend.chats.shared.request_context import (
    CHANNEL_USER_ASSISTANT,
    CONVERSATION_ID_CONTEXT,
    REQUEST_CHANNEL_CONTEXT,
)
from backend.chats.shared.state import RESPONSE_LANGUAGE_CONTEXT
from backend.chats.user_assistant.bootstrap import (
    build_snapshot_from_repository,
    reseed_defaults,
)
from backend.chats.user_assistant.state import (
    USER_ASSISTANT_CONVERSATIONS,
    ensure_user_assistant_state,
)
from backend.domain.language_policy import detect_user_language
from backend.domain.models import (
    CategoryDetail,
    ReseedDefaultsResponse,
    ReseedDeletedCounts,
    ReseedSeededCounts,
)

USER_ASSISTANT_TRIAGE_AGENT_NAME = "Help Desk Triage Agent"


def is_user_assistant_triage_agent(agent: Agent[Any]) -> bool:
    return agent.name == USER_ASSISTANT_TRIAGE_AGENT_NAME


async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = ensure_user_assistant_state(
        conversation_id,
        deps.USER_ASSISTANT_RUNTIME_SNAPSHOT,
    )

    async with state.lock:
        if (
            state.snapshot_id != deps.USER_ASSISTANT_RUNTIME_SNAPSHOT.snapshot_id
            and is_user_assistant_triage_agent(state.current_agent)
        ):
            state.current_agent = deps.USER_ASSISTANT_RUNTIME_SNAPSHOT.triage_agent
            state.snapshot_id = deps.USER_ASSISTANT_RUNTIME_SNAPSHOT.snapshot_id

        state.response_language = detect_user_language(message, state.response_language)
        state.input_items.append({"content": message, "role": "user"})
        context_token = RESPONSE_LANGUAGE_CONTEXT.set(state.response_language)
        conversation_token = CONVERSATION_ID_CONTEXT.set(conversation_id)
        channel_token = REQUEST_CHANNEL_CONTEXT.set(CHANNEL_USER_ASSISTANT)
        try:
            with trace("Help desk web chat", group_id=conversation_id):
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


async def chat_stream(request: ChatRequest) -> StreamingResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = ensure_user_assistant_state(
        conversation_id,
        deps.USER_ASSISTANT_RUNTIME_SNAPSHOT,
    )

    async def stream_events() -> AsyncIterator[str]:
        async with state.lock:
            if (
                state.snapshot_id != deps.USER_ASSISTANT_RUNTIME_SNAPSHOT.snapshot_id
                and is_user_assistant_triage_agent(state.current_agent)
            ):
                state.current_agent = deps.USER_ASSISTANT_RUNTIME_SNAPSHOT.triage_agent
                state.snapshot_id = deps.USER_ASSISTANT_RUNTIME_SNAPSHOT.snapshot_id

            state.response_language = detect_user_language(message, state.response_language)
            state.input_items.append({"content": message, "role": "user"})
            yield ndjson_line(
                {
                    "type": "start",
                    "conversation_id": conversation_id,
                    "current_agent": state.current_agent.name,
                }
            )

            context_token = RESPONSE_LANGUAGE_CONTEXT.set(state.response_language)
            conversation_token = CONVERSATION_ID_CONTEXT.set(conversation_id)
            channel_token = REQUEST_CHANNEL_CONTEXT.set(CHANNEL_USER_ASSISTANT)
            try:
                with trace("Help desk web chat streamed", group_id=conversation_id):
                    streamed_result = Runner.run_streamed(state.current_agent, state.input_items)
                    try:
                        async for stream_event in streamed_result.stream_events():
                            if stream_event.type == "agent_updated_stream_event":
                                yield ndjson_line(
                                    {
                                        "type": "agent_updated",
                                        "agent": stream_event.new_agent.name,
                                    }
                                )
                                continue

                            if stream_event.type == "raw_response_event":
                                raw_event = stream_event.data
                                if getattr(raw_event, "type", "") == "response.output_text.delta":
                                    delta = getattr(raw_event, "delta", "")
                                    if delta:
                                        yield ndjson_line(
                                            {
                                                "type": "text_delta",
                                                "delta": delta,
                                            }
                                        )
                                continue

                            if stream_event.type == "run_item_stream_event":
                                run_event = event_from_item(
                                    stream_event.item,
                                    state.response_language,
                                )
                                if run_event is None:
                                    continue
                                yield ndjson_line(
                                    {
                                        "type": "event",
                                        "event": run_event.model_dump(),
                                    }
                                )
                    except Exception as exc:
                        yield ndjson_line({"type": "error", "detail": str(exc)})
                        return
            finally:
                REQUEST_CHANNEL_CONTEXT.reset(channel_token)
                CONVERSATION_ID_CONTEXT.reset(conversation_token)
                RESPONSE_LANGUAGE_CONTEXT.reset(context_token)

            state.input_items = streamed_result.to_input_list()
            state.current_agent = streamed_result.last_agent
            yield ndjson_line(
                {
                    "type": "final",
                    "conversation_id": conversation_id,
                    "current_agent": state.current_agent.name,
                }
            )

    return StreamingResponse(stream_events(), media_type="application/x-ndjson")


async def reset(request: ResetRequest) -> ResetResponse:
    deleted = USER_ASSISTANT_CONVERSATIONS.pop(request.conversation_id, None) is not None
    return ResetResponse(deleted=deleted)


async def refresh_user_assistant_runtime_snapshot() -> None:
    async with deps.USER_ASSISTANT_RUNTIME_LOCK:
        deps.USER_ASSISTANT_RUNTIME_SNAPSHOT = build_snapshot_from_repository(
            deps.USE_CASE_REPOSITORY,
            deps.TICKET_REPOSITORY,
        )


async def publish_category_and_sync(category_id: str) -> CategoryDetail:
    detail = deps.CATEGORY_REPOSITORY.publish_draft(category_id)
    if detail.published_definition is not None:
        deps.USE_CASE_REPOSITORY.create_or_update_default_use_case_for_category(detail)
    await refresh_user_assistant_runtime_snapshot()
    return detail


async def archive_category_and_sync(category_id: str) -> None:
    deps.CATEGORY_REPOSITORY.archive_category(category_id)
    deps.USE_CASE_REPOSITORY.archive_default_use_case_for_category(category_id)
    await refresh_user_assistant_runtime_snapshot()


async def restore_category_and_sync(category_id: str) -> None:
    detail = deps.CATEGORY_REPOSITORY.restore_category(category_id)
    if detail.published_definition is not None:
        deps.USE_CASE_REPOSITORY.create_or_update_default_use_case_for_category(detail)
    await refresh_user_assistant_runtime_snapshot()


async def reseed_defaults_and_refresh_runtime() -> ReseedDefaultsResponse:
    async with deps.USER_ASSISTANT_RUNTIME_LOCK:
        deleted_counts, seeded_counts = reseed_defaults(
            deps.CATEGORY_REPOSITORY,
            deps.USE_CASE_REPOSITORY,
            deps.TICKET_REPOSITORY,
        )
        deps.USER_ASSISTANT_RUNTIME_SNAPSHOT = build_snapshot_from_repository(
            deps.USE_CASE_REPOSITORY,
            deps.TICKET_REPOSITORY,
        )

    return ReseedDefaultsResponse(
        success=True,
        deleted_counts=ReseedDeletedCounts(**deleted_counts),
        seeded_counts=ReseedSeededCounts(**seeded_counts),
    )
