import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.models.schema_spec import (
    IncidentDoc,
    LogEventDoc,
    KnowledgeArticleDoc,
    AnalysisRunDoc,
    ModelRegistryDoc,
    ServiceMeta,
    RootCauseMeta,
    IncidentMetrics,
    ResolutionMeta,
    EnvironmentEnum,
    SeverityEnum,
    IncidentStatusEnum,
    CategoryLabelEnum,
    ConfirmationStatusEnum,
    LogLevelEnum,
    ModelTypeEnum,
)


def test_incident_doc_valid_creation():
    doc = IncidentDoc(
        incident_key="INC-000001",
        title="DB connection pool timeout",
        description="Checkout service queries timing out",
        service=ServiceMeta(name="payments-api", environment=EnvironmentEnum.synthetic),
        severity=SeverityEnum.critical,
        status=IncidentStatusEnum.open,
        category_label=CategoryLabelEnum.database,
        root_cause=RootCauseMeta(
            label="db_pool_timeout",
            explanation="Pool saturated due to slow query",
            confirmation_status=ConfirmationStatusEnum.synthetic_ground_truth,
        ),
        metrics=IncidentMetrics(
            cpu_usage_pct=45.2,
            memory_usage_pct=60.1,
            error_count_1m=25,
            db_timeout_count_1m=18,
            response_time_ms=3200.0,
            network_error_count_1m=0,
            connection_pool_usage_pct=96.5,
        ),
        symptoms=["Queries timing out", "Pool at capacity"],
        resolution=ResolutionMeta(summary=None, verified=False),
        is_synthetic=True,
    )
    assert doc.incident_key == "INC-000001"
    assert doc.metrics.connection_pool_usage_pct == 96.5
    assert doc.is_synthetic is True


def test_metric_validation_ranges():
    # cpu_usage_pct > 100 must fail
    with pytest.raises(ValidationError):
        IncidentMetrics(cpu_usage_pct=105.0)

    # cpu_usage_pct < 0 must fail
    with pytest.raises(ValidationError):
        IncidentMetrics(cpu_usage_pct=-5.0)

    # negative count must fail
    with pytest.raises(ValidationError):
        IncidentMetrics(error_count_1m=-1)

    # Missing metrics must be preserved as None, not silently 0
    m = IncidentMetrics(cpu_usage_pct=50.0, db_timeout_count_1m=None)
    assert m.db_timeout_count_1m is None
    assert m.cpu_usage_pct == 50.0


def test_log_event_embedding_dimension():
    # Correct 384 dimension passes
    valid_emb = [0.1] * 384
    log_doc = LogEventDoc(
        event_id="evt_001",
        service_name="auth-service",
        environment=EnvironmentEnum.synthetic,
        level=LogLevelEnum.ERROR,
        message="Token expired",
        fingerprint="fp123",
        embedding=valid_emb,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    )
    assert len(log_doc.embedding) == 384

    # Invalid dimension (e.g. 128 instead of 384) must fail
    invalid_emb = [0.1] * 128
    with pytest.raises(ValidationError):
        LogEventDoc(
            event_id="evt_002",
            service_name="auth-service",
            environment=EnvironmentEnum.synthetic,
            level=LogLevelEnum.ERROR,
            message="Token expired",
            fingerprint="fp123",
            embedding=invalid_emb,
        )


def test_knowledge_article_validation():
    # 384 dimension vector required
    emb = [0.0] * 384
    emb[0] = 1.0
    article = KnowledgeArticleDoc(
        article_id="KB-001",
        title="Database Runbook",
        content="Steps to recover database pool.",
        category=CategoryLabelEnum.database,
        service_names=["payments-api"],
        resolution_steps=["Restart pooler"],
        embedding=emb,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        content_version=1,
    )
    assert article.article_id == "KB-001"
    assert len(article.embedding) == 384


def test_model_registry_doc_validation():
    reg = ModelRegistryDoc(
        model_name="xgboost-category-classifier",
        model_type=ModelTypeEnum.classifier,
        version="1.0.0",
        source_model_id="xgboost_category_model.json",
        feature_names=["cpu_usage_pct", "memory_usage_pct"],
        label_names=["database", "network"],
        metrics={"macro_f1": 0.92},
        training_data_version="synth-seed-42",
        is_active=True,
    )
    assert reg.model_name == "xgboost-category-classifier"
    assert reg.metrics["macro_f1"] == 0.92
