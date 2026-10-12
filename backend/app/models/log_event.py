from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class LogSeverity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SourceType(str, Enum):
    MANUAL_UPLOAD = "manual_upload"
    LIVE = "live"

class LogSourceMeta(BaseModel):
    type: SourceType
    sourceId: str = "default"
    fileName: Optional[str] = None
    uploadId: Optional[str] = None

class ParseStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"

class LogEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: Optional[str] = Field(default=None, alias="_id")
    timestamp: datetime
    ingestedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service: str
    severity: LogSeverity
    message: str
    source: LogSourceMeta
    traceId: Optional[str] = None
    requestId: Optional[str] = None
    hostId: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    parseStatus: ParseStatus = ParseStatus.OK
    parseError: Optional[str] = None
    fingerprint: str
    redacted: bool = False

class LogEventCreate(BaseModel):
    timestamp: datetime
    service: str
    severity: LogSeverity
    message: str
    source: LogSourceMeta
    traceId: Optional[str] = None
    requestId: Optional[str] = None
    hostId: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    parseStatus: ParseStatus = ParseStatus.OK
    parseError: Optional[str] = None
    fingerprint: Optional[str] = None
    redacted: bool = False

class LogFilterParams(BaseModel):
    service: Optional[str] = None
    severity: Optional[LogSeverity] = None
    source_type: Optional[SourceType] = None
    source_id: Optional[str] = None
    upload_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    search: Optional[str] = None
    fingerprint: Optional[str] = None
    page: int = 1
    page_size: int = 50
