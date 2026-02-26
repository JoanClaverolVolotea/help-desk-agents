from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

import backend.api.deps as deps
from backend.api.schemas.admin import (
    ApproveTicketRequest,
    RejectTicketRequest,
    TicketDetailResponse,
    TicketListResponse,
    TicketStatus,
)
from backend.storage import InvalidTicketStatusTransitionError, TicketNotFoundError

router = APIRouter()


@router.get("/api/admin/tickets", response_model=TicketListResponse)
async def admin_list_tickets(
    status: Annotated[TicketStatus | None, Query()] = None,
    conversation_id: Annotated[str | None, Query()] = None,
    external_ticket_id: Annotated[str | None, Query()] = None,
    use_case_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketListResponse:
    items = deps.TICKET_REPOSITORY.list_tickets(
        status=status,
        conversation_id=conversation_id,
        external_ticket_id=external_ticket_id,
        use_case_id=use_case_id,
        limit=limit,
        offset=offset,
    )
    return TicketListResponse(items=items)


@router.get("/api/admin/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def admin_get_ticket(ticket_id: str) -> TicketDetailResponse:
    try:
        ticket = deps.TICKET_REPOSITORY.get_ticket_detail(ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TicketDetailResponse(ticket=ticket)


@router.post("/api/admin/tickets/{ticket_id}/approve", response_model=TicketDetailResponse)
async def admin_approve_ticket(
    ticket_id: str,
    request: ApproveTicketRequest,
) -> TicketDetailResponse:
    try:
        ticket = deps.TICKET_REPOSITORY.approve_ticket(
            ticket_id=ticket_id,
            reviewed_by=request.reviewed_by,
            note=request.note,
        )
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTicketStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TicketDetailResponse(ticket=ticket)


@router.post("/api/admin/tickets/{ticket_id}/reject", response_model=TicketDetailResponse)
async def admin_reject_ticket(
    ticket_id: str,
    request: RejectTicketRequest,
) -> TicketDetailResponse:
    try:
        ticket = deps.TICKET_REPOSITORY.reject_ticket(
            ticket_id=ticket_id,
            reviewed_by=request.reviewed_by,
            reason=request.reason,
        )
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTicketStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TicketDetailResponse(ticket=ticket)
