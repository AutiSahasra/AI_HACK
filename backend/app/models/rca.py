from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.incident import ProbableCause, DiagnosticCheck

class RCAResult(BaseModel):
    probableCauses: List[ProbableCause] = Field(default_factory=list)
    observedFacts: List[str] = Field(default_factory=list)
    aiInferences: List[str] = Field(default_factory=list)
    diagnosticChecks: List[DiagnosticCheck] = Field(default_factory=list)
    recommendedRunbookIds: List[str] = Field(default_factory=list)
    overallUncertainty: Optional[str] = None
    insufficientEvidence: bool = False
