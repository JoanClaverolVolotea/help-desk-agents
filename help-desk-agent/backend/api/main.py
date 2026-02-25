from __future__ import annotations

import os
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents import Runner
from backend.api.routes import (
    admin_assistant,
    admin_categories,
    admin_use_cases,
    chat,
    health,
)
from backend.api_internal.conversation_state import (
    ADMIN_ASSISTANT_CONVERSATIONS,
    CONVERSATIONS,
    ConversationState,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Help Desk Agent API", version="0.4.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(admin_assistant.router)
    app.include_router(admin_categories.router)
    app.include_router(admin_use_cases.router)
    return app


app = create_app()


def __getattr__(name: str) -> Any:
    if name in {
        "CATEGORY_REPOSITORY",
        "USE_CASE_REPOSITORY",
        "RUNTIME_SNAPSHOT",
        "RUNTIME_LOCK",
    }:
        from backend.api import deps

        return getattr(deps, name)
    if name == "ADMIN_ASSISTANT_TRIAGE_AGENT":
        return admin_assistant.ADMIN_ASSISTANT_TRIAGE_AGENT
    raise AttributeError(name)


__all__ = [
    "app",
    "create_app",
    "Runner",
    "ConversationState",
    "CONVERSATIONS",
    "ADMIN_ASSISTANT_CONVERSATIONS",
]


if __name__ == "__main__":
    host = os.getenv("HELP_DESK_API_HOST", "127.0.0.1")
    port = int(os.getenv("HELP_DESK_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
