from __future__ import annotations

from typing import Any

import backend.api.deps as deps
from agents import Agent
from backend.domain.models import CategoryDetail
from backend.runtime.bootstrap import build_snapshot_from_repository


def is_triage_agent(agent: Agent[Any]) -> bool:
    return agent.name == "Help Desk Triage Agent"


async def refresh_runtime_snapshot() -> None:
    async with deps.RUNTIME_LOCK:
        deps.RUNTIME_SNAPSHOT = build_snapshot_from_repository(
            deps.USE_CASE_REPOSITORY,
            deps.TICKET_REPOSITORY,
        )


async def publish_category_and_sync(category_id: str) -> CategoryDetail:
    detail = deps.CATEGORY_REPOSITORY.publish_draft(category_id)
    if detail.published_definition is not None:
        deps.USE_CASE_REPOSITORY.create_or_update_default_use_case_for_category(detail)
    await refresh_runtime_snapshot()
    return detail


async def archive_category_and_sync(category_id: str) -> None:
    deps.CATEGORY_REPOSITORY.archive_category(category_id)
    deps.USE_CASE_REPOSITORY.archive_default_use_case_for_category(category_id)
    await refresh_runtime_snapshot()


async def restore_category_and_sync(category_id: str) -> None:
    detail = deps.CATEGORY_REPOSITORY.restore_category(category_id)
    if detail.published_definition is not None:
        deps.USE_CASE_REPOSITORY.create_or_update_default_use_case_for_category(detail)
    await refresh_runtime_snapshot()
