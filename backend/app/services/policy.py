from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from app.core.database import DatabaseManager
from app.models.remediation import ApprovalStatus
from app.models.user import UserRole

class PolicyViolationError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_403_FORBIDDEN):
        super().__init__(status_code=status_code, detail=detail)

class PolicyService:
    async def get_allow_listed_action(self, action_name: str) -> Dict[str, Any]:
        col = DatabaseManager.get_collection("remediationActions")
        action = await col.find_one({"name": action_name})
        if not action:
            raise PolicyViolationError(
                f"Action '{action_name}' is not in the approved remediation allow-list",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        return action

    async def validate_action_request(self, action_name: str, requester_role: str):
        action = await self.get_allow_listed_action(action_name)
        if requester_role not in ("support_engineer", "approver", "admin"):
            raise PolicyViolationError(
                f"Role '{requester_role}' is not authorized to create approval requests",
                status_code=status.HTTP_403_FORBIDDEN
            )
        return action

    async def validate_approval_decision(
        self,
        approval_doc: Dict[str, Any],
        approver_username: str,
        approver_role: str
    ):
        if approver_role not in ("approver", "senior_approver", "admin"):
            raise PolicyViolationError(
                "Only Approvers (role: approver) can decide on approval requests",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Self-approval prevention
        if approval_doc.get("requestedBy") == approver_username:
            raise PolicyViolationError(
                "Self-approval policy violation: Requester cannot approve their own protected action request"
            )

        if approval_doc.get("status") != ApprovalStatus.PENDING.value:
            raise PolicyViolationError(
                f"Cannot decide on approval with status '{approval_doc.get('status')}'",
                status_code=status.HTTP_409_CONFLICT
            )

        # Expiry check
        now = datetime.now(timezone.utc)
        expires_at = approval_doc.get("expiresAt")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now > expires_at:
                raise PolicyViolationError(
                    "Approval decision rejected: Request has expired. A fresh approval request must be submitted.",
                    status_code=status.HTTP_410_GONE
                )

    async def validate_execution(
        self,
        approval_doc: Dict[str, Any],
        executor_role: str
    ) -> Dict[str, Any]:
        # 1. Allow-list check
        action_name = approval_doc.get("actionName")
        action = await self.get_allow_listed_action(action_name)

        # 2. Role authorization check
        allowed_roles = action.get("allowedRoles", [])
        if executor_role not in allowed_roles and executor_role != "admin":
            raise PolicyViolationError(
                f"Role '{executor_role}' is not authorized to execute action '{action_name}'. Allowed: {allowed_roles}"
            )

        # 3. Check if action requires approval
        if action.get("requiresApproval", True):
            # 4. Check approval state
            if approval_doc.get("status") != ApprovalStatus.APPROVED.value:
                raise PolicyViolationError(
                    f"Execution blocked: Action '{action_name}' requires approval, but approval status is '{approval_doc.get('status')}'"
                )

            # 5. Check expiry
            now = datetime.now(timezone.utc)
            expires_at = approval_doc.get("expiresAt")
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if now > expires_at:
                    raise PolicyViolationError(
                        "Execution blocked: Approval has expired. A new approval request must be submitted.",
                        status_code=status.HTTP_410_GONE
                    )

        return action

    async def validate_direct_execution(
        self,
        action_name: str,
        executor_role: str,
        incident_id: str
    ) -> Dict[str, Any]:
        # 1. Allow-list check
        action = await self.get_allow_listed_action(action_name)

        # 2. Check executor role authorization: Only approvers (and admin) can directly resolve
        if executor_role not in ("approver", "admin"):
            raise PolicyViolationError(
                f"Role '{executor_role}' is not authorized for direct remediation resolution. Only approvers can directly execute eligible remediations.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        allowed_roles = action.get("allowedRoles", [])
        if executor_role not in allowed_roles and executor_role != "admin":
            raise PolicyViolationError(
                f"Role '{executor_role}' is not authorized to execute action '{action_name}'. Allowed: {allowed_roles}",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # 3. High-risk, destructive, or dual-approval restricted actions CANNOT bypass approval
        risk_level = str(action.get("riskLevel", "")).lower()
        requires_dual_approval = action.get("requiresDualApproval", False)
        if risk_level == "critical" or requires_dual_approval:
            raise PolicyViolationError(
                f"Policy Restriction: Action '{action_name}' is classified as Critical / Destructive risk ({risk_level}). Direct single-approver execution is prohibited; formal dual-authorization is mandatory.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        return action

policy_service = PolicyService()
