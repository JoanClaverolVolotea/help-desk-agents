from __future__ import annotations

import sqlite3

from backend.chats.user_assistant.graph.snapshot import (
    RuntimeSnapshot,
    build_runtime_snapshot,
)
from backend.domain.templates import seed_category_definitions, seed_use_case_definitions
from backend.storage import CategoryRepository, TicketRepository, UseCaseRepository
from backend.storage.db import connect


def initialize_repositories(
    category_repository: CategoryRepository,
    use_case_repository: UseCaseRepository,
    ticket_repository: TicketRepository | None = None,
) -> None:
    category_repository.initialize()
    use_case_repository.initialize()
    if ticket_repository is not None:
        ticket_repository.initialize()

    categories_by_slug = category_repository.seed_if_empty(seed_category_definitions())
    use_case_repository.seed_if_empty(seed_use_case_definitions(), categories_by_slug)
    use_case_repository.sync_default_use_cases_for_published_categories(category_repository)


def reseed_defaults(
    category_repository: CategoryRepository,
    use_case_repository: UseCaseRepository,
    ticket_repository: TicketRepository,
) -> tuple[dict[str, int], dict[str, int]]:
    _assert_shared_db_path(category_repository, use_case_repository, ticket_repository)
    db_path = category_repository.db_path

    with connect(db_path) as conn:
        deleted_counts = {
            "tickets": _count_rows(conn, "tickets"),
            "use_cases": _count_rows(conn, "use_cases"),
            "categories": _count_rows(conn, "categories"),
        }

        conn.executescript(
            """
            DELETE FROM ticket_events;
            DELETE FROM ticket_steps;
            DELETE FROM ticket_fields;
            DELETE FROM ticket_status_history;
            DELETE FROM tickets;
            DELETE FROM use_case_versions;
            DELETE FROM use_cases;
            DELETE FROM category_versions;
            DELETE FROM categories;
            """
        )
        conn.commit()

    initialize_repositories(category_repository, use_case_repository, ticket_repository)

    with connect(db_path) as conn:
        seeded_counts = {
            "categories": _count_rows(conn, "categories"),
            "use_cases": _count_rows(conn, "use_cases"),
        }

    return deleted_counts, seeded_counts


def build_snapshot_from_repository(
    use_case_repository: UseCaseRepository,
    ticket_repository: TicketRepository | None = None,
) -> RuntimeSnapshot:
    published_use_cases = use_case_repository.list_published_use_cases()
    return build_runtime_snapshot(published_use_cases, ticket_repository=ticket_repository)


def _count_rows(conn: sqlite3.Connection, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(1) AS count FROM {table_name}").fetchone()
    assert row is not None
    return int(row["count"])


def _assert_shared_db_path(
    category_repository: CategoryRepository,
    use_case_repository: UseCaseRepository,
    ticket_repository: TicketRepository,
) -> None:
    if category_repository.db_path != use_case_repository.db_path:
        raise ValueError("Category and use-case repositories must use the same DB path.")
    if category_repository.db_path != ticket_repository.db_path:
        raise ValueError("Category and ticket repositories must use the same DB path.")
