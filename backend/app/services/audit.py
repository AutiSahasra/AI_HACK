import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.database import DatabaseManager
from app.models.user import UserRole

logger = logging.getLogger(__name__)

class AuditService:
    @property
    def col(self):
        return DatabaseManager.get_collection("auditLogs")

    async def log_event(
        self,
        action: str,
        actor: str,
        role: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        doc = {
            "_id": log_id,
            "action": action,
            "actor": actor,
            "role": role,
            "entityType": entity_type,
            "entityId": entity_id,
            "details": details or {},
            "timestamp": now
        }
        await self.col.insert_one(doc)
        logger.info(f"AUDIT: [{action}] by {actor} ({role}) on {entity_type}:{entity_id}")
        return log_id

    async def list_audit_logs(
        self,
        actor: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        fltr: Dict[str, Any] = {}
        if actor:
            fltr["actor"] = actor
        if entity_type:
            fltr["entityType"] = entity_type
        if entity_id:
            fltr["entityId"] = entity_id
        cursor = self.col.find(fltr).sort("timestamp", -1).limit(limit)
        items = await cursor.to_list(length=limit)
        for item in items:
            if "_id" in item:
                item["id"] = str(item["_id"])
        return items

audit_service = AuditService()
