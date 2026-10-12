import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.remediation import (
    RemediationActionDef,
    ActionApprovalRecord,
    ApprovalStatus,
    ExecutionResult
)
from app.models.user import UserRole
from app.api.deps import get_current_user, require_roles
from app.services.policy import policy_service
from app.services.remediation import remediation_executor
from app.services.health_checks import health_check_service
from app.services.audit import audit_service
from app.core.database import DatabaseManager
from app.repositories.incident_repo import incident_repo

router = APIRouter(prefix="/remediation", tags=["remediation"])

class ActionRequestPayload(BaseModel):
    incidentId: str
    actionName: str
    parameters: Dict[str, Any] = {}

class ApprovalDecisionPayload(BaseModel):
    decision: str  # "approved" or "rejected"
    reason: Optional[str] = None

@router.get("/actions", response_model=List[RemediationActionDef], response_model_by_alias=False)
async def list_remediation_actions(current_user: dict = Depends(get_current_user)):
    col = DatabaseManager.get_collection("remediationActions")
    docs = await col.find({}).to_list(100)
    for d in docs:
        if "_id" in d:
            d["id"] = str(d["_id"])
    return [RemediationActionDef(**d) for d in docs]

@router.post("/request", response_model=ActionApprovalRecord, response_model_by_alias=False)
async def request_action(
    payload: ActionRequestPayload,
    current_user: dict = Depends(get_current_user)
):
    user_role = current_user.get("role", "support_engineer")
    username = current_user.get("username", "anonymous")

    # Policy validation
    action = await policy_service.validate_action_request(payload.actionName, user_role)

    # Incident existence check
    incident = await incident_repo.get_by_id(payload.incidentId)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    approval_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=30)

    # If action doesn't require approval, auto-approve
    requires_approval = action.get("requiresApproval", True)
    initial_status = ApprovalStatus.PENDING if requires_approval else ApprovalStatus.APPROVED

    doc = {
        "_id": approval_id,
        "incidentId": payload.incidentId,
        "actionName": payload.actionName,
        "status": initial_status.value,
        "requestedBy": username,
        "requestedByRole": user_role,
        "approvedBy": "auto-policy" if not requires_approval else None,
        "approvedByRole": "system" if not requires_approval else None,
        "rejectionReason": None,
        "parameters": payload.parameters,
        "createdAt": now,
        "updatedAt": now,
        "expiresAt": expires_at
    }

    col = DatabaseManager.get_collection("actionApprovals")
    await col.insert_one(doc)

    # Transition incident status to awaiting_approval if approval required
    if requires_approval:
        await incident_repo.update(payload.incidentId, {"status": "awaiting_approval"})

    await audit_service.log_event(
        action="REMEDIATION_ACTION_REQUESTED",
        actor=username,
        role=user_role,
        entity_type="actionApproval",
        entity_id=approval_id,
        details={
            "actionName": payload.actionName,
            "incidentId": payload.incidentId,
            "requiresApproval": requires_approval
        }
    )

    doc["id"] = approval_id
    return ActionApprovalRecord(**doc)

