from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel

from app.api.deps import verify_collector_api_key
from app.services.ingestion import ingestion_service
from app.core.database import DatabaseManager

router = APIRouter(prefix="/ingest", tags=["ingest"])

class IngestBatchRequest(BaseModel):
    sourceId: str = "demo-app-live"
    events: List[Dict[str, Any]]

@router.post("")
async def ingest_live_events(
    payload: IngestBatchRequest,
    api_key: str = Depends(verify_collector_api_key)
):
    if not payload.events:
        return {"ingested": 0, "status": "empty_batch"}

    # Update or register source in logSources
    col = DatabaseManager.get_collection("logSources")
    now = datetime.now(timezone.utc)
    await col.update_one(
        {"sourceId": payload.sourceId},
        {
            "$set": {
                "sourceId": payload.sourceId,
                "name": payload.sourceId,
                "status": "active",
                "lastSeenAt": now,
            },
            "$inc": {"eventCount": len(payload.events)}
        },
        upsert=True
    )

    # Process events through shared pipeline
    normalized = await ingestion_service.process_live_events(
        raw_events=payload.events,
        source_id=payload.sourceId
    )

    return {
        "status": "ok",
        "ingested": len(normalized),
        "sourceId": payload.sourceId,
        "timestamp": now.isoformat()
    }
