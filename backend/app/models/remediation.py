from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from app.models.user import UserRole

class ActionRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    READY_TO_EXECUTE = "ready_to_execute"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    EXECUTED = "executed"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    FAILED = "failed"
    EXPIRED = "expired"

class RemediationActionDef(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=False)
    id: str = Field(default="", alias="_id")
    name: str
    description: str
    riskLevel: ActionRiskLevel = ActionRiskLevel.MEDIUM
    requiresApproval: bool = True
    requiresDualApproval: bool = False
    allowedRoles: List[UserRole]
    parametersSchema: Dict[str, Any] = Field(default_factory=dict)
    executorKey: str
    associatedHealthCheck: str = "/health"
    timeoutSeconds: int = 30
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RemediationRecommendation(BaseModel):
    actionName: str
    actionTitle: str
    relevanceReason: str
    supportingEvidence: List[str] = Field(default_factory=list)
    expectedOutcome: str
    riskLevel: ActionRiskLevel = ActionRiskLevel.MEDIUM
    affectedService: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    requiresApproval: bool = True
    confidence: float = 0.90
    runbookReference: Optional[str] = None
    historicalIncidentReference: Optional[str] = None

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
    justification: Optional[str] = None
    riskLevel: Optional[str] = None
    expectedOutcome: Optional[str] = None
    supportingEvidence: Optional[List[str]] = Field(default_factory=list)
    runbookReference: Optional[str] = None
    executionId: Optional[str] = None
    executionError: Optional[str] = None
    verificationStatus: Optional[str] = None
    verifiedAt: Optional[datetime] = None
    verificationError: Optional[str] = None
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
