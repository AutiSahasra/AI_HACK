from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from app.models.log_event import LogSeverity

class IncidentStatus(str, Enum):
    NEW = "new"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    AWAITING_APPROVAL = "awaiting_approval"
    REMEDIATING = "remediating"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FAILED_ANALYSIS = "failed_analysis"

class EvidenceItem(BaseModel):
    eventId: Optional[str] = None
    excerpt: str

class ProbableCause(BaseModel):
    rank: int
    description: str
    confidence: float = 0.5
    confidenceTier: str = "medium"  # low, medium, high
    supportingEvidence: List[EvidenceItem] = Field(default_factory=list)
    alternativeExplanations: Optional[str] = None
    assumptions: Optional[str] = None
    verified: bool = False

class DiagnosticCheck(BaseModel):
    step: str
    rationale: str

class Incident(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=False)
    id: str = Field(default="", alias="_id")
    title: str
    severity: LogSeverity
    service: str
    status: IncidentStatus = IncidentStatus.NEW
    sources: List[str] = Field(default_factory=list)
    eventRefs: List[str] = Field(default_factory=list)
    eventCount: int = 1
    firstSeen: datetime
    lastSeen: datetime
    matchedRules: List[str] = Field(default_factory=list)
    fingerprint: Optional[str] = None
    probableCauses: List[ProbableCause] = Field(default_factory=list)
    observedFacts: List[str] = Field(default_factory=list)
    aiInferences: List[str] = Field(default_factory=list)
    diagnosticChecks: List[DiagnosticCheck] = Field(default_factory=list)
    recommendedRunbookIds: List[str] = Field(default_factory=list)
    overallUncertainty: Optional[str] = None
    insufficientEvidence: bool = False
    ticketId: Optional[str] = None
    escalationReason: Optional[str] = None
    isRepeated: bool = False
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class IncidentFilterParams(BaseModel):
    status: Optional[IncidentStatus] = None
    severity: Optional[LogSeverity] = None
    service: Optional[str] = None
    source: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 50
