import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.core.database import DatabaseManager
from app.models.log_event import LogFilterParams

class LogEventRepository:
    @property
    def col(self):
        return DatabaseManager.get_collection("logEvents")

    async def insert_many(self, events: List[Dict[str, Any]]) -> List[str]:
        if not events:
            return []
        for e in events:
            if "_id" not in e:
                e["_id"] = str(uuid.uuid4())
        res = await self.col.insert_many(events)
        return res.inserted_ids

    async def insert_one(self, event: Dict[str, Any]) -> str:
        if "_id" not in event:
            event["_id"] = str(uuid.uuid4())
        await self.col.insert_one(event)
        return event["_id"]

    async def find_events(self, params: LogFilterParams) -> Tuple[List[Dict[str, Any]], int]:
        filter_dict: Dict[str, Any] = {}
        if params.service:
            filter_dict["service"] = params.service
        if params.severity:
            filter_dict["severity"] = params.severity.value
        if params.source_type:
            filter_dict["source.type"] = params.source_type.value
        if params.source_id:
            filter_dict["source.sourceId"] = params.source_id
        if params.upload_id:
            filter_dict["source.uploadId"] = params.upload_id
        if params.fingerprint:
            filter_dict["fingerprint"] = params.fingerprint

        time_filter = {}
        if params.start_time:
            time_filter["$gte"] = params.start_time
        if params.end_time:
            time_filter["$lte"] = params.end_time
        if time_filter:
            filter_dict["timestamp"] = time_filter

        if params.search:
            # Use regex for flexible matching in both Mongo and In-Memory
            filter_dict["message"] = {"$regex": params.search}

        total = await self.col.count_documents(filter_dict)
        skip = (params.page - 1) * params.page_size
        cursor = self.col.find(filter_dict).sort("timestamp", -1).skip(skip).limit(params.page_size)
        items = await cursor.to_list(length=params.page_size)
        return items, total

    async def get_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        cursor = self.col.find({"_id": {"$in": ids}}).sort("timestamp", 1)
        return await cursor.to_list(length=len(ids))

    async def get_service_events_in_window(self, service: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        cursor = self.col.find({
            "service": service,
            "timestamp": {"$gte": start, "$lte": end}
        }).sort("timestamp", 1)
        return await cursor.to_list(length=1000)

log_event_repo = LogEventRepository()
