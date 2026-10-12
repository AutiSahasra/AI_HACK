from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class UploadStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"

class LineError(BaseModel):
    line: int
    raw: str
    error: str

class UploadRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id")
    fileName: str
    fileSize: int
    contentType: str
    detectedFormat: str
    status: UploadStatus = UploadStatus.PENDING
    parsedCount: int = 0
    failedCount: int = 0
    errors: List[LineError] = Field(default_factory=list)
    uploadedBy: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completedAt: Optional[datetime] = None

class UploadResponse(BaseModel):
    id: str
    fileName: str
    fileSize: int
    detectedFormat: str
    status: UploadStatus
    parsedCount: int
    failedCount: int
    errors: List[LineError]
    uploadedBy: str
    createdAt: datetime
    completedAt: Optional[datetime] = None
