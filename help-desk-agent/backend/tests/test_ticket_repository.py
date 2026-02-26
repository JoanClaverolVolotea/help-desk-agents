from __future__ import annotations

import sqlite3

from backend.chats.user_assistant.bootstrap import initialize_repositories
from backend.domain.models import TicketFieldSource, TicketStatus
from backend.storage import (
    CategoryRepository,
    InvalidTicketStatusTransitionError,
    TicketRepository,
    UseCaseRepository,
)
from backend.storage.db import init_schema
from backend.storage.ticket_repository import TicketEventWrite, TicketFieldWrite, TicketStepWrite


def _build_repositories(tmp_path):
    db_path = tmp_path / "ticket-repository.db"
    category_repository = CategoryRepository(db_path=db_path)
    use_case_repository = UseCaseRepository(db_path=db_path)
    ticket_repository = TicketRepository(db_path=db_path)
    initialize_repositories(category_repository, use_case_repository, ticket_repository)
    return category_repository, use_case_repository, ticket_repository


def _seed_pending_review_ticket(
    use_case_repository: UseCaseRepository,
    ticket_repository: TicketRepository,
    *,
    external_ticket_id: str = "USDV-176285",
) -> str:
    use_case = use_case_repository.list_use_cases(include_archived=False)[0]
    ticket_id = ticket_repository.start_workflow_execution(
        conversation_id="conversation-success",
        use_case_id=use_case.use_case_id,
        language="en",
        ticket_context=f"Please help with {external_ticket_id}",
        external_ticket_id=external_ticket_id,
        agent_name="Reset de acceso eCrew Specialist",
    )
    ticket_repository.complete_workflow_execution_success(
        ticket_id=ticket_id,
        fields=[
            TicketFieldWrite(
                field_name="ticket_id",
                field_value=external_ticket_id,
                is_required=True,
                source=TicketFieldSource.PROVIDED,
            ),
            TicketFieldWrite(
                field_name="requester_name",
                field_value="Francois Emeriau",
                is_required=True,
                source=TicketFieldSource.PROVIDED,
            ),
        ],
        steps=[
            TicketStepWrite(
                step_order=1,
                step_id="verify_requester",
                output_text="Requester verified.",
            ),
            TicketStepWrite(
                step_order=2,
                step_id="reset_ecrew_access",
                output_text="Account reset complete.",
            ),
        ],
        events=[
            TicketEventWrite(
                event_type="workflow_completed",
                agent_name="Reset de acceso eCrew Specialist",
                payload_json='{"result":"ok"}',
            )
        ],
    )
    return ticket_id


def test_ticket_repository_records_successful_workflow_execution(tmp_path) -> None:
    _, use_case_repository, ticket_repository = _build_repositories(tmp_path)
    ticket_id = _seed_pending_review_ticket(use_case_repository, ticket_repository)

    detail = ticket_repository.get_ticket_detail(ticket_id)
    assert detail.status == TicketStatus.PENDING_REVIEW
    assert detail.external_ticket_id == "USDV-176285"
    assert [item.status for item in detail.status_history] == [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.PENDING_REVIEW,
    ]
    assert len(detail.fields) == 2
    assert len(detail.steps) == 2
    assert any(item.event_type == "workflow_completed" for item in detail.events)

    listed = ticket_repository.list_tickets(status=TicketStatus.PENDING_REVIEW)
    assert any(item.ticket_id == ticket_id for item in listed)


def test_ticket_repository_keeps_in_progress_after_failure(tmp_path) -> None:
    _, use_case_repository, ticket_repository = _build_repositories(tmp_path)
    use_case = use_case_repository.list_use_cases(include_archived=False)[0]

    ticket_id = ticket_repository.start_workflow_execution(
        conversation_id="conversation-failure",
        use_case_id=use_case.use_case_id,
        language="en",
        ticket_context="Please help with USDV-176893",
        external_ticket_id="USDV-176893",
    )
    ticket_repository.complete_workflow_execution_failure(
        ticket_id=ticket_id,
        error_message="Workflow failed on a deterministic step.",
        events=[
            TicketEventWrite(
                event_type="workflow_failed",
                payload_json='{"error":"step failure"}',
            )
        ],
    )

    detail = ticket_repository.get_ticket_detail(ticket_id)
    assert detail.status == TicketStatus.IN_PROGRESS
    assert detail.error_message == "Workflow failed on a deterministic step."
    assert detail.status_history[-1].status == TicketStatus.IN_PROGRESS
    assert any(item.event_type == "workflow_failed" for item in detail.events)


