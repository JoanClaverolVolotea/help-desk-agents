from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from backend.domain.models import VersionStatus


def _next_version_number(
    conn: sqlite3.Connection,
    table_name: str,
    foreign_key_name: str,
    foreign_key_value: str,
) -> int:
    row = conn.execute(
        (
            f"SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version "
            f"FROM {table_name} WHERE {foreign_key_name} = ?"
        ),
        (foreign_key_value,),
    ).fetchone()
    assert row is not None
    return int(row["next_version"])


def _active_published_row(rows: list[sqlite3.Row]) -> sqlite3.Row | None:
    published_rows = [row for row in rows if row["status"] == VersionStatus.PUBLISHED.value]
    if not published_rows:
        return None
    return max(published_rows, key=lambda row: int(row["version_number"]))


def _editable_draft_row(
    rows: list[sqlite3.Row],
    published_row: sqlite3.Row | None,
) -> sqlite3.Row | None:
    published_version = int(published_row["version_number"]) if published_row else 0
    candidate_drafts = [
        row
        for row in rows
        if row["status"] == VersionStatus.DRAFT.value
        and int(row["version_number"]) > published_version
    ]
    if not candidate_drafts:
        return None
    return max(candidate_drafts, key=lambda row: int(row["version_number"]))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
