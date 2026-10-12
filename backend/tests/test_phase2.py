import pytest
import io
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data
from app.core.config import settings
from app.services.detection import detection_service
from app.services.grouping import grouping_service
from app.repositories.incident_repo import incident_repo
from app.repositories.log_event_repo import log_event_repo
from app.models.incident import IncidentStatus

@pytest.fixture(autouse=True)
async def setup_test_environment():
    settings.USE_IN_MEMORY_DB = True
    await DatabaseManager.connect()
    await seed_all_data()
    yield
    await DatabaseManager.disconnect()

@pytest.mark.asyncio
async def test_pattern_detection_rule_matching():
    events = [
        {
            "_id": str(uuid.uuid4()),
            "service": "order-service",
            "severity": "ERROR",
            "message": "Connection to database replica timed out after 5000ms",
            "fingerprint": "fp-db-timeout",
            "timestamp": datetime.now(timezone.utc),
            "source": {"type": "manual_upload", "sourceId": "up-1"}
        },
        {
            "_id": str(uuid.uuid4()),
            "service": "order-service",
            "severity": "CRITICAL",
            "message": "database connection pool exhausted",
            "fingerprint": "fp-db-timeout",
            "timestamp": datetime.now(timezone.utc),
            "source": {"type": "manual_upload", "sourceId": "up-1"}
        },
        {
            "_id": str(uuid.uuid4()),
            "service": "order-service",
            "severity": "ERROR",
            "message": "postgres timeout connecting to master node",
            "fingerprint": "fp-db-timeout",
            "timestamp": datetime.now(timezone.utc),
            "source": {"type": "manual_upload", "sourceId": "up-1"}
        }
    ]
    matches = await detection_service.evaluate_events(events)
    assert len(matches) >= 1
    matched_rule_names = [m.rule_name for m in matches]
    assert any("Database Connection Timeout" in name for name in matched_rule_names)

@pytest.mark.asyncio
async def test_grouping_and_deduplication():
    # Insert two events with identical fingerprint
    fp = "shared-fp-test-01"
    ev1 = {
        "_id": str(uuid.uuid4()),
        "service": "inventory-service",
        "severity": "ERROR",
        "message": "ConfigError: missing required env DB_HOST",
        "fingerprint": fp,
        "timestamp": datetime.now(timezone.utc),
        "source": {"type": "manual_upload", "sourceId": "up-2"}
    }
    ev2 = {
        "_id": str(uuid.uuid4()),
        "service": "inventory-service",
        "severity": "ERROR",
        "message": "ConfigError: missing required env DB_HOST",
        "fingerprint": fp,
        "timestamp": datetime.now(timezone.utc),
        "source": {"type": "manual_upload", "sourceId": "up-2"}
    }
    await log_event_repo.insert_many([ev1, ev2])

    matches1 = await detection_service.evaluate_events([ev1])
    created_ids = await grouping_service.correlate_and_group(matches1)
    assert len(created_ids) == 1
    incident_id = created_ids[0]

    # Verify incident created
    inc = await incident_repo.get_by_id(incident_id)
    assert inc is not None
    assert inc["eventCount"] == 1
    assert inc["status"] == IncidentStatus.NEW.value

    # Second event should deduplicate into existing open incident
    matches2 = await detection_service.evaluate_events([ev2])
    dedup_ids = await grouping_service.correlate_and_group(matches2)
    assert len(dedup_ids) == 1
    assert dedup_ids[0] == incident_id

    # Verify count incremented
    inc_after = await incident_repo.get_by_id(incident_id)
    assert inc_after["eventCount"] == 2
    assert len(inc_after["eventRefs"]) == 2

@pytest.mark.asyncio
async def test_reopen_recently_resolved_incident_as_repeated():
    fp = "fp-repeat-test-02"
    ev1 = {
        "_id": str(uuid.uuid4()),
        "service": "inventory-service",
        "severity": "ERROR",
        "message": "ConfigError: invalid configuration parameter",
        "fingerprint": fp,
        "timestamp": datetime.now(timezone.utc),
        "source": {"type": "manual_upload", "sourceId": "up-3"}
    }
    await log_event_repo.insert_many([ev1])

    matches = await detection_service.evaluate_events([ev1])
    created_ids = await grouping_service.correlate_and_group(matches)
    incident_id = created_ids[0]

    # Mark incident resolved
    await incident_repo.update(incident_id, {"status": "resolved"})
    inc_resolved = await incident_repo.get_by_id(incident_id)
    assert inc_resolved["status"] == "resolved"

    # Now receive repeat error within 15 minutes
    ev2 = {
        "_id": str(uuid.uuid4()),
        "service": "inventory-service",
        "severity": "ERROR",
        "message": "ConfigError: invalid configuration parameter",
        "fingerprint": fp,
        "timestamp": datetime.now(timezone.utc),
        "source": {"type": "manual_upload", "sourceId": "up-3"}
    }
    await log_event_repo.insert_many([ev2])
    matches_repeat = await detection_service.evaluate_events([ev2])
    reopened_ids = await grouping_service.correlate_and_group(matches_repeat)
    assert incident_id in reopened_ids

    # Should be reopened as escalated with isRepeated = True
    inc_reopened = await incident_repo.get_by_id(incident_id)
    assert inc_reopened["status"] == IncidentStatus.ESCALATED.value
    assert inc_reopened["isRepeated"] is True
    assert "Repeated incident" in inc_reopened["escalationReason"]

@pytest.mark.asyncio
async def test_incidents_api_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login_resp = await client.post("/api/auth/login", json={
            "username": "support",
            "password": "supportpassword123"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload a log with bad config error to trigger automatic incident creation
        csv_bytes = (
            b"timestamp,severity,service,message\n"
            b"2026-10-13T10:00:00Z,ERROR,inventory-service,invalid configuration detected in yaml\n"
        )
        files = {"file": ("config_test.csv", io.BytesIO(csv_bytes), "text/csv")}
        await client.post("/api/uploads", files=files, headers=headers)

        # Query incidents endpoint
        inc_resp = await client.get("/api/incidents?service=inventory-service", headers=headers)
        assert inc_resp.status_code == 200
        inc_list = inc_resp.json()
        assert len(inc_list) >= 1
        first_inc = inc_list[0]
        inc_id = first_inc.get("id") or first_inc.get("_id")
        assert inc_id is not None

        # Detail endpoint
        detail_resp = await client.get(f"/api/incidents/{inc_id}", headers=headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["service"] == "inventory-service"

        # Events endpoint
        events_resp = await client.get(f"/api/incidents/{inc_id}/events", headers=headers)
        assert events_resp.status_code == 200
        events_data = events_resp.json()
        assert len(events_data) >= 1

        # Submit operator feedback
        fb_resp = await client.post(
            f"/api/incidents/{inc_id}/feedback",
            json={"useful": True, "notes": "Accurate detection"},
            headers=headers
        )
        assert fb_resp.status_code == 200
        assert fb_resp.json()["success"] is True
