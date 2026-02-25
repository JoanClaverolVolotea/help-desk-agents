from __future__ import annotations

from pydantic import BaseModel


class ResetRequest(BaseModel):
    conversation_id: str


class ResetResponse(BaseModel):
    deleted: bool
