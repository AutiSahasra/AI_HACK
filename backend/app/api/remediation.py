import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from pydantic import BaseModel

from app.models.remediation import (
    RemediationActionDef,
    ActionApprovalRecord,
    ApprovalStatus,
    ExecutionResult,
    RemediationRecommendation
)
from app.models.user import UserRole
from app.api.deps import get_current_user, require_roles
from app.services.policy import policy_service
from app.services.remediation import remediation_executor
from app.services.health_checks import health_check_service
from app.services.recommendation import recommendation_service
from app.services.audit import audit_service
from app.core.database import DatabaseManager
from app.repositories.incident_repo import incident_repo

router = APIRouter(prefix="/remediation", tags=["remediation"])

class ActionRequestPayload(BaseModel):
    incidentId: str
    actionName: str
    parameters: Dict[str, Any] = {}
    justification: Optional[str] = None
    riskLevel: Optional[str] = None
    expectedOutcome: Optional[str] = None
    supportingEvidence: Optional[List[str]] = None
    runbookReference: Optional[str] = None

class DirectExecutionPayload(BaseModel):
    incidentId: str
    actionName: str
    parameters: Dict[str, Any] = {}
    justification: Optional[str] = None

class ApprovalDecisionPayload(BaseModel):
    decision: str  # "approved" or "rejected"
    reason: Optional[str] = None

@router.get("/recommendations/{incident_id}", response_model=List[RemediationRecommendation])
async def get_remediation_recommendations(
    incident_id: str,
    current_user: dict = Depends(get_current_user)
):
    recs = await recommendation_service.get_recommendations_for_incident(incident_id)
    return recs

@router.get("/actions", response_model=List[RemediationActionDef], response_model_by_alias=False)
async def list_remediation_actions(current_user: dict = Depends(get_current_user)):
    col = DatabaseManager.get_collection("remediationActions")
    docs = await col.find({}).to_list(100)
    for d in docs:
        if "_id" in d:
            d["id"] = str(d["_id"])
    return [RemediationActionDef(**d) for d in docs]

@router.post("/direct-execute")
async def direct_execute_remediation(
    payload: DirectExecutionPayload,
    current_user: dict = Depends(require_roles([UserRole.APPROVER]))
):
    user_role = current_user.get("role", "approver")
    username = current_user.get("username", "anonymous")

    incident = await incident_repo.get_by_id(payload.incidentId)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    # Backend Policy validation (enforces allow-list, permitted roles, and strictly blocks Critical/destructive bypass)
    action_def = await policy_service.validate_direct_execution(
        action_name=payload.actionName,
        executor_role=user_role,
        incident_id=payload.incidentId
    )

    now = datetime.now(timezone.utc)
    execution_id = str(uuid.uuid4())

    # Move incident to 'remediating'
    await incident_repo.update(payload.incidentId, {"status": "remediating"})

    # Execute action via allow-listed compiled dispatch table
    success, output = await remediation_executor.execute_allow_listed_action(
        executor_key=action_def.get("executorKey"),
        parameters=payload.parameters
    )

    exec_status = "executed" if success else "failed"

    # Store execution result in actionExecutions collection
    exec_col = DatabaseManager.get_collection("actionExecutions")
    await exec_col.insert_one({
        "_id": execution_id,
        "incidentId": payload.incidentId,
        "actionName": payload.actionName,
        "status": exec_status,
        "output": output,
        "actor": username,
        "role": user_role,
        "directExecution": True,
        "justification": payload.justification or "Direct Approver Resolution",
        "timestamp": now
    })

    # Record in Immutable Audit Trail
    await audit_service.log_event(
        action="DIRECT_REMEDIATION_EXECUTED",
        actor=username,
        role=user_role,
        entity_type="incident",
        entity_id=payload.incidentId,
        details={
            "actionName": payload.actionName,
            "success": success,
            "output": output,
            "directExecution": True,
            "justification": payload.justification
        }
    )

    # Fetch linked ticket if exists
    ticket_id = incident.get("ticketId")
    ticket_col = DatabaseManager.get_collection("tickets")
    if not ticket_id:
        t_doc = await ticket_col.find_one({"incidentId": payload.incidentId})
        if t_doc:
            ticket_id = str(t_doc["_id"])

    if not success:
        await incident_repo.update(payload.incidentId, {
            "status": "escalated",
            "escalationReason": f"Direct remediation action '{payload.actionName}' execution failed: {output.get('error')}"
        })
        if ticket_id:
            fail_comment = {
                "id": str(uuid.uuid4())[:8],
                "author": "system",
                "authorRole": "system",
                "text": f"Direct remediation action '{payload.actionName}' execution failed: {output.get('error')}. Ticket automatically escalated.",
                "createdAt": now
            }
            await ticket_col.update_one(
                {"_id": ticket_id},
                {
                    "$set": {"status": "escalated", "updatedAt": now},
                    "$push": {"comments": fail_comment}
                }
            )
        return {
            "status": "failed",
            "message": f"Remediation action failed: {output.get('error')}",
            "verified": False,
            "executionId": execution_id
        }

    # Trigger recovery verification check in background
    health_check_path = action_def.get("associatedHealthCheck", "/health")
    asyncio.create_task(
        health_check_service.verify_recovery(
            incident_id=payload.incidentId,
            ticket_id=ticket_id,
            health_check_path=health_check_path
        )
    )

    return {
        "status": "executing_recovery_verification",
        "message": f"Action '{payload.actionName}' executed directly by {username}. Verifying recovery health checks...",
        "verified": False,
        "executionId": execution_id
    }

