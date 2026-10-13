import pytest
from app.services.synthetic_generator import generate_synthetic_dataset
from app.core.database import DatabaseManager, InMemoryCollection
from pymongo.errors import DuplicateKeyError


def test_deterministic_generation():
    # Same seed must generate identical records
    inc1, logs1, ka1 = generate_synthetic_dataset(count=50, seed=42)
    inc2, logs2, ka2 = generate_synthetic_dataset(count=50, seed=42)

    assert len(inc1) == 50
    assert len(inc2) == 50
    assert inc1[0]["incident_key"] == inc2[0]["incident_key"]
    assert inc1[0]["metrics"] == inc2[0]["metrics"]
    assert inc1[0]["title"] == inc2[0]["title"]
    assert len(logs1) == len(logs2)

    # Different seed should generate different samples
    inc3, _, _ = generate_synthetic_dataset(count=50, seed=99)
    assert inc1[0]["metrics"] != inc3[0]["metrics"] or inc1[0]["title"] != inc3[0]["title"]


def test_referential_integrity_and_synthetic_flags():
    incidents, log_events, knowledge_articles = generate_synthetic_dataset(count=30, seed=42)
    inc_keys = {inc["incident_key"] for inc in incidents}

    # Verify synthetic flags on all items
    for inc in incidents:
        assert inc["is_synthetic"] is True
        assert inc["label_source"] == "synthetic_rule"

    for log in log_events:
        assert log["is_synthetic"] is True
        # Every log event must reference a valid incident
        assert log["incident_id"] in inc_keys
        # Check embedding present and 384 dimensional
        assert len(log["embedding"]) == 384


@pytest.mark.asyncio
async def test_unique_index_constraint_enforcement():
    col = InMemoryCollection("test_incidents")
    await col.create_index([("incident_key", 1)], unique=True, name="idx_key_unique")

    await col.insert_one({"incident_key": "INC-000001", "title": "Test 1"})

    # Duplicate incident_key must raise DuplicateKeyError
    with pytest.raises(DuplicateKeyError):
        await col.insert_one({"incident_key": "INC-000001", "title": "Duplicate"})
