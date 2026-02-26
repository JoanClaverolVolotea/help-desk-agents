from __future__ import annotations

from contextvars import ContextVar

CHANNEL_ADMIN_ASSISTANT = "admin_assistant"
CHANNEL_UNKNOWN = "unknown"
CHANNEL_USER_ASSISTANT = "user_assistant"

CONVERSATION_ID_CONTEXT: ContextVar[str | None] = ContextVar(
    "help_desk_conversation_id",
    default=None,
)
REQUEST_CHANNEL_CONTEXT: ContextVar[str] = ContextVar(
    "help_desk_request_channel",
    default=CHANNEL_UNKNOWN,
)


def current_conversation_id() -> str | None:
    return CONVERSATION_ID_CONTEXT.get()


def current_request_channel() -> str:
    return REQUEST_CHANNEL_CONTEXT.get()