@router.post("/request", response_model=ActionApprovalRecord, response_model_by_alias=False)
async def request_action(
    payload: ActionRequestPayload,
    current_user: dict = Depends(require_roles([UserRole.SUPPORT_ENGINEER, UserRole.ADMIN]))
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
        "justification": payload.justification,
        "riskLevel": payload.riskLevel or str(action.get("riskLevel", "medium")),
        "expectedOutcome": payload.expectedOutcome,
        "supportingEvidence": payload.supportingEvidence or [],
        "runbookReference": payload.runbookReference,
        "createdAt": now,
        "updatedAt": now,
        "expiresAt": expires_at
    }

    col = DatabaseManager.get_collection("actionApprovals")
    await col.insert_one(doc)

    # Transition incident status to awaiting_approval if approval required
    if requires_approval:
        await incident_repo.update(payload.incidentId, {"status": "awaiting_approval"})

    # Synchronize linked ticket status to pending_approval and append comment
    ticket_col = DatabaseManager.get_collection("tickets")
    t_doc = await ticket_col.find_one({"incidentId": payload.incidentId})
    if not t_doc and incident.get("ticketId"):
        t_doc = await ticket_col.find_one({"_id": incident["ticketId"]})

    if t_doc:
        ticket_id = str(t_doc["_id"])
        ticket_status_to_set = "pending_approval" if requires_approval else "verifying"
        comment = {
            "id": str(uuid.uuid4())[:8],
            "author": username,
            "authorRole": user_role,
            "text": f"Remediation action '{payload.actionName}' requested (Risk: {doc['riskLevel']}). Justification: {payload.justification or 'No justification provided'}. Routed to Senior Approver queue.",
            "createdAt": now
        }
        await ticket_col.update_one(
            {"_id": ticket_id},
            {
                "$set": {"status": ticket_status_to_set, "updatedAt": now},
                "$push": {"comments": comment}
            }
        )

    await audit_service.log_event(
        action="REMEDIATION_ACTION_REQUESTED",
        actor=username,
        role=user_role,
        entity_type="actionApproval",
        entity_id=approval_id,
        details={
            "actionName": payload.actionName,
            "incidentId": payload.incidentId,
            "requiresApproval": requires_approval,
            "justification": payload.justification
        }
    )

    doc["id"] = approval_id
    return ActionApprovalRecord(**doc)

@router.get("/my-requests", response_model=List[ActionApprovalRecord], response_model_by_alias=False)
async def list_my_requests(
    current_user: dict = Depends(get_current_user)
):
    username = current_user.get("username", "")
    col = DatabaseManager.get_collection("actionApprovals")
    cursor = col.find({"requestedBy": username}).sort("createdAt", -1)
    items = await cursor.to_list(100)
    for i in items:
        if "_id" in i:
            i["id"] = str(i["_id"])
    return [ActionApprovalRecord(**i) for i in items]

@router.get("/incident/{incident_id}/requests", response_model=List[ActionApprovalRecord], response_model_by_alias=False)
async def list_incident_requests(
    incident_id: str,
    current_user: dict = Depends(get_current_user)
):
    col = DatabaseManager.get_collection("actionApprovals")
    cursor = col.find({"incidentId": incident_id}).sort("createdAt", -1)
    items = await cursor.to_list(20)
    for i in items:
        if "_id" in i:
            i["id"] = str(i["_id"])
    return [ActionApprovalRecord(**i) for i in items]

