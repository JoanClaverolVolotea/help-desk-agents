from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

import backend.api.deps as deps
from agents import Runner, trace
from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.api.schemas.common import ResetRequest, ResetResponse
from backend.api_internal.conversation_state import (
    CONVERSATIONS,
    RESPONSE_LANGUAGE_CONTEXT,
    ensure_chat_state,
)
from backend.api_internal.event_serialization import event_from_item, ndjson_line
from backend.api_internal.runtime_sync import is_triage_agent
from backend.domain.language_policy import detect_user_language

router = APIRouter()


async def _chat_impl(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = ensure_chat_state(conversation_id, deps.RUNTIME_SNAPSHOT)

    async with state.lock:
        if state.snapshot_id != deps.RUNTIME_SNAPSHOT.snapshot_id and is_triage_agent(
            state.current_agent
        ):
            state.current_agent = deps.RUNTIME_SNAPSHOT.triage_agent
            state.snapshot_id = deps.RUNTIME_SNAPSHOT.snapshot_id

        state.response_language = detect_user_language(message, state.response_language)
        state.input_items.append({"content": message, "role": "user"})
        context_token = RESPONSE_LANGUAGE_CONTEXT.set(state.response_language)
        try:
            with trace("Help desk web chat", group_id=conversation_id):
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


async def _chat_stream_impl(request: ChatRequest) -> StreamingResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    conversation_id = request.conversation_id or uuid.uuid4().hex[:16]
    state = ensure_chat_state(conversation_id, deps.RUNTIME_SNAPSHOT)

    async def stream_events() -> AsyncIterator[str]:
        async with state.lock:
            if state.snapshot_id != deps.RUNTIME_SNAPSHOT.snapshot_id and is_triage_agent(
                state.current_agent
            ):
                state.current_agent = deps.RUNTIME_SNAPSHOT.triage_agent
                state.snapshot_id = deps.RUNTIME_SNAPSHOT.snapshot_id

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


async def _reset_impl(request: ResetRequest) -> ResetResponse:
    deleted = CONVERSATIONS.pop(request.conversation_id, None) is not None
    return ResetResponse(deleted=deleted)


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await _chat_impl(request)


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return await _chat_stream_impl(request)


@router.post("/api/reset", response_model=ResetResponse)
async def reset(request: ResetRequest) -> ResetResponse:
    return await _reset_impl(request)
