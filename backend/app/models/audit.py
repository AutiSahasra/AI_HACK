from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.models.user import UserRole

class AuditLog(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=False)
    id: str = Field(default="", alias="_id")
    action: str
    actor: str
    role: UserRole
    entityType: str
    entityId: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
