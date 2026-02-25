from __future__ import annotations

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from agents import Agent, TResponseInputItem
from backend.domain.language_policy import normalize_language
from backend.runtime.snapshot import RuntimeSnapshot


@dataclass
class ConversationState:
    snapshot_id: str
    current_agent: Agent[Any]
    response_language: str = "en"
    input_items: list[TResponseInputItem] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


CONVERSATIONS: dict[str, ConversationState] = {}
ADMIN_ASSISTANT_CONVERSATIONS: dict[str, ConversationState] = {}

RESPONSE_LANGUAGE_CONTEXT: ContextVar[str] = ContextVar(
    "help_desk_response_language",
    default="en",
)


def current_response_language() -> str:
    return normalize_language(RESPONSE_LANGUAGE_CONTEXT.get())


def ensure_chat_state(
    conversation_id: str,
    runtime_snapshot: RuntimeSnapshot,
) -> ConversationState:
    state = CONVERSATIONS.get(conversation_id)
    if state is None:
        state = ConversationState(
            snapshot_id=runtime_snapshot.snapshot_id,
            current_agent=runtime_snapshot.triage_agent,
        )
        CONVERSATIONS[conversation_id] = state
    return state


def ensure_admin_assistant_state(
    conversation_id: str,
    admin_triage_agent: Agent[Any],
) -> ConversationState:
    state = ADMIN_ASSISTANT_CONVERSATIONS.get(conversation_id)
    if state is None:
        state = ConversationState(
            snapshot_id="admin-assistant",
            current_agent=admin_triage_agent,
        )
        ADMIN_ASSISTANT_CONVERSATIONS[conversation_id] = state
    return state
