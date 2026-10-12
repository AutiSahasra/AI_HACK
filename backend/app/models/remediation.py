from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from app.models.user import UserRole

class ActionRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"

class RemediationActionDef(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=False)
    id: str = Field(default="", alias="_id")
    name: str
    description: str
    riskLevel: ActionRiskLevel = ActionRiskLevel.MEDIUM
    requiresApproval: bool = True
    allowedRoles: List[UserRole]
    parametersSchema: Dict[str, Any] = Field(default_factory=dict)
    executorKey: str
    associatedHealthCheck: str = "/health"
    timeoutSeconds: int = 30
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ActionApprovalRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=False)
    id: str = Field(default="", alias="_id")
    incidentId: str
    actionName: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requestedBy: str
    requestedByRole: UserRole
    approvedBy: Optional[str] = None
    approvedByRole: Optional[UserRole] = None
    rejectionReason: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiresAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExecutionResult(BaseModel):
    id: str
    incidentId: str
    actionName: str
    status: str  # success, failure
    output: Dict[str, Any]
    actor: str
    approver: Optional[str] = None
    startedAt: datetime
    completedAt: datetime
    verifiedRecovery: bool = False