def test_ticket_repository_approve_ticket_marks_terminal_state(tmp_path) -> None:
    _, use_case_repository, ticket_repository = _build_repositories(tmp_path)
    ticket_id = _seed_pending_review_ticket(use_case_repository, ticket_repository)

    updated = ticket_repository.approve_ticket(
        ticket_id=ticket_id,
        reviewed_by="Jane Doe",
        note="Validation looks complete.",
    )

    assert updated.status == TicketStatus.APPROVED
    assert updated.resolved_at is not None
    assert updated.status_history[-1].status == TicketStatus.APPROVED
    assert "Jane Doe" in (updated.status_history[-1].reason or "")
    approved_events = [event for event in updated.events if event.event_type == "ticket_approved"]
    assert len(approved_events) == 1
    assert '"reviewed_by": "Jane Doe"' in approved_events[0].payload_json


def test_ticket_repository_reject_ticket_marks_terminal_state(tmp_path) -> None:
    _, use_case_repository, ticket_repository = _build_repositories(tmp_path)
    ticket_id = _seed_pending_review_ticket(use_case_repository, ticket_repository)

    updated = ticket_repository.reject_ticket(
        ticket_id=ticket_id,
        reviewed_by="Jane Doe",
        reason="Requester identity does not match records.",
    )

    assert updated.status == TicketStatus.REJECTED
    assert updated.resolved_at is not None
    assert updated.error_message == "Requester identity does not match records."
    assert updated.status_history[-1].status == TicketStatus.REJECTED
    rejected_events = [event for event in updated.events if event.event_type == "ticket_rejected"]
    assert len(rejected_events) == 1
    assert '"reviewed_by": "Jane Doe"' in rejected_events[0].payload_json


def test_ticket_repository_reject_requires_pending_review_status(tmp_path) -> None:
    _, use_case_repository, ticket_repository = _build_repositories(tmp_path)
    ticket_id = _seed_pending_review_ticket(use_case_repository, ticket_repository)
    ticket_repository.approve_ticket(ticket_id=ticket_id, reviewed_by="Jane Doe")

    try:
        ticket_repository.reject_ticket(
            ticket_id=ticket_id,
            reviewed_by="Jane Doe",
            reason="Cannot reject after approval.",
        )
    except InvalidTicketStatusTransitionError:
        pass
    else:
        raise AssertionError("Expected InvalidTicketStatusTransitionError")


def test_init_schema_migrates_legacy_resolved_status_to_approved(tmp_path) -> None:
    db_path = tmp_path / "legacy-ticket-status.db"
    use_case_id = "legacy-use-case-id"
    ticket_id = "legacy-ticket-id"

    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE use_cases (
                id TEXT PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                template_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE tickets (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                external_ticket_id TEXT,
                use_case_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'resolved')),
                language TEXT NOT NULL,
                ticket_context TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (use_case_id) REFERENCES use_cases(id)
            );

            CREATE TABLE ticket_status_history (
                id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'resolved')),
                changed_at TEXT NOT NULL,
                reason TEXT,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            INSERT INTO use_cases(
                id, slug, display_name, template_id, created_at, updated_at, archived
            )
            VALUES(?, ?, ?, ?, ?, ?, 0)
            """,
            (use_case_id, "legacy-use-case", "Legacy Use Case", "legacy-template", "now", "now"),
        )
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
            VALUES(?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                ticket_id,
                "legacy-conversation",
                "USDV-000001",
                use_case_id,
                "resolved",
                "en",
                "Legacy context",
                "now",
                "now",
                "now",
            ),
        )
        conn.execute(
            """
            INSERT INTO ticket_status_history(id, ticket_id, status, changed_at, reason)
            VALUES(?, ?, ?, ?, ?)
            """,
            ("status-history-id", ticket_id, "resolved", "now", "Legacy resolved status"),
        )
        conn.commit()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        init_schema(conn)
        ticket_row = conn.execute(
            "SELECT status FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        assert ticket_row is not None
        assert ticket_row["status"] == "approved"
        history_row = conn.execute(
            """
            SELECT status
            FROM ticket_status_history
            WHERE ticket_id = ?
            """,
            (ticket_id,),
        ).fetchone()
        assert history_row is not None
        assert history_row["status"] == "approved"
