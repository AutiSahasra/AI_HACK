from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class EnvironmentEnum(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"
    synthetic = "synthetic"


class SeverityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatusEnum(str, Enum):
    open = "open"
    investigating = "investigating"
    mitigated = "mitigated"
    resolved = "resolved"
    closed = "closed"


class CategoryLabelEnum(str, Enum):
    database = "database"
    network = "network"
    compute = "compute"
    memory = "memory"
    authentication = "authentication"
    dependency = "dependency"
    unknown = "unknown"


class ConfirmationStatusEnum(str, Enum):
    unconfirmed = "unconfirmed"
    suspected = "suspected"
    confirmed = "confirmed"
    synthetic_ground_truth = "synthetic_ground_truth"


class LogLevelEnum(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SourceEnum(str, Enum):
    synthetic = "synthetic"
    application = "application"
    monitoring = "monitoring"
    manual = "manual"


class LabelSourceEnum(str, Enum):
    synthetic_rule = "synthetic_rule"
    human_verified = "human_verified"
    imported_verified = "imported_verified"
    unknown = "unknown"


class ModelTypeEnum(str, Enum):
    embedding = "embedding"
    classifier = "classifier"


# Sub-models
class ServiceMeta(BaseModel):
    name: str = Field(..., description="e.g. payments-api, auth-service, inventory-service")
    environment: EnvironmentEnum = Field(..., description="Target service environment")


class RootCauseMeta(BaseModel):
    label: Optional[str] = Field(None, description="Verified or synthetic cause label")
    explanation: Optional[str] = Field(None, description="Narrative explanation of cause")
    confirmation_status: ConfirmationStatusEnum = Field(
        default=ConfirmationStatusEnum.unconfirmed,
        description="unconfirmed, suspected, confirmed, synthetic_ground_truth"
    )


class IncidentMetrics(BaseModel):
    cpu_usage_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="0-100 percentage")
    memory_usage_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="0-100 percentage")
    error_count_1m: Optional[int] = Field(None, ge=0, description="Non-negative count in prior 1 minute")
    db_timeout_count_1m: Optional[int] = Field(None, ge=0, description="Non-negative count in prior 1 minute")
    response_time_ms: Optional[float] = Field(None, ge=0.0, description="Non-negative latency milliseconds")
    network_error_count_1m: Optional[int] = Field(None, ge=0, description="Non-negative count in prior 1 minute")
    connection_pool_usage_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="0-100 percentage or null")


class ResolutionAction(BaseModel):
    action: str
    outcome: str
    performed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = False


class ResolutionMeta(BaseModel):
    summary: Optional[str] = Field(None, description="Summary of action that fixed/mitigated issue")
    actions: List[ResolutionAction] = Field(default_factory=list, description="Audit actions performed")
    verified: bool = Field(False, description="True only if a human or automated health check confirmed")


# 1. Collection: incidents
class IncidentDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    incident_key: str = Field(..., description="Human-readable unique ID, e.g. INC-000001; unique index")
    title: str = Field(..., description="Short incident summary")
    description: str = Field(..., description="Human-readable symptom/context; redact secrets")
    service: ServiceMeta
    severity: SeverityEnum
    status: IncidentStatusEnum
    category_label: Optional[CategoryLabelEnum] = Field(None, description="Target label for XGBoost")
    root_cause: RootCauseMeta
    metrics: IncidentMetrics
    symptoms: List[str] = Field(..., description="Observed symptoms, not model conclusions")
    resolution: ResolutionMeta
    source: SourceEnum = SourceEnum.synthetic
    is_synthetic: bool = True
    label_source: LabelSourceEnum = LabelSourceEnum.synthetic_rule
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None


# 2. Collection: log_events
class LogEventDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    event_id: str = Field(..., description="Unique event identifier from collector")
    incident_id: Optional[str] = Field(None, description="Reference to incidents._id once grouped")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC event time")
    service_name: str
    environment: EnvironmentEnum
    level: LogLevelEnum
    message: str
    error_type: Optional[str] = None
    request_id: Optional[str] = None
    metrics_snapshot: Optional[Dict[str, Any]] = None
    fingerprint: str = Field(..., description="Stable hash of normalized error/service to group duplicates")
    embedding: Optional[List[float]] = Field(None, description="384 floats if generated")
    embedding_model: Optional[str] = Field(None, description="e.g. sentence-transformers/all-MiniLM-L6-v2")
    is_synthetic: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dim(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None and len(v) != 384:
            raise ValueError(f"MiniLM embeddings must be exactly 384 dimensions; received {len(v)}")
        return v


# 3. Collection: knowledge_articles
class KnowledgeArticleDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    article_id: str = Field(..., description="Unique stable ID")
    title: str = Field(..., description="Article or runbook title")
    content: str = Field(..., description="Retrieval text; chunk long documents for better matching")
    category: CategoryLabelEnum = Field(..., description="database, network, compute, memory, authentication, etc.")
    service_names: List[str] = Field(default_factory=list, description="Services where this guidance applies")
    resolution_steps: List[str] = Field(default_factory=list, description="Reviewed troubleshooting steps")
    embedding: List[float] = Field(..., description="384-dimensional MiniLM vector for retrieval")
    embedding_model: str = Field(..., description="Model identifier and revision")
    content_version: int = Field(1, description="Increment when text changes; regenerate embedding")
    verified: bool = Field(True, description="Whether a human reviewed the guidance")
    source: str = Field("synthetic", description="synthetic, internal_runbook, manually_authored")
    is_synthetic: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dim(cls, v: List[float]) -> List[float]:
        if len(v) != 384:
            raise ValueError(f"Knowledge article MiniLM vector must have exactly 384 dimensions; received {len(v)}")
        return v


# 4. Collection: analysis_runs
class XGBoostPredictionMeta(BaseModel):
    model_version: str
    predicted_category: str
    class_probabilities: Dict[str, float] = Field(default_factory=dict)
    feature_schema_version: str


class MiniLMMatchesMeta(BaseModel):
    model_id: str
    top_matches: List[Dict[str, Any]] = Field(default_factory=list)


class AnalysisRunDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    incident_id: str = Field(..., description="Reference to incident being analyzed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_fingerprint: str = Field(..., description="Normalized input fingerprint; useful for cache correlation")
    xgboost: XGBoostPredictionMeta
    minilm: MiniLMMatchesMeta
    final_assessment: str = Field(..., description="Rule/template-based summary; avoid claiming certainty")
    actual_category: Optional[str] = Field(None, description="Fill after verification; used for evaluation")
    feedback: Optional[Dict[str, Any]] = Field(None, description="Helpful flag, reviewer note, resolution outcome")
    is_synthetic: bool = True


# 5. Collection: model_registry
class ModelRegistryDoc(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    model_name: str = Field(..., description="e.g. minilm-incident-embeddings or xgboost-category-classifier")
    model_type: ModelTypeEnum = Field(..., description="embedding or classifier")
    version: str = Field(..., description="Application-assigned model version")
    source_model_id: str = Field(..., description="Exact Hugging Face ID or XGBoost artifact name")
    feature_names: List[str] = Field(default_factory=list, description="Exact ordered XGBoost input columns; empty for MiniLM")
    label_names: List[str] = Field(default_factory=list, description="Known classifier labels")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Evaluation data: macro-F1, per-class precision/recall, test set size")
    training_data_version: str = Field(..., description="Dataset version / generation seed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(True, description="Whether inference currently uses this version")