@router.get("/approvals", response_model=List[ActionApprovalRecord], response_model_by_alias=False)
async def list_approvals(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    col = DatabaseManager.get_collection("actionApprovals")
    fltr = {"status": status} if status else {}
    cursor = col.find(fltr).sort("createdAt", -1)
    items = await cursor.to_list(100)
    for i in items:
        if "_id" in i:
            i["id"] = str(i["_id"])
    return [ActionApprovalRecord(**i) for i in items]

@router.post("/approvals/{approval_id}/decision", response_model=ActionApprovalRecord, response_model_by_alias=False)
async def decide_approval(
    approval_id: str,
    payload: ApprovalDecisionPayload,
    current_user: dict = Depends(require_roles([UserRole.APPROVER, UserRole.ADMIN]))
):
    col = DatabaseManager.get_collection("actionApprovals")
    doc = await col.find_one({"_id": approval_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval record not found")

    username = current_user.get("username", "anonymous")
    user_role = current_user.get("role", "approver")

    # Backend Policy Verification (Blocks self-approval and invalid status transitions!)
    await policy_service.validate_approval_decision(
        approval_doc=doc,
        approver_username=username,
        approver_role=user_role
    )

    now = datetime.now(timezone.utc)
    new_status = ApprovalStatus.APPROVED if payload.decision.lower() == "approved" else ApprovalStatus.REJECTED

    updates = {
        "status": new_status.value,
        "approvedBy": username,
        "approvedByRole": user_role,
        "rejectionReason": payload.reason if new_status == ApprovalStatus.REJECTED else None,
        "updatedAt": now
    }
    await col.update_one({"_id": approval_id}, {"$set": updates})

    await audit_service.log_event(
        action=f"APPROVAL_DECISION_{new_status.value.upper()}",
        actor=username,
        role=user_role,
        entity_type="actionApproval",
        entity_id=approval_id,
        details={"decision": new_status.value, "reason": payload.reason}
    )

    doc.update(updates)
    doc["id"] = approval_id
    return ActionApprovalRecord(**doc)

@router.post("/execute/{approval_id}")
async def execute_remediation(
    approval_id: str,
    current_user: dict = Depends(get_current_user)
):
    col = DatabaseManager.get_collection("actionApprovals")
    approval_doc = await col.find_one({"_id": approval_id})
    if not approval_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval record not found")

    user_role = current_user.get("role", "support_engineer")
    username = current_user.get("username", "anonymous")

    # Backend policy enforcement immediately before execution!
    action_def = await policy_service.validate_execution(
        approval_doc=approval_doc,
        executor_role=user_role
    )

    incident_id = approval_doc.get("incidentId")
    action_name = approval_doc.get("actionName")

    # Move incident to 'remediating'
    await incident_repo.update(incident_id, {"status": "remediating"})

    # Execute action via fixed code path
    success, output = await remediation_executor.execute_allow_listed_action(
        executor_key=action_def.get("executorKey"),
        parameters=approval_doc.get("parameters", {})
    )

    now = datetime.now(timezone.utc)
    exec_status = "executed" if success else "failed"

    # Update approval record status
    await col.update_one(
        {"_id": approval_id},
        {"$set": {"status": exec_status, "updatedAt": now}}
    )

    # Store execution result
    exec_col = DatabaseManager.get_collection("actionExecutions")
    await exec_col.insert_one({
        "_id": str(uuid.uuid4()),
        "approvalId": approval_id,
        "incidentId": incident_id,
        "actionName": action_name,
        "status": exec_status,
        "output": output,
        "actor": username,
        "approver": approval_doc.get("approvedBy"),
        "timestamp": now
    })

    await audit_service.log_event(
        action="REMEDIATION_ACTION_EXECUTED",
        actor=username,
        role=user_role,
        entity_type="incident",
        entity_id=incident_id,
        details={"actionName": action_name, "success": success, "output": output}
    )

    if not success:
        await incident_repo.update(incident_id, {
            "status": "escalated",
            "escalationReason": f"Remediation action '{action_name}' execution failed: {output.get('error')}"
        })
        return {
            "status": "failed",
            "message": f"Remediation action failed: {output.get('error')}",
            "verified": False
        }

    # Fetch linked ticket if exists
    inc_doc = await incident_repo.get_by_id(incident_id)
    ticket_id = inc_doc.get("ticketId") if inc_doc else None

    # Trigger recovery verification check in background
    health_check_path = action_def.get("associatedHealthCheck", "/health")
    asyncio.create_task(
        health_check_service.verify_recovery(
            incident_id=incident_id,
            ticket_id=ticket_id,
            health_check_path=health_check_path
        )
    )

    return {
        "status": "executing_recovery_verification",
        "message": f"Action '{action_name}' ran successfully. Verifying recovery health checks...",
        "verified": False
    }