@router.get("/approvals", response_model=List[ActionApprovalRecord], response_model_by_alias=False)
async def list_approvals(
    status: Optional[str] = None,
    current_user: dict = Depends(require_roles([UserRole.APPROVER]))
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
    current_user: dict = Depends(require_roles([UserRole.APPROVER]))
):
    decision_clean = payload.decision.lower().strip()
    if decision_clean not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be either 'approved' or 'rejected'"
        )

    # Rejection requires mandatory rationale
    if decision_clean == "rejected":
        if not payload.reason or not payload.reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A rejection reason/rationale is mandatory when rejecting a remediation request"
            )

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
    new_status = ApprovalStatus.APPROVED if decision_clean == "approved" else ApprovalStatus.REJECTED

    updates = {
        "status": new_status.value,
        "approvedBy": username,
        "approvedByRole": user_role,
        "rejectionReason": payload.reason.strip() if new_status == ApprovalStatus.REJECTED else None,
        "updatedAt": now
    }
    
    # Concurrency-safe atomic transition from 'pending' state
    res = await col.update_one(
        {"_id": approval_id, "status": ApprovalStatus.PENDING.value},
        {"$set": updates}
    )
    if res.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Approval request was already decided or is no longer in pending status"
        )

    incident_id = doc.get("incidentId")
    action_name = doc.get("actionName", "remediation action")
    ticket_col = DatabaseManager.get_collection("tickets")
    t_doc = None
    if incident_id:
        t_doc = await ticket_col.find_one({"incidentId": incident_id})
        if not t_doc:
            inc_doc = await incident_repo.get_by_id(incident_id)
            if inc_doc and inc_doc.get("ticketId"):
                t_doc = await ticket_col.find_one({"_id": inc_doc["ticketId"]})

    if new_status == ApprovalStatus.REJECTED:
        rejection_reason = payload.reason.strip()
        # Revert incident back to analyzed so supporter can review alternative options
        if incident_id:
            await incident_repo.update(incident_id, {
                "status": "analyzed",
                "rejectionReason": rejection_reason
            })

        # Revert ticket to in_progress with explicit rejection reason comment
        if t_doc:
            ticket_id = str(t_doc["_id"])
            reject_comment = {
                "id": str(uuid.uuid4())[:8],
                "author": username,
                "authorRole": user_role,
                "text": f"Remediation request for '{action_name}' was REJECTED by Senior Approver @{username}. Reason: {rejection_reason}. Please review alternative fixes.",
                "createdAt": now
            }
            await ticket_col.update_one(
                {"_id": ticket_id},
                {
                    "$set": {"status": "in_progress", "updatedAt": now},
                    "$push": {"comments": reject_comment}
                }
            )
    elif new_status == ApprovalStatus.APPROVED:
        # Notify ticket that request was approved and is pending execution
        if t_doc:
            ticket_id = str(t_doc["_id"])
            approve_comment = {
                "id": str(uuid.uuid4())[:8],
                "author": username,
                "authorRole": user_role,
                "text": f"Remediation request for '{action_name}' was APPROVED by Senior Approver @{username}. Pending execution.",
                "createdAt": now
            }
            await ticket_col.update_one(
                {"_id": ticket_id},
                {
                    "$set": {"updatedAt": now},
                    "$push": {"comments": approve_comment}
                }
            )

    await audit_service.log_event(
        action=f"APPROVAL_DECISION_{new_status.value.upper()}",
        actor=username,
        role=user_role,
        entity_type="actionApproval",
        entity_id=approval_id,
        details={"decision": new_status.value, "reason": updates["rejectionReason"]}
    )

    doc.update(updates)
    doc["id"] = approval_id
    return ActionApprovalRecord(**doc)

@router.post("/execute/{approval_id}")
async def execute_remediation(
    approval_id: str,
    current_user: dict = Depends(require_roles([UserRole.APPROVER]))
):
    col = DatabaseManager.get_collection("actionApprovals")
    approval_doc = await col.find_one({"_id": approval_id})
    if not approval_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval record not found")

    user_role = current_user.get("role", "approver")
    username = current_user.get("username", "anonymous")

    # Backend policy enforcement immediately before execution (checks expiry, role authorization, approval status)
    action_def = await policy_service.validate_execution(
        approval_doc=approval_doc,
        executor_role=user_role
    )

    now = datetime.now(timezone.utc)

    # Concurrency-safe atomic transition from 'approved' to 'executing'
    lock_res = await col.update_one(
        {"_id": approval_id, "status": ApprovalStatus.APPROVED.value},
        {"$set": {"status": "executing", "updatedAt": now}}
    )
    if lock_res.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Action is not in approved state or is already being executed"
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

    # Fetch linked ticket if exists
    inc_doc = await incident_repo.get_by_id(incident_id)
    ticket_id = inc_doc.get("ticketId") if inc_doc else None
    ticket_col = DatabaseManager.get_collection("tickets")
    if not ticket_id:
        t_doc = await ticket_col.find_one({"incidentId": incident_id})
        if t_doc:
            ticket_id = str(t_doc["_id"])

    if not success:
        await incident_repo.update(incident_id, {
            "status": "escalated",
            "escalationReason": f"Remediation action '{action_name}' execution failed: {output.get('error')}"
        })
        if ticket_id:
            fail_comment = {
                "id": str(uuid.uuid4())[:8],
                "author": "system",
                "authorRole": "system",
                "text": f"Remediation action '{action_name}' execution failed: {output.get('error')}. Ticket automatically escalated.",
                "createdAt": now
            }
            await ticket_col.update_one(
                {"_id": ticket_id},
                {
                    "$set": {"status": "escalated", "updatedAt": now},
                    "$push": {"comments": fail_comment}
                }
            )
        return {
            "status": "failed",
            "message": f"Remediation action failed: {output.get('error')}",
            "verified": False
        }

    # Trigger recovery verification check in background
    health_check_path = action_def.get("associatedHealthCheck", "/health")
    asyncio.create_task(
        health_check_service.verify_recovery(
            incident_id=incident_id,
            ticket_id=ticket_id,
            approval_id=approval_id,
            health_check_path=health_check_path
        )
    )

    return {
        "status": "executing_recovery_verification",
        "message": f"Action '{action_name}' ran successfully. Verifying recovery health checks...",
        "verified": False
    }
