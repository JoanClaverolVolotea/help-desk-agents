from __future__ import annotations

import pathlib
import sqlite3
import uuid
from dataclasses import dataclass
from typing import cast

from backend.domain.models import (
    TicketDetail,
    TicketEventItem,
    TicketFieldItem,
    TicketFieldSource,
    TicketListItem,
    TicketStatus,
    TicketStatusHistoryItem,
    TicketStepItem,
)

from .db import connect, init_schema, resolve_db_path
from .errors import TicketNotFoundError
from .sql_helpers import _utc_now


@dataclass(frozen=True)
class TicketFieldWrite:
    field_name: str
    field_value: str
    is_required: bool
    source: TicketFieldSource


@dataclass(frozen=True)
class TicketStepWrite:
    step_order: int
    step_id: str
    output_text: str


@dataclass(frozen=True)
class TicketEventWrite:
    event_type: str
    payload_json: str
    agent_name: str | None = None


class TicketRepository:
    def __init__(self, db_path: str | pathlib.Path | None = None) -> None:
        if isinstance(db_path, pathlib.Path):
            self.db_path = db_path
        else:
            self.db_path = resolve_db_path(db_path)

    def initialize(self) -> None:
        with connect(self.db_path) as conn:
            init_schema(conn)

    def start_workflow_execution(
        self,
        *,
        conversation_id: str | None,
        use_case_id: str,
        language: str,
        ticket_context: str,
        external_ticket_id: str | None,
        agent_name: str | None = None,
    ) -> str:
        now = _utc_now()
        ticket_id = uuid.uuid4().hex

        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tickets(
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
                VALUES(?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL)
                """,
                (
                    ticket_id,
                    conversation_id,
                    external_ticket_id,
                    use_case_id,
                    TicketStatus.OPEN.value,
                    language,
                    ticket_context,
                    now,
                    now,
                ),
            )
            self._append_status_history(
                conn,
                ticket_id=ticket_id,
                status=TicketStatus.OPEN,
                changed_at=now,
                reason="Workflow execution created.",
            )
            self._update_ticket_status(
                conn,
                ticket_id=ticket_id,
                status=TicketStatus.IN_PROGRESS,
                changed_at=now,
                reason="Workflow execution started.",
            )
            if agent_name:
                self._insert_events(
                    conn,
                    ticket_id=ticket_id,
                    events=[
                        TicketEventWrite(
                            event_type="workflow_started",
                            agent_name=agent_name,
                            payload_json=('{"note":"Workflow execution started for this ticket."}'),
                        )
                    ],
                    created_at=now,
                )
            conn.commit()

        return ticket_id

    def complete_workflow_execution_success(
        self,
        *,
        ticket_id: str,
        fields: list[TicketFieldWrite],
        steps: list[TicketStepWrite],
        events: list[TicketEventWrite],
    ) -> None:
        now = _utc_now()
        with connect(self.db_path) as conn:
            self._assert_ticket_exists(conn, ticket_id)
            self._insert_fields(conn, ticket_id=ticket_id, fields=fields, created_at=now)
            self._insert_steps(conn, ticket_id=ticket_id, steps=steps, created_at=now)
            self._insert_events(conn, ticket_id=ticket_id, events=events, created_at=now)
            self._update_ticket_status(
                conn,
                ticket_id=ticket_id,
                status=TicketStatus.RESOLVED,
                changed_at=now,
                reason="Workflow execution completed successfully.",
                resolved_at=now,
                clear_error_message=True,
            )
            conn.commit()

    def complete_workflow_execution_failure(
        self,
        *,
        ticket_id: str,
        error_message: str,
        events: list[TicketEventWrite] | None = None,
    ) -> None:
        now = _utc_now()
        with connect(self.db_path) as conn:
            self._assert_ticket_exists(conn, ticket_id)
            if events:
                self._insert_events(conn, ticket_id=ticket_id, events=events, created_at=now)
            self._update_ticket_status(
                conn,
                ticket_id=ticket_id,
                status=TicketStatus.IN_PROGRESS,
                changed_at=now,
                reason="Workflow execution failed and requires follow-up.",
                error_message=error_message,
            )
            conn.commit()

    def list_tickets(
        self,
        *,
        status: TicketStatus | None = None,
        conversation_id: str | None = None,
        external_ticket_id: str | None = None,
        use_case_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TicketListItem]:
        where_clauses: list[str] = []
        params: list[object] = []
        if status is not None:
            where_clauses.append("t.status = ?")
            params.append(status.value)
        if conversation_id:
            where_clauses.append("t.conversation_id = ?")
            params.append(conversation_id)
        if external_ticket_id:
            where_clauses.append("t.external_ticket_id = ?")
            params.append(external_ticket_id)
        if use_case_id:
            where_clauses.append("t.use_case_id = ?")
            params.append(use_case_id)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        params.extend([max(limit, 1), max(offset, 0)])

        with connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT
                    t.id,
                    t.conversation_id,
                    t.external_ticket_id,
                    t.use_case_id,
                    uc.display_name AS use_case_display_name,
                    t.status,
                    t.language,
                    t.created_at,
                    t.updated_at,
                    t.resolved_at
                FROM tickets AS t
                LEFT JOIN use_cases AS uc
                    ON uc.id = t.use_case_id
                {where_sql}
                ORDER BY t.created_at DESC, t.id DESC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()

        return [self._to_ticket_list_item(row) for row in rows]

    def get_ticket_detail(self, ticket_id: str) -> TicketDetail:
        with connect(self.db_path) as conn:
            ticket_row = conn.execute(
                """
                SELECT
                    t.id,
                    t.conversation_id,
                    t.external_ticket_id,
                    t.use_case_id,
                    uc.display_name AS use_case_display_name,
                    t.status,
                    t.language,
                    t.ticket_context,
                    t.error_message,
                    t.created_at,
                    t.updated_at,
                    t.resolved_at
                FROM tickets AS t
                LEFT JOIN use_cases AS uc
                    ON uc.id = t.use_case_id
                WHERE t.id = ?
                """,
                (ticket_id,),
            ).fetchone()
            if ticket_row is None:
                raise TicketNotFoundError(f"Unknown ticket_id={ticket_id}")

            status_history_rows = conn.execute(
                """
                SELECT status, changed_at, reason
                FROM ticket_status_history
                WHERE ticket_id = ?
                ORDER BY rowid ASC
                """,
                (ticket_id,),
            ).fetchall()
            field_rows = conn.execute(
                """
                SELECT field_name, field_value, is_required, source, created_at
                FROM ticket_fields
                WHERE ticket_id = ?
                ORDER BY created_at ASC, field_name ASC, id ASC
                """,
                (ticket_id,),
            ).fetchall()
            step_rows = conn.execute(
                """
                SELECT step_order, step_id, output_text, created_at
                FROM ticket_steps
                WHERE ticket_id = ?
                ORDER BY step_order ASC, id ASC
                """,
                (ticket_id,),
            ).fetchall()
            event_rows = conn.execute(
                """
                SELECT event_type, agent_name, payload_json, created_at
                FROM ticket_events
                WHERE ticket_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (ticket_id,),
            ).fetchall()

        return TicketDetail(
            ticket_id=ticket_row["id"],
            conversation_id=ticket_row["conversation_id"],
            external_ticket_id=ticket_row["external_ticket_id"],
            use_case_id=ticket_row["use_case_id"],
            use_case_display_name=ticket_row["use_case_display_name"],
            status=TicketStatus(ticket_row["status"]),
            language=ticket_row["language"],
            ticket_context=ticket_row["ticket_context"],
            error_message=ticket_row["error_message"],
            created_at=ticket_row["created_at"],
            updated_at=ticket_row["updated_at"],
            resolved_at=ticket_row["resolved_at"],
            status_history=[
                TicketStatusHistoryItem(
                    status=TicketStatus(row["status"]),
                    changed_at=row["changed_at"],
                    reason=row["reason"],
                )
                for row in status_history_rows
            ],
            fields=[
                TicketFieldItem(
                    field_name=row["field_name"],
                    field_value=row["field_value"],
                    is_required=bool(row["is_required"]),
                    source=TicketFieldSource(row["source"]),
                    created_at=row["created_at"],
                )
                for row in field_rows
            ],
            steps=[
                TicketStepItem(
                    step_order=int(row["step_order"]),
                    step_id=row["step_id"],
                    output_text=row["output_text"],
                    created_at=row["created_at"],
                )
                for row in step_rows
            ],
            events=[
                TicketEventItem(
                    event_type=row["event_type"],
                    agent_name=row["agent_name"],
                    payload_json=row["payload_json"],
                    created_at=row["created_at"],
                )
                for row in event_rows
            ],
        )

    def _to_ticket_list_item(self, row: sqlite3.Row) -> TicketListItem:
        return TicketListItem(
            ticket_id=row["id"],
            conversation_id=row["conversation_id"],
            external_ticket_id=row["external_ticket_id"],
            use_case_id=row["use_case_id"],
            use_case_display_name=row["use_case_display_name"],
            status=TicketStatus(row["status"]),
            language=row["language"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            resolved_at=row["resolved_at"],
        )

    def _assert_ticket_exists(self, conn: sqlite3.Connection, ticket_id: str) -> sqlite3.Row:
        row = conn.execute(
            "SELECT id FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        if row is None:
            raise TicketNotFoundError(f"Unknown ticket_id={ticket_id}")
        return cast(sqlite3.Row, row)

    def _insert_fields(
        self,
        conn: sqlite3.Connection,
        *,
        ticket_id: str,
        fields: list[TicketFieldWrite],
        created_at: str,
    ) -> None:
        for field in fields:
            conn.execute(
                """
                INSERT INTO ticket_fields(
                    id, ticket_id, field_name, field_value, is_required, source, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    ticket_id,
                    field.field_name,
                    field.field_value,
                    int(field.is_required),
                    field.source.value,
                    created_at,
                ),
            )

    def _insert_steps(
        self,
        conn: sqlite3.Connection,
        *,
        ticket_id: str,
        steps: list[TicketStepWrite],
        created_at: str,
    ) -> None:
        for step in steps:
            conn.execute(
                """
                INSERT INTO ticket_steps(
                    id, ticket_id, step_order, step_id, output_text, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    ticket_id,
                    step.step_order,
                    step.step_id,
                    step.output_text,
                    created_at,
                ),
            )

    def _insert_events(
        self,
        conn: sqlite3.Connection,
        *,
        ticket_id: str,
        events: list[TicketEventWrite],
        created_at: str,
    ) -> None:
        for event in events:
            conn.execute(
                """
                INSERT INTO ticket_events(
                    id, ticket_id, event_type, agent_name, payload_json, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    ticket_id,
                    event.event_type,
                    event.agent_name,
                    event.payload_json,
                    created_at,
                ),
            )

    def _append_status_history(
        self,
        conn: sqlite3.Connection,
        *,
        ticket_id: str,
        status: TicketStatus,
        changed_at: str,
        reason: str | None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO ticket_status_history(id, ticket_id, status, changed_at, reason)
            VALUES(?, ?, ?, ?, ?)
            """,
            (uuid.uuid4().hex, ticket_id, status.value, changed_at, reason),
        )

    def _update_ticket_status(
        self,
        conn: sqlite3.Connection,
        *,
        ticket_id: str,
        status: TicketStatus,
        changed_at: str,
        reason: str | None,
        resolved_at: str | None = None,
        error_message: str | None = None,
        clear_error_message: bool = False,
    ) -> None:
        if clear_error_message:
            conn.execute(
                """
                UPDATE tickets
                SET status = ?,
                    updated_at = ?,
                    resolved_at = ?,
                    error_message = NULL
                WHERE id = ?
                """,
                (status.value, changed_at, resolved_at, ticket_id),
            )
        else:
            conn.execute(
                """
                UPDATE tickets
                SET status = ?,
                    updated_at = ?,
                    resolved_at = COALESCE(?, resolved_at),
                    error_message = COALESCE(?, error_message)
                WHERE id = ?
                """,
                (status.value, changed_at, resolved_at, error_message, ticket_id),
            )
        self._append_status_history(
            conn,
            ticket_id=ticket_id,
            status=status,
            changed_at=changed_at,
            reason=reason,
        )
