from __future__ import annotations

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from agents import Agent, TResponseInputItem
from backend.domain.language_policy import normalize_language


@dataclass
class ConversationState:
    snapshot_id: str
    current_agent: Agent[Any]
    response_language: str = "en"
    input_items: list[TResponseInputItem] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


RESPONSE_LANGUAGE_CONTEXT: ContextVar[str] = ContextVar(
    "help_desk_response_language",
    default="en",
)


def current_response_language() -> str:
    return normalize_language(RESPONSE_LANGUAGE_CONTEXT.get())
