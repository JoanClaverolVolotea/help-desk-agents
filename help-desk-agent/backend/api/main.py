from __future__ import annotations

import os
import pathlib
import sys
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _ensure_helpdesk_app_root_on_path() -> None:
    """Add the app root so `backend.*` imports work from nested execution directories."""
    app_root = pathlib.Path(__file__).resolve().parents[2]
    app_root_str = str(app_root)
    if app_root_str not in sys.path:
        sys.path.insert(0, app_root_str)


_ensure_helpdesk_app_root_on_path()

from agents import Runner
from backend.api.routes import (
    admin_bootstrap,
    admin_categories,
    admin_tickets,
    admin_use_cases,
    health,
)
from backend.chats.admin_assistant import routes as admin_assistant_routes
from backend.chats.admin_assistant.service import ADMIN_ASSISTANT_RUNTIME_SNAPSHOT
from backend.chats.admin_assistant.state import ADMIN_ASSISTANT_CONVERSATIONS
from backend.chats.shared.state import ConversationState
from backend.chats.user_assistant import routes as user_assistant_routes
from backend.chats.user_assistant.state import USER_ASSISTANT_CONVERSATIONS


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
    app.include_router(user_assistant_routes.router)
    app.include_router(admin_assistant_routes.router)
    app.include_router(admin_bootstrap.router)
    app.include_router(admin_categories.router)
    app.include_router(admin_use_cases.router)
    app.include_router(admin_tickets.router)
    return app


app = create_app()


def __getattr__(name: str) -> Any:
    if name in {
        "CATEGORY_REPOSITORY",
        "TICKET_REPOSITORY",
        "USE_CASE_REPOSITORY",
        "USER_ASSISTANT_RUNTIME_SNAPSHOT",
        "USER_ASSISTANT_RUNTIME_LOCK",
    }:
        from backend.api import deps

        return getattr(deps, name)
    if name == "ADMIN_ASSISTANT_RUNTIME_SNAPSHOT":
        return ADMIN_ASSISTANT_RUNTIME_SNAPSHOT
    raise AttributeError(name)


__all__ = [
    "app",
    "create_app",
    "Runner",
    "ConversationState",
    "USER_ASSISTANT_CONVERSATIONS",
    "ADMIN_ASSISTANT_CONVERSATIONS",
]


if __name__ == "__main__":
    host = os.getenv("HELP_DESK_API_HOST", "127.0.0.1")
    port = int(os.getenv("HELP_DESK_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
