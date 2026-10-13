from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import secrets
import httpx

from app.api.deps import require_roles, get_current_user
from app.models.user import UserRole
from app.core.database import DatabaseManager
from app.core.config import settings

from app.services.audit import audit_service

router = APIRouter(prefix="/admin", tags=["admin"])

class LogSourceCreate(BaseModel):
    name: str
    description: Optional[str] = None

class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    threshold: Optional[int] = None
    windowMinutes: Optional[int] = None

@router.get("/sources")
async def list_log_sources(current_user: dict = Depends(require_roles([UserRole.ADMIN]))):
    col = DatabaseManager.get_collection("logSources")
    sources = await col.find({}).to_list(100)
    for s in sources:
        if "_id" in s:
            s["id"] = str(s["_id"])
        # Mask API key in responses to prevent credential exposure
        if "apiKey" in s and s["apiKey"]:
            raw_key = str(s["apiKey"])
            if len(raw_key) > 10:
                s["apiKey"] = f"{raw_key[:6]}...{raw_key[-4:]}"
            else:
                s["apiKey"] = "src_***"
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
    
    actor = current_user.get("username", "admin")
    await audit_service.log_event(
        action="LOG_SOURCE_CONFIGURED",
        actor=actor,
        role=current_user.get("role", "admin"),
        entity_type="logSource",
        entity_id=payload.name,
        details={"name": payload.name, "description": payload.description}
    )
    
    return {"message": "Log source configured", "sourceId": payload.name, "apiKey": api_key}

@router.get("/rules")
async def list_detection_rules(current_user: dict = Depends(require_roles([UserRole.ADMIN]))):
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
    
    actor = current_user.get("username", "admin")
    await audit_service.log_event(
        action="DETECTION_RULE_UPDATED",
        actor=actor,
        role=current_user.get("role", "admin"),
        entity_type="detectionRule",
        entity_id=rule_id,
        details=up_dict
    )
    
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

from app.services.analytics import analytics_service

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    time_range: str = "24h",
    service: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    return await analytics_service.get_dashboard_analytics(time_range=time_range, service=service)

@router.post("/retention/cleanup")
async def trigger_retention_cleanup(
    days: int = 30,
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    logs_col = DatabaseManager.get_collection("logEvents")
    res = await logs_col.delete_many({"timestamp": {"$lt": cutoff}})
    deleted_cnt = getattr(res, "deleted_count", res) if res is not None else 0
    
    actor = current_user.get("username", "admin")
    await audit_service.log_event(
        action="RETENTION_CLEANUP_EXECUTED",
        actor=actor,
        role=current_user.get("role", "admin"),
        entity_type="system",
        entity_id="retentionPolicy",
        details={"days": days, "deletedCount": deleted_cnt, "cutoff": cutoff.isoformat()}
    )
    
    return {
        "message": f"Pruned logs older than {days} days",
        "cutoff": cutoff.isoformat(),
        "deletedCount": deleted_cnt
    }

@router.get("/demo/status")
async def get_demo_status(current_user: dict = Depends(get_current_user)):
    url = f"{settings.DEMO_APP_URL.rstrip('/')}/health"
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            return resp.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}

class DemoFaultPayload(BaseModel):
    faultType: str

@router.post("/demo/inject-fault")
async def trigger_demo_fault(
    payload: DemoFaultPayload,
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    url = f"{settings.DEMO_APP_URL.rstrip('/')}/faults/{payload.faultType}"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(url)
            if resp.status_code == 200:
                actor = current_user.get("username", "admin")
                await audit_service.log_event(
                    action="DEMO_FAULT_INJECTED",
                    actor=actor,
                    role=current_user.get("role", "admin"),
                    entity_type="demoApp",
                    entity_id=payload.faultType,
                    details={"faultType": payload.faultType}
                )
                return resp.json()
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

@router.post("/demo/reset-fault")
async def reset_demo_fault(current_user: dict = Depends(require_roles([UserRole.ADMIN]))):
    url = f"{settings.DEMO_APP_URL.rstrip('/')}/admin/reset-fault"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(url)
            if resp.status_code == 200:
                actor = current_user.get("username", "admin")
                await audit_service.log_event(
                    action="DEMO_FAULT_RESET",
                    actor=actor,
                    role=current_user.get("role", "admin"),
                    entity_type="demoApp",
                    entity_id="all",
                    details={"status": "fault_cleared"}
                )
                return resp.json()
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

