import pytest
import uuid
from datetime import datetime, timezone
from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data
from app.core.config import settings
from app.models.rca import RCAResult
from app.models.incident import IncidentStatus
from app.services.llm.mock_provider import MockProvider
from app.services.retrieval import retriever_service
from app.services.rca import rca_service
from app.repositories.incident_repo import incident_repo
from app.repositories.log_event_repo import log_event_repo

@pytest.fixture(autouse=True)
async def setup_test_environment():
    settings.USE_IN_MEMORY_DB = True
    await DatabaseManager.connect()
    await seed_all_data()
    yield
    await DatabaseManager.disconnect()

@pytest.mark.asyncio
async def test_mock_llm_provider_schema_conformance():
    provider = MockProvider()
    messages = [
        {"role": "user", "content": "Service order-service emitted: Connection to database replica timed out after 5000ms"}
    ]
    result = await provider.generate(messages, RCAResult)
    assert isinstance(result, RCAResult)
    assert len(result.probableCauses) >= 1
    assert result.probableCauses[0].confidence > 0.8
    assert "Database connection pool" in result.probableCauses[0].description
    assert len(result.observedFacts) >= 1
    assert len(result.aiInferences) >= 1
    assert len(result.diagnosticChecks) >= 1

@pytest.mark.asyncio
async def test_retrieval_historical_and_runbooks():
    # Test runbooks retrieval
    runbooks = await retriever_service.retrieve_runbooks(service="order-service", query="database connection timeout", top_k=2)
    assert len(runbooks) >= 1
    assert any("Database" in rb["title"] for rb in runbooks)

    # Test historical incidents retrieval
    history = await retriever_service.retrieve_historical_incidents(service="order-service", query="pool exhaustion", top_k=2)
    assert len(history) >= 1
    assert any("PostgreSQL connection pool" in h["title"] for h in history)

@pytest.mark.asyncio
async def test_rca_pipeline_execution_and_anti_hallucination():
    # Create incident with real events
    inc_id = str(uuid.uuid4())
    ev1_id = str(uuid.uuid4())
    ev1 = {
        "_id": ev1_id,
        "service": "order-service",
        "severity": "CRITICAL",
        "message": "Connection to database replica timed out after 5000ms for worker thread 4",
        "fingerprint": "fp-rca-test",
        "timestamp": datetime.now(timezone.utc),
        "source": {"type": "manual_upload", "sourceId": "up-rca"}
    }
    await log_event_repo.insert_one(ev1)

    inc_doc = {
        "_id": inc_id,
        "title": "order-service: Database Timeout",
        "severity": "CRITICAL",
        "service": "order-service",
        "status": IncidentStatus.NEW.value,
        "sources": ["manual_upload"],
        "eventRefs": [ev1_id],
        "eventCount": 1,
        "firstSeen": datetime.now(timezone.utc),
        "lastSeen": datetime.now(timezone.utc),
        "matchedRules": ["Database Connection Timeout Spike"],
        "fingerprint": "fp-rca-test",
        "probableCauses": [],
        "observedFacts": [],
        "aiInferences": [],
        "diagnosticChecks": [],
        "recommendedRunbookIds": [],
        "overallUncertainty": None,
        "insufficientEvidence": False,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    await incident_repo.create(inc_doc)

    # Run RCA analysis
    rca_res = await rca_service.analyze_incident(inc_id)
    assert rca_res is not None

    # Verify incident state was updated
    updated_inc = await incident_repo.get_by_id(inc_id)
    assert updated_inc["status"] in (IncidentStatus.ANALYZED.value, IncidentStatus.ESCALATED.value)
    assert len(updated_inc["probableCauses"]) >= 1
    
    # Verify cause is unverified by default
    assert updated_inc["probableCauses"][0]["verified"] is False

    # Verify supporting evidence is grounded in actual log messages
    evidence_list = updated_inc["probableCauses"][0]["supportingEvidence"]
    assert len(evidence_list) >= 1
    # Check that excerpt is present in ev1 message
    for ev_item in evidence_list:
        excerpt = ev_item["excerpt"]
        snippet = excerpt[:30] if len(excerpt) > 30 else excerpt
        assert snippet.lower() in ev1["message"].lower()

@pytest.mark.asyncio
async def test_rca_pipeline_graceful_fallback_on_failure(monkeypatch):
    # Simulate an error in LLM provider
    async def mock_fail_generate(*args, **kwargs):
        raise RuntimeError("Remote LLM connection timeout")

    from app.services.llm.mock_provider import MockProvider
    monkeypatch.setattr(MockProvider, "generate", mock_fail_generate)

    inc_id = str(uuid.uuid4())
    inc_doc = {
        "_id": inc_id,
        "title": "Failure test incident",
        "severity": "ERROR",
        "service": "payment-service",
        "status": IncidentStatus.NEW.value,
        "eventRefs": [],
        "eventCount": 1,
        "firstSeen": datetime.now(timezone.utc),
        "lastSeen": datetime.now(timezone.utc),
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    await incident_repo.create(inc_doc)

    res = await rca_service.analyze_incident(inc_id)
    assert res is None

    # Must transition to failed_analysis and record escalation reason, never silently dropped
    inc = await incident_repo.get_by_id(inc_id)
    assert inc["status"] == IncidentStatus.FAILED_ANALYSIS.value
    assert "Analysis unavailable" in inc["escalationReason"]
