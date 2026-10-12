from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.models.log_event import LogFilterParams, LogSeverity, SourceType
from app.api.deps import get_current_user
from app.repositories.log_event_repo import log_event_repo

router = APIRouter(prefix="/logs", tags=["logs"])

class LogListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int

@router.get("", response_model=LogListResponse)
async def get_logs(
    service: Optional[str] = None,
    severity: Optional[LogSeverity] = None,
    source_type: Optional[SourceType] = None,
    source_id: Optional[str] = None,
    upload_id: Optional[str] = None,
    fingerprint: Optional[str] = None,
    search: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    params = LogFilterParams(
        service=service,
        severity=severity,
        source_type=source_type,
        source_id=source_id,
        upload_id=upload_id,
        fingerprint=fingerprint,
        search=search,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )
    items, total = await log_event_repo.find_events(params)
    # Ensure serializable format
    for item in items:
        if "_id" in item:
            item["id"] = str(item["_id"])
    return LogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/services", response_model=List[str])
async def get_distinct_services(current_user: dict = Depends(get_current_user)):
    col = log_event_repo.col
    # Support both distinct and manual collection iteration
    if hasattr(col, "distinct"):
        services = await col.distinct("service")
        return sorted([s for s in services if s])
    else:
        # InMemory fallback
        all_docs = await col.find({}).to_list(1000)
        return sorted(list(set(d.get("service") for d in all_docs if d.get("service"))))
