from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import secrets

from app.api.deps import require_roles, get_current_user
from app.models.user import UserRole
from app.core.database import DatabaseManager
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

class LogSourceCreate(BaseModel):
    name: str
    description: Optional[str] = None

class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    threshold: Optional[int] = None
    windowMinutes: Optional[int] = None

@router.get("/sources")
async def list_log_sources(current_user: dict = Depends(get_current_user)):
    col = DatabaseManager.get_collection("logSources")
    sources = await col.find({}).to_list(100)
    for s in sources:
        if "_id" in s:
            s["id"] = str(s["_id"])
    return sources

@router.post("/sources")
async def create_or_rotate_source(
    payload: LogSourceCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    col = DatabaseManager.get_collection("logSources")
    api_key = f"src_{secrets.token_hex(16)}"
    now = datetime.now(timezone.utc)
    doc = {
        "sourceId": payload.name,
        "name": payload.name,
        "description": payload.description,
        "apiKey": api_key,
        "status": "configured",
        "eventCount": 0,
        "createdAt": now,
        "lastSeenAt": now
    }
    await col.update_one(
        {"sourceId": payload.name},
        {"$set": doc},
        upsert=True
    )
    return {"message": "Log source configured", "sourceId": payload.name, "apiKey": api_key}

@router.get("/rules")
async def list_detection_rules(current_user: dict = Depends(get_current_user)):
    col = DatabaseManager.get_collection("detectionRules")
    rules = await col.find({}).to_list(100)
    for r in rules:
        if "_id" in r:
            r["id"] = str(r["_id"])
    return rules

@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    update: RuleUpdate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    col = DatabaseManager.get_collection("detectionRules")
    up_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    if not up_dict:
        return {"updated": False}
    res = await col.update_one({"_id": rule_id}, {"$set": up_dict})
    return {"updated": True, "ruleId": rule_id}

@router.get("/settings")
async def get_system_settings(current_user: dict = Depends(require_roles([UserRole.ADMIN]))):
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "openai_model": settings.OPENAI_MODEL,
        "anthropic_model": settings.ANTHROPIC_MODEL,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
        "environment": settings.ENVIRONMENT,
        "demo_app_url": settings.DEMO_APP_URL
    }
