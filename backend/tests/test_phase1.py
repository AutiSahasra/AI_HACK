import pytest
import io
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.redaction import redaction_service
from app.services.fingerprint import fingerprint_service
from app.services.normalization import normalization_service
from app.services.parsing import parsing_service
from app.models.log_event import LogSeverity
from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data
from app.core.config import settings

@pytest.fixture(autouse=True)
async def setup_test_environment():
    settings.USE_IN_MEMORY_DB = True
    await DatabaseManager.connect()
    await seed_all_data()
    yield
    await DatabaseManager.disconnect()

# Unit Tests for Redaction
def test_redaction_secrets_and_tokens():
    text = "User auth with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123456789 and password=SuperSecret123!"
    redacted, was_redacted = redaction_service.redact(text)
    assert was_redacted is True
    assert "Bearer [REDACTED_TOKEN]" in redacted
    assert "password=[REDACTED_SECRET]" in redacted
    assert "SuperSecret123!" not in redacted

def test_redaction_emails_and_cards():
    text = "Customer email john.doe@example.com paid with card 4111-2222-3333-4444"
    redacted, was_redacted = redaction_service.redact(text)
    assert was_redacted is True
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_CARD]" in redacted
    assert "john.doe@example.com" not in redacted

# Unit Tests for Fingerprinting
def test_fingerprinting_generates_stable_hash():
    msg1 = "Connection pool exhausted for worker 0x7fa8901 after 5000ms uuid 123e4567-e89b-12d3-a456-426614174000"
    msg2 = "Connection pool exhausted for worker 0x7fa8902 after 10000ms uuid 987e6543-e21b-12d3-a456-426614174999"
    fp1 = fingerprint_service.generate(msg1)
    fp2 = fingerprint_service.generate(msg2)
    assert fp1 == fp2  # Should produce identical fingerprint because variables are collapsed

# Unit Tests for Normalization
def test_severity_normalization():
    assert normalization_service.normalize_severity("err") == LogSeverity.ERROR
    assert normalization_service.normalize_severity("WARNING") == LogSeverity.WARN
    assert normalization_service.normalize_severity("critical") == LogSeverity.CRITICAL
    assert normalization_service.normalize_severity("unknown") == LogSeverity.INFO

# Unit Tests for Parsers
def test_parse_csv_with_headers():
    csv_data = (
        "timestamp,severity,service,message,trace_id\n"
        "2026-10-13T10:00:00Z,ERROR,order-service,Database timeout,tr-100\n"
        "2026-10-13T10:01:00Z,WARN,payment-service,High memory,tr-101\n"
    )
    events, errors = parsing_service.parse_content(csv_data, "csv")
    assert len(errors) == 0
    assert len(events) == 2
    assert events[0]["service"] == "order-service"
    assert events[0]["severity"] == LogSeverity.ERROR
    assert events[0]["traceId"] == "tr-100"

def test_parse_jsonl_with_malformed_line():
    jsonl_data = (
        '{"timestamp": "2026-10-13T10:00:00Z", "level": "ERROR", "service": "auth-service", "message": "Failed login"}\n'
        'invalid non json string here\n'
        '{"timestamp": "2026-10-13T10:01:00Z", "level": "INFO", "service": "auth-service", "message": "User logout"}\n'
    )
    events, errors = parsing_service.parse_content(jsonl_data, "jsonl")
    assert len(events) == 2
    assert len(errors) == 1
    assert errors[0].line == 2

def test_parse_plain_text_with_multiline_stacktrace():
    raw_logs = (
        "2026-10-13 12:00:00 [ERROR] [order-service] Failed to process checkout\n"
        "Traceback (most recent call last):\n"
        "  File 'order.py', line 45, in checkout\n"
        "    db.connect()\n"
        "ConnectionRefusedError: Connection refused\n"
        "2026-10-13 12:00:05 [INFO] [order-service] Retrying checkout\n"
    )
    events, errors = parsing_service.parse_content(raw_logs, "text")
    assert len(events) == 2
    assert "Traceback" in events[0]["message"]
    assert "ConnectionRefusedError" in events[0]["message"]
    assert events[0]["severity"] == LogSeverity.ERROR
    assert events[1]["severity"] == LogSeverity.INFO

# Integration Tests for FastAPI Endpoints
@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_auth_login_and_me():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login with seeded admin user
        login_resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "adminpassword123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token_data = login_resp.json()
        assert "access_token" in token_data
        token = token_data["access_token"]
        assert token_data["user"]["role"] == "admin"

        # Call /me with token
        me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "admin"

@pytest.mark.asyncio
async def test_upload_and_log_explorer():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login to get token
        login_resp = await client.post("/api/auth/login", json={
            "username": "support",
            "password": "supportpassword123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload a CSV file
        csv_bytes = (
            b"timestamp,severity,service,message\n"
            b"2026-10-13T10:00:00Z,ERROR,checkout-svc,Payment gateway timeout password=secret123\n"
        )
        files = {"file": ("test_logs.csv", io.BytesIO(csv_bytes), "text/csv")}
        upload_resp = await client.post("/api/uploads", files=files, headers=headers)
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        upload_data = upload_resp.json()
        assert upload_data["status"] == "completed"
        assert upload_data["parsedCount"] == 1

        # Query log explorer
        logs_resp = await client.get("/api/logs?service=checkout-svc", headers=headers)
        assert logs_resp.status_code == 200
        logs_data = logs_resp.json()
        assert logs_data["total"] >= 1
        first_event = logs_data["items"][0]
        # Verify secret was redacted during ingestion
        assert "password=[REDACTED_SECRET]" in first_event["message"]
        assert "secret123" not in first_event["message"]
        assert first_event["redacted"] is True
