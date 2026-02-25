from __future__ import annotations

import asyncio

from backend.runtime.bootstrap import (
    build_snapshot_from_repository,
    initialize_repositories,
)
from backend.runtime.snapshot import RuntimeSnapshot
from backend.storage import CategoryRepository, TicketRepository, UseCaseRepository

CATEGORY_REPOSITORY = CategoryRepository()
USE_CASE_REPOSITORY = UseCaseRepository()
TICKET_REPOSITORY = TicketRepository()
initialize_repositories(CATEGORY_REPOSITORY, USE_CASE_REPOSITORY, TICKET_REPOSITORY)

RUNTIME_SNAPSHOT: RuntimeSnapshot = build_snapshot_from_repository(
    USE_CASE_REPOSITORY,
    TICKET_REPOSITORY,
)
RUNTIME_LOCK = asyncio.Lock()
