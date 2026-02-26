from __future__ import annotations

from fastapi import APIRouter

from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.api.schemas.common import ResetRequest, ResetResponse
from backend.chats.admin_assistant import service

router = APIRouter()


@router.post("/api/admin/assistant/chat", response_model=ChatResponse)
async def admin_assistant_chat(request: ChatRequest) -> ChatResponse:
    return await service.chat(request)


@router.post("/api/admin/assistant/reset", response_model=ResetResponse)
async def admin_assistant_reset(request: ResetRequest) -> ResetResponse:
    return await service.reset(request)
