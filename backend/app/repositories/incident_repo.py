import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from app.core.database import DatabaseManager
from app.models.incident import IncidentFilterParams, IncidentStatus

class IncidentRepository:
    @property
    def col(self):
        return DatabaseManager.get_collection("incidents")

    async def create(self, incident_doc: Dict[str, Any]) -> str:
        if "_id" not in incident_doc:
            incident_doc["_id"] = str(uuid.uuid4())
        await self.col.insert_one(incident_doc)
        return incident_doc["_id"]

    async def get_by_id(self, incident_id: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"_id": incident_id})

    async def find_matching_open_incident(
        self,
        service: str,
        fingerprint: str,
        window_minutes: int = 15
    ) -> Optional[Dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        filter_dict = {
            "service": service,
            "fingerprint": fingerprint,
            "status": {"$in": ["new", "analyzing", "analyzed", "awaiting_approval", "remediating", "verifying"]},
            "lastSeen": {"$gte": since}
        }
        return await self.col.find_one(filter_dict)

    async def find_recently_resolved_incident(
        self,
        service: str,
        fingerprint: str,
        window_minutes: int = 15
    ) -> Optional[Dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        filter_dict = {
            "service": service,
            "fingerprint": fingerprint,
            "status": "resolved",
            "updatedAt": {"$gte": since}
        }
        return await self.col.find_one(filter_dict)

    async def add_events_to_incident(
        self,
        incident_id: str,
        event_ids: List[str],
        source: str,
        last_seen: datetime
    ):
        await self.col.update_one(
            {"_id": incident_id},
            {
                "$inc": {"eventCount": len(event_ids)},
                "$set": {
                    "lastSeen": last_seen,
                    "updatedAt": datetime.now(timezone.utc)
                },
                "$addToSet": {
                    "sources": source
                },
                "$push": {
                    "eventRefs": {"$each": event_ids}
                }
            }
        )

    async def update(self, incident_id: str, updates: Dict[str, Any]):
        updates["updatedAt"] = datetime.now(timezone.utc)
        await self.col.update_one({"_id": incident_id}, {"$set": updates})

    async def list_incidents(self, params: IncidentFilterParams) -> Tuple[List[Dict[str, Any]], int]:
        filter_dict: Dict[str, Any] = {}
        if params.status:
            filter_dict["status"] = params.status.value
        if params.severity:
            filter_dict["severity"] = params.severity.value
        if params.service:
            filter_dict["service"] = params.service
        if params.source:
            filter_dict["sources"] = params.source

        time_filter = {}
        if params.start_time:
            time_filter["$gte"] = params.start_time
        if params.end_time:
            time_filter["$lte"] = params.end_time
        if time_filter:
            filter_dict["firstSeen"] = time_filter

        total = await self.col.count_documents(filter_dict)
        skip = (params.page - 1) * params.page_size
        cursor = self.col.find(filter_dict).sort("updatedAt", -1).skip(skip).limit(params.page_size)
        items = await cursor.to_list(length=params.page_size)
        return items, total

incident_repo = IncidentRepository()
