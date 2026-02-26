from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.api.schemas.common import ResetRequest, ResetResponse
from backend.chats.user_assistant import service

router = APIRouter()


@router.post("/api/user/assistant/chat", response_model=ChatResponse)
@router.post("/api/chat", response_model=ChatResponse, deprecated=True)
async def user_assistant_chat(request: ChatRequest) -> ChatResponse:
    return await service.chat(request)


@router.post("/api/user/assistant/chat/stream")
@router.post("/api/chat/stream", deprecated=True)
async def user_assistant_chat_stream(request: ChatRequest) -> StreamingResponse:
    return await service.chat_stream(request)


@router.post("/api/user/assistant/reset", response_model=ResetResponse)
@router.post("/api/reset", response_model=ResetResponse, deprecated=True)
async def user_assistant_reset(request: ResetRequest) -> ResetResponse:
    return await service.reset(request)
