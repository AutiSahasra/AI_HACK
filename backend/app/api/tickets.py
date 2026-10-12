from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel

from app.models.ticket import Ticket, TicketStatus, TicketComment
from app.services.tickets import ticket_service
from app.api.deps import get_current_user

router = APIRouter(prefix="/tickets", tags=["tickets"])

class StatusUpdateRequest(BaseModel):
    status: TicketStatus

class AssignRequest(BaseModel):
    assignee: str

class CommentRequest(BaseModel):
    text: str

@router.get("", response_model=List[Ticket])
async def list_tickets(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    items = await ticket_service.list_tickets(status=status)
    return [Ticket(**i) for i in items]

@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    doc = await ticket_service.get_ticket(ticket_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return Ticket(**doc)

@router.patch("/{ticket_id}/status", response_model=Ticket)
async def update_status(
    ticket_id: str,
    body: StatusUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        updated = await ticket_service.update_status(
            ticket_id=ticket_id,
            new_status=body.status,
            actor=current_user.get("username", "anonymous"),
            role=current_user.get("role", "support_engineer")
        )
        return Ticket(**updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/{ticket_id}/assign", response_model=Ticket)
async def assign_ticket(
    ticket_id: str,
    body: AssignRequest,
    current_user: dict = Depends(get_current_user)
):
    updated = await ticket_service.assign_ticket(
        ticket_id=ticket_id,
        assignee=body.assignee,
        actor=current_user.get("username", "anonymous"),
        role=current_user.get("role", "support_engineer")
    )
    return Ticket(**updated)

@router.post("/{ticket_id}/comments", response_model=Ticket)
async def add_comment(
    ticket_id: str,
    body: CommentRequest,
    current_user: dict = Depends(get_current_user)
):
    updated = await ticket_service.add_comment(
        ticket_id=ticket_id,
        author=current_user.get("username", "anonymous"),
        role=current_user.get("role", "support_engineer"),
        text=body.text
    )
    return Ticket(**updated)
