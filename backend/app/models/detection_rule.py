from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class RuleType(str, Enum):
    PATTERN = "pattern"
    THRESHOLD = "threshold"
    ANOMALY = "anomaly"

class DetectionRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id")
    name: str
    description: str
    ruleType: RuleType
    service: str = "*"
    pattern: str = ""
    severity: str = "ERROR"
    threshold: int = 3
    windowMinutes: int = 5
    enabled: bool = True
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DetectionRuleCreate(BaseModel):
    name: str
    description: str
    ruleType: RuleType
    service: str = "*"
    pattern: str = ""
    severity: str = "ERROR"
    threshold: int = 3
    windowMinutes: int = 5
    enabled: bool = True
