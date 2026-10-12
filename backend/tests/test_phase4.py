import pytest
import os
import json
import uuid
import tempfile
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data
from app.core.config import settings
from app.models.log_event import SourceType
from app.repositories.incident_repo import incident_repo

# Import demo-app
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "demo-app"))
from main import app as demo_app, state as demo_state

# Import collector
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "collector"))
from tailer import LogTailer

@pytest.fixture(autouse=True)
async def setup_test_environment():
    settings.USE_IN_MEMORY_DB = True
    await DatabaseManager.connect()
    await seed_all_data()
    yield
    await DatabaseManager.disconnect()

@pytest.mark.asyncio
async def test_demo_app_fault_injection_and_health():
    async with AsyncClient(transport=ASGITransport(app=demo_app), base_url="http://test-demo") as client:
        # 1. Initially healthy
        demo_state.current_fault = None
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        # 2. Inject fault
        fault_resp = await client.post("/faults/db_connection_timeout")
        assert fault_resp.status_code == 200
        assert fault_resp.json()["status"] == "fault_injected"

        # 3. Health reflects fault state (503)
        unhealthy_resp = await client.get("/health")
        assert unhealthy_resp.status_code == 503
        assert unhealthy_resp.json()["status"] == "unhealthy"

        # 4. Admin remediation clears fault and restores health
        restart_resp = await client.post("/admin/restart")
        assert restart_resp.status_code == 200
        assert restart_resp.json()["recovered"] is True

        # 5. Health is restored to 200
        recovered_resp = await client.get("/health")
        assert recovered_resp.status_code == 200
        assert recovered_resp.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_collector_tailer_offset_tracking():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "test.log")
        offset_path = os.path.join(tmpdir, "offset.json")

        tailer = LogTailer(log_path=log_path, offset_path=offset_path)

        # Write first line
        with open(log_path, "w") as f:
            f.write('{"service": "demo-app", "severity": "INFO", "message": "Line 1"}\n')

        lines = tailer.read_new_lines()
        assert len(lines) == 1
        assert "Line 1" in lines[0]
        assert tailer.offset > 0

        # Read again with no new content -> should return 0 lines (offset preserved)
        lines_empty = tailer.read_new_lines()
        assert len(lines_empty) == 0

        # Append second line
        with open(log_path, "a") as f:
            f.write('{"service": "demo-app", "severity": "ERROR", "message": "Line 2"}\n')

        lines_new = tailer.read_new_lines()
        assert len(lines_new) == 1
        assert "Line 2" in lines_new[0]

@pytest.mark.asyncio
async def test_backend_live_ingest_pipeline_and_detection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Missing API key rejected
        no_key_resp = await client.post("/api/ingest", json={"sourceId": "live-1", "events": []})
        assert no_key_resp.status_code == 401

        # 2. Valid API key ingests batch
        headers = {"X-API-Key": "collector-secret-api-key-live-demo-2026"}
        live_events = [
            {
                "service": "order-service",
                "severity": "ERROR",
                "message": "Connection to database replica timed out after 5000ms password=secret_token_123",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "service": "order-service",
                "severity": "CRITICAL",
                "message": "database connection pool exhausted. Active: 20/20",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "service": "order-service",
                "severity": "ERROR",
                "message": "postgres timeout connecting to master node",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]

        ingest_resp = await client.post(
            "/api/ingest",
            json={"sourceId": "live-demo-collector", "events": live_events},
            headers=headers
        )
        assert ingest_resp.status_code == 200
        assert ingest_resp.json()["ingested"] == 3

        # 3. Verify incident was auto-created from live events
        incidents, total = await incident_repo.list_incidents(
            type("FilterParams", (), {
                "status": None, "severity": None, "service": "order-service", "source": None,
                "start_time": None, "end_time": None, "page": 1, "page_size": 10
            })()
        )
        assert len(incidents) >= 1
        live_inc = incidents[0]
        assert "live" in live_inc["sources"]
        assert live_inc["service"] == "order-service"
