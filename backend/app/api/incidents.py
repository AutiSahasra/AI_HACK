from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel

from app.models.incident import Incident, IncidentStatus, IncidentFilterParams
from app.models.log_event import LogSeverity
from app.api.deps import get_current_user
from app.repositories.incident_repo import incident_repo
from app.repositories.log_event_repo import log_event_repo

router = APIRouter(prefix="/incidents", tags=["incidents"])

class FeedbackRequest(BaseModel):
    useful: bool
    notes: Optional[str] = None

@router.get("", response_model=List[Incident])
async def list_incidents(
    status: Optional[IncidentStatus] = None,
    severity: Optional[LogSeverity] = None,
    service: Optional[str] = None,
    source: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    params = IncidentFilterParams(
        status=status,
        severity=severity,
        service=service,
        source=source,
        page=page,
        page_size=page_size
    )
    items, total = await incident_repo.list_incidents(params)
    res = []
    for item in items:
        if "_id" in item and "id" not in item:
            item["id"] = str(item["_id"])
        res.append(Incident(**item))
    return res

@router.get("/{incident_id}", response_model=Incident)
async def get_incident(
    incident_id: str,
    current_user: dict = Depends(get_current_user)
):
    doc = await incident_repo.get_by_id(incident_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if "_id" in doc and "id" not in doc:
        doc["id"] = str(doc["_id"])
    return Incident(**doc)

@router.get("/{incident_id}/events")
async def get_incident_events(
    incident_id: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    doc = await incident_repo.get_by_id(incident_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    event_ids = doc.get("eventRefs", [])[:limit]
    events = await log_event_repo.get_by_ids(event_ids)
    for e in events:
        if "_id" in e:
            e["id"] = str(e["_id"])
    return events

@router.post("/{incident_id}/feedback")
async def submit_feedback(
    incident_id: str,
    body: FeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    doc = await incident_repo.get_by_id(incident_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    
    from app.core.database import DatabaseManager
    col = DatabaseManager.get_collection("evalFeedback")
    await col.insert_one({
        "incidentId": incident_id,
        "username": current_user.get("username"),
        "role": current_user.get("role"),
        "useful": body.useful,
        "notes": body.notes,
        "timestamp": datetime.now(timezone.utc)
    })
    return {"success": True, "message": "Feedback recorded"}
