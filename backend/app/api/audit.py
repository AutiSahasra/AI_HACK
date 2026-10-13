from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any, Optional
from app.models.audit import AuditLog
from app.services.audit import audit_service
from app.api.deps import require_roles
from app.models.user import UserRole

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("", response_model=List[AuditLog])
async def list_audit_trail(
    actor: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_roles([UserRole.APPROVER, UserRole.ADMIN]))
):
    items = await audit_service.list_audit_logs(
        actor=actor,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit
    )
    return [AuditLog(**i) for i in items]
