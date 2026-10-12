import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.models.ticket import Ticket, TicketPriority, TicketStatus, TicketComment
from app.core.database import DatabaseManager
from app.services.audit import audit_service
from app.repositories.incident_repo import incident_repo

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED, TicketStatus.CLOSED],
    TicketStatus.IN_PROGRESS: [TicketStatus.PENDING_APPROVAL, TicketStatus.VERIFYING, TicketStatus.RESOLVED, TicketStatus.ESCALATED],
    TicketStatus.PENDING_APPROVAL: [TicketStatus.IN_PROGRESS, TicketStatus.VERIFYING, TicketStatus.ESCALATED],
    TicketStatus.VERIFYING: [TicketStatus.RESOLVED, TicketStatus.ESCALATED, TicketStatus.IN_PROGRESS],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.REOPENED],
    TicketStatus.CLOSED: [TicketStatus.REOPENED],
    TicketStatus.ESCALATED: [TicketStatus.IN_PROGRESS, TicketStatus.CLOSED],
    TicketStatus.REOPENED: [TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED],
}

class TicketService:
    @property
    def col(self):
        return DatabaseManager.get_collection("tickets")

    async def create_ticket_for_incident(
        self,
        incident_id: str,
        title: str,
        severity: str
    ) -> str:
        ticket_id = f"TCK-{str(uuid.uuid4())[:8].upper()}"
        
        # Priority mapping
        if severity == "CRITICAL":
            priority = TicketPriority.P1
        elif severity == "ERROR":
            priority = TicketPriority.P2
        elif severity == "WARN":
            priority = TicketPriority.P3
        else:
            priority = TicketPriority.P4

        now = datetime.now(timezone.utc)
        doc = {
            "_id": ticket_id,
            "incidentId": incident_id,
            "title": f"[{priority.value}] {title}",
            "priority": priority.value,
            "status": TicketStatus.OPEN.value,
            "assignee": None,
            "comments": [],
            "createdAt": now,
            "updatedAt": now
        }
        await self.col.insert_one(doc)

        # Link ticket to incident
        await incident_repo.update(incident_id, {"ticketId": ticket_id})

        await audit_service.log_event(
            action="TICKET_CREATED",
            actor="system",
            role="system",
            entity_type="ticket",
            entity_id=ticket_id,
            details={"incidentId": incident_id, "priority": priority.value}
        )
        return ticket_id

    async def list_tickets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        fltr = {"status": status} if status else {}
        cursor = self.col.find(fltr).sort("createdAt", -1)
        items = await cursor.to_list(100)
        for i in items:
            if "_id" in i:
                i["id"] = str(i["_id"])
        return items

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        doc = await self.col.find_one({"_id": ticket_id})
        if doc and "_id" in doc:
            doc["id"] = str(doc["_id"])
        return doc

    async def update_status(
        self,
        ticket_id: str,
        new_status: TicketStatus,
        actor: str,
        role: str
    ) -> Dict[str, Any]:
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        curr_status = TicketStatus(ticket.get("status", "open"))
        allowed = VALID_TRANSITIONS.get(curr_status, [])
        if new_status not in allowed and new_status != curr_status:
            # Allow transitions if user is admin
            if role != "admin":
                raise ValueError(f"Invalid ticket state transition from '{curr_status.value}' to '{new_status.value}'")

        now = datetime.now(timezone.utc)
        updates: Dict[str, Any] = {"status": new_status.value, "updatedAt": now}
        if new_status == TicketStatus.RESOLVED:
            updates["resolvedAt"] = now

        await self.col.update_one({"_id": ticket_id}, {"$set": updates})

        await audit_service.log_event(
            action="TICKET_STATUS_CHANGED",
            actor=actor,
            role=role,
            entity_type="ticket",
            entity_id=ticket_id,
            details={"from": curr_status.value, "to": new_status.value}
        )
        ticket.update(updates)
        return ticket

    async def assign_ticket(
        self,
        ticket_id: str,
        assignee: str,
        actor: str,
        role: str
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        await self.col.update_one(
            {"_id": ticket_id},
            {"$set": {"assignee": assignee, "updatedAt": now}}
        )
        await audit_service.log_event(
            action="TICKET_ASSIGNED",
            actor=actor,
            role=role,
            entity_type="ticket",
            entity_id=ticket_id,
            details={"assignee": assignee}
        )
        return await self.get_ticket(ticket_id)

    async def add_comment(
        self,
        ticket_id: str,
        author: str,
        role: str,
        text: str
    ) -> Dict[str, Any]:
        comment = {
            "id": str(uuid.uuid4())[:8],
            "author": author,
            "authorRole": role,
            "text": text,
            "createdAt": datetime.now(timezone.utc)
        }
        await self.col.update_one(
            {"_id": ticket_id},
            {
                "$push": {"comments": comment},
                "$set": {"updatedAt": datetime.now(timezone.utc)}
            }
        )
        return await self.get_ticket(ticket_id)

ticket_service = TicketService()
