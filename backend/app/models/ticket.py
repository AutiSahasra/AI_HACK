from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from app.models.user import UserRole

class TicketPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_APPROVAL = "pending_approval"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    ESCALATED = "escalated"

class TicketComment(BaseModel):
    id: str
    author: str
    authorRole: UserRole
    text: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Ticket(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=False)
    id: str = Field(default="", alias="_id")
    incidentId: str
    title: str
    priority: TicketPriority = TicketPriority.P2
    status: TicketStatus = TicketStatus.OPEN
    assignee: Optional[str] = None
    comments: List[TicketComment] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolvedAt: Optional[datetime] = None

class TicketCreate(BaseModel):
    incidentId: str
    title: str
    priority: TicketPriority = TicketPriority.P2
    assignee: Optional[str] = None

class TicketUpdate(BaseModel):
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    assignee: Optional[str] = None
