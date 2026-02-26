from __future__ import annotations

import os
import pathlib
import sqlite3

DEFAULT_DB_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "helpdesk.db"
TICKET_STATUS_VALUES = ("open", "in_progress", "pending_review", "approved", "rejected")


def resolve_db_path(path_override: str | None = None) -> pathlib.Path:
    if path_override:
        return pathlib.Path(path_override)
    env_value = os.getenv("HELP_DESK_DB_PATH")
    if env_value:
        return pathlib.Path(env_value)
    return DEFAULT_DB_PATH


def connect(db_path: pathlib.Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS category_versions (
            id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('draft', 'published')),
            definition_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_category_versions_unique_version
            ON category_versions(category_id, version_number);

        CREATE INDEX IF NOT EXISTS idx_category_versions_status
            ON category_versions(category_id, status);

        CREATE TABLE IF NOT EXISTS use_cases (
            id TEXT PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            template_id TEXT NOT NULL,
            category_id TEXT,
            category_version_number INTEGER,
            is_system_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS use_case_versions (
            id TEXT PRIMARY KEY,
            use_case_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('draft', 'published')),
            definition_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (use_case_id) REFERENCES use_cases(id) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_use_case_versions_unique_version
            ON use_case_versions(use_case_id, version_number);

        CREATE INDEX IF NOT EXISTS idx_use_case_versions_status
            ON use_case_versions(use_case_id, status);

        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            external_ticket_id TEXT,
            use_case_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('open', 'in_progress', 'pending_review', 'approved', 'rejected')
            ),
            language TEXT NOT NULL,
            ticket_context TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (use_case_id) REFERENCES use_cases(id)
        );

        CREATE INDEX IF NOT EXISTS idx_tickets_created_at
            ON tickets(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_tickets_status
            ON tickets(status);

        CREATE INDEX IF NOT EXISTS idx_tickets_external_ticket_id
            ON tickets(external_ticket_id);

        CREATE INDEX IF NOT EXISTS idx_tickets_conversation_id
            ON tickets(conversation_id);

        CREATE INDEX IF NOT EXISTS idx_tickets_use_case_id
            ON tickets(use_case_id);

        CREATE TABLE IF NOT EXISTS ticket_status_history (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('open', 'in_progress', 'pending_review', 'approved', 'rejected')
            ),
            changed_at TEXT NOT NULL,
            reason TEXT,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ticket_status_history_ticket_id
            ON ticket_status_history(ticket_id, changed_at ASC);

        CREATE TABLE IF NOT EXISTS ticket_fields (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT NOT NULL,
            is_required INTEGER NOT NULL CHECK (is_required IN (0, 1)),
            source TEXT NOT NULL CHECK (source IN ('provided', 'derived', 'missing')),
            created_at TEXT NOT NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ticket_fields_ticket_id
            ON ticket_fields(ticket_id, field_name ASC);

        CREATE TABLE IF NOT EXISTS ticket_steps (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            step_order INTEGER NOT NULL,
            step_id TEXT NOT NULL,
            output_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ticket_steps_ticket_id
            ON ticket_steps(ticket_id, step_order ASC);

        CREATE TABLE IF NOT EXISTS ticket_events (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            agent_name TEXT,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket_id
            ON ticket_events(ticket_id, created_at ASC);

        """
    )

    _migrate_ticket_status_tables(conn)
    _ensure_ticket_indexes(conn)

    _ensure_use_cases_column(conn, "category_id", "TEXT")
    _ensure_use_cases_column(conn, "category_version_number", "INTEGER")
    _ensure_use_cases_column(conn, "is_system_default", "INTEGER NOT NULL DEFAULT 0")
    _dedupe_active_default_use_cases(conn)
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_use_cases_default_per_category
            ON use_cases(category_id)
            WHERE is_system_default = 1 AND archived = 0
        """
    )

    conn.commit()


def _ensure_use_cases_column(
    conn: sqlite3.Connection, column_name: str, column_sql_type: str
) -> None:
    if _table_has_column(conn, "use_cases", column_name):
        return
    conn.execute(f"ALTER TABLE use_cases ADD COLUMN {column_name} {column_sql_type}")


def _table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def _migrate_ticket_status_tables(conn: sqlite3.Connection) -> None:
    tickets_needs_migration = _ticket_status_table_needs_migration(conn, "tickets")
    history_needs_migration = _ticket_status_table_needs_migration(conn, "ticket_status_history")
    if not tickets_needs_migration and not history_needs_migration:
        return

    conn.commit()
    foreign_keys_row = conn.execute("PRAGMA foreign_keys").fetchone()
    foreign_keys_enabled = bool(foreign_keys_row[0]) if foreign_keys_row is not None else True
    if foreign_keys_enabled:
        conn.execute("PRAGMA foreign_keys = OFF;")
    try:
        conn.execute("BEGIN")
        if tickets_needs_migration:
            _rebuild_tickets_table(conn)
        if history_needs_migration:
            _rebuild_ticket_status_history_table(conn)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        if foreign_keys_enabled:
            conn.execute("PRAGMA foreign_keys = ON;")


def _ticket_status_table_needs_migration(conn: sqlite3.Connection, table_name: str) -> bool:
    sql_row = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    table_sql = (str(sql_row["sql"]) if sql_row and sql_row["sql"] else "").lower()
    has_current_statuses = all(f"'{status}'" in table_sql for status in TICKET_STATUS_VALUES)
    if not has_current_statuses:
        return True

    resolved_count_row = conn.execute(
        f"""
        SELECT COUNT(1) AS count
        FROM {table_name}
        WHERE status = 'resolved'
        """
    ).fetchone()
    if resolved_count_row is None:
        return False
    return int(resolved_count_row["count"]) > 0


def _rebuild_tickets_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE tickets_migrated (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            external_ticket_id TEXT,
            use_case_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('open', 'in_progress', 'pending_review', 'approved', 'rejected')
            ),
            language TEXT NOT NULL,
            ticket_context TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (use_case_id) REFERENCES use_cases(id)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO tickets_migrated(
            id,
            conversation_id,
            external_ticket_id,
            use_case_id,
            status,
            language,
            ticket_context,
            error_message,
            created_at,
            updated_at,
            resolved_at
        )
        SELECT
            id,
            conversation_id,
            external_ticket_id,
            use_case_id,
            CASE status
                WHEN 'resolved' THEN 'approved'
                ELSE status
            END,
            language,
            ticket_context,
            error_message,
            created_at,
            updated_at,
            resolved_at
        FROM tickets
        """
    )
    conn.execute("DROP TABLE tickets")
    conn.execute("ALTER TABLE tickets_migrated RENAME TO tickets")


def _rebuild_ticket_status_history_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE ticket_status_history_migrated (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('open', 'in_progress', 'pending_review', 'approved', 'rejected')
            ),
            changed_at TEXT NOT NULL,
            reason TEXT,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO ticket_status_history_migrated(id, ticket_id, status, changed_at, reason)
        SELECT
            id,
            ticket_id,
            CASE status
                WHEN 'resolved' THEN 'approved'
                ELSE status
            END,
            changed_at,
            reason
        FROM ticket_status_history
        """
    )
    conn.execute("DROP TABLE ticket_status_history")
    conn.execute("ALTER TABLE ticket_status_history_migrated RENAME TO ticket_status_history")


def _ensure_ticket_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_tickets_created_at
            ON tickets(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_tickets_status
            ON tickets(status);

        CREATE INDEX IF NOT EXISTS idx_tickets_external_ticket_id
            ON tickets(external_ticket_id);

        CREATE INDEX IF NOT EXISTS idx_tickets_conversation_id
            ON tickets(conversation_id);

        CREATE INDEX IF NOT EXISTS idx_tickets_use_case_id
            ON tickets(use_case_id);

        CREATE INDEX IF NOT EXISTS idx_ticket_status_history_ticket_id
            ON ticket_status_history(ticket_id, changed_at ASC);

        CREATE INDEX IF NOT EXISTS idx_ticket_fields_ticket_id
            ON ticket_fields(ticket_id, field_name ASC);

        CREATE INDEX IF NOT EXISTS idx_ticket_steps_ticket_id
            ON ticket_steps(ticket_id, step_order ASC);

        CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket_id
            ON ticket_events(ticket_id, created_at ASC);
        """
    )


def _dedupe_active_default_use_cases(conn: sqlite3.Connection) -> None:
    duplicate_categories = conn.execute(
        """
        SELECT category_id
        FROM use_cases
        WHERE is_system_default = 1
          AND archived = 0
          AND category_id IS NOT NULL
        GROUP BY category_id
        HAVING COUNT(1) > 1
        """
    ).fetchall()
    for duplicate in duplicate_categories:
        category_id = duplicate["category_id"]
        rows = conn.execute(
            """
            SELECT id
            FROM use_cases
            WHERE category_id = ?
              AND is_system_default = 1
              AND archived = 0
            ORDER BY updated_at DESC, created_at DESC, id DESC
            """,
            (category_id,),
        ).fetchall()
        for stale_row in rows[1:]:
            conn.execute(
                """
                UPDATE use_cases
                SET archived = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (stale_row["id"],),
            )
