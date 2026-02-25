from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatEvent(BaseModel):
    kind: str
    agent: str
    text: str


class ChatResponse(BaseModel):
    conversation_id: str
    current_agent: str
    events: list[ChatEvent]
