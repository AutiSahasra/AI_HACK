import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data
from app.core.config import settings
from app.models.ticket import TicketStatus, TicketPriority
from app.models.incident import IncidentStatus
from app.services.tickets import ticket_service
from app.services.policy import policy_service, PolicyViolationError
from app.services.health_checks import health_check_service
from app.services.audit import audit_service
from app.repositories.incident_repo import incident_repo

@pytest.fixture(autouse=True)
async def setup_test_environment():
    settings.USE_IN_MEMORY_DB = True
    await DatabaseManager.connect()
    await seed_all_data()
    yield
    await DatabaseManager.disconnect()

@pytest.mark.asyncio
async def test_ticket_lifecycle_and_transitions():
    inc_id = str(uuid.uuid4())
    # Create ticket
    ticket_id = await ticket_service.create_ticket_for_incident(inc_id, "Database Timeout Outage", "CRITICAL")
    assert ticket_id.startswith("TCK-")

    t = await ticket_service.get_ticket(ticket_id)
    assert t["priority"] == TicketPriority.P1.value
    assert t["status"] == TicketStatus.OPEN.value

    # Assign ticket
    updated = await ticket_service.assign_ticket(ticket_id, "sre-engineer-1", "support", "support_engineer")
    assert updated["assignee"] == "sre-engineer-1"

    # Valid status transition: open -> in_progress
    updated = await ticket_service.update_status(ticket_id, TicketStatus.IN_PROGRESS, "support", "support_engineer")
    assert updated["status"] == TicketStatus.IN_PROGRESS.value

    # Invalid status transition: in_progress -> closed (cannot skip resolution)
    with pytest.raises(ValueError):
        await ticket_service.update_status(ticket_id, TicketStatus.CLOSED, "support", "support_engineer")

    # Add comment
    with_comment = await ticket_service.add_comment(ticket_id, "support", "support_engineer", "Investigating query locks")
    assert len(with_comment["comments"]) == 1
    assert with_comment["comments"][0]["text"] == "Investigating query locks"

@pytest.mark.asyncio
async def test_policy_rejection_of_unallowlisted_action():
    with pytest.raises(PolicyViolationError):
        await policy_service.validate_action_request("rm -rf / --no-preserve-root", "support_engineer")

    with pytest.raises(PolicyViolationError):
        await policy_service.validate_action_request("arbitrary_bash_script", "admin")

@pytest.mark.asyncio
async def test_policy_blocks_self_approval():
    # User tries to approve their own request
    approval_doc = {
        "_id": "appr-01",
        "actionName": "restart_demo_service",
        "status": "pending",
        "requestedBy": "approver",
        "requestedByRole": "approver"
    }
    with pytest.raises(PolicyViolationError) as exc_info:
        await policy_service.validate_approval_decision(
            approval_doc=approval_doc,
            approver_username="approver",
            approver_role="approver"
        )
    assert "Self-approval policy violation" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_remediation_api_approval_gated_flow_and_verification(monkeypatch):
    async def mock_exec(*args, **kwargs):
        return True, {"status": "ok", "message": "Demo app restarted"}
    monkeypatch.setattr("app.api.remediation.remediation_executor.execute_allow_listed_action", mock_exec)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login as support
        support_resp = await client.post("/api/auth/login", json={"username": "support", "password": "supportpassword123"})
        support_token = support_resp.json()["access_token"]
        support_headers = {"Authorization": f"Bearer {support_token}"}

        # Login as approver
        approver_resp = await client.post("/api/auth/login", json={"username": "approver", "password": "approverpassword123"})
        approver_token = approver_resp.json()["access_token"]
        approver_headers = {"Authorization": f"Bearer {approver_token}"}

        # Create an incident to remediate
        inc_id = str(uuid.uuid4())
        inc_doc = {
            "_id": inc_id,
            "title": "Database Connection Pool Timeout",
            "severity": "CRITICAL",
            "service": "order-service",
            "status": "awaiting_approval",
            "eventRefs": [],
            "eventCount": 1,
            "firstSeen": datetime.now(timezone.utc),
            "lastSeen": datetime.now(timezone.utc),
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        }
        await incident_repo.create(inc_doc)

        # 1. Support engineer requests protected action 'restart_demo_service'
        req_resp = await client.post(
            "/api/remediation/request",
            json={"incidentId": inc_id, "actionName": "restart_demo_service"},
            headers=support_headers
        )
        assert req_resp.status_code == 200
        approval_data = req_resp.json()
        approval_id = approval_data.get("id") or approval_data.get("_id")
        assert approval_id is not None
        assert approval_data["status"] == "pending"

        # 2. Direct API bypass attempts:
        # a) Support engineer tries to execute directly -> BLOCKED (HTTP 403, role not allowed)
        support_bypass = await client.post(f"/api/remediation/execute/{approval_id}", headers=support_headers)
        assert support_bypass.status_code == 403
        assert "not authorized" in support_bypass.text

        # b) Approver tries to execute BEFORE approval is granted -> BLOCKED (HTTP 403, status pending)
        approver_bypass = await client.post(f"/api/remediation/execute/{approval_id}", headers=approver_headers)
        assert approver_bypass.status_code == 403
        assert "Execution blocked" in approver_bypass.text

        # 3. Requester tries to self-approve -> MUST BE BLOCKED
        # If support tries to approve:
        support_approve_resp = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved"},
            headers=support_headers
        )
        assert support_approve_resp.status_code == 403

        # 4. Senior approver approves request
        approve_resp = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved"},
            headers=approver_headers
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # 5. Now execution is permitted
        exec_resp = await client.post(f"/api/remediation/execute/{approval_id}", headers=approver_headers)
        assert exec_resp.status_code == 200
        assert exec_resp.json()["status"] == "executing_recovery_verification"

@pytest.mark.asyncio
async def test_recovery_verification_success_and_failure(monkeypatch):
    import httpx

    inc_id = str(uuid.uuid4())
    inc_doc = {
        "_id": inc_id,
        "title": "Verification test incident",
        "severity": "CRITICAL",
        "service": "order-service",
        "status": "remediating",
        "eventRefs": [],
        "firstSeen": datetime.now(timezone.utc),
        "lastSeen": datetime.now(timezone.utc),
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    await incident_repo.create(inc_doc)

    # 1. Test verification success
    class MockHealthyResponse:
        status_code = 200
        def json(self):
            return {"status": "healthy", "active_fault": None}

    async def mock_healthy_get(*args, **kwargs):
        return MockHealthyResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_healthy_get)
    success = await health_check_service.verify_recovery(inc_id, max_retries=1, retry_delay_seconds=0.01)
    assert success is True

    inc_after_success = await incident_repo.get_by_id(inc_id)
    assert inc_after_success["status"] == "resolved"

    # 2. Test verification failure
    class MockUnhealthyResponse:
        status_code = 503
        def json(self):
            return {"status": "unhealthy", "active_fault": "db_connection_timeout"}

    async def mock_unhealthy_get(*args, **kwargs):
        return MockUnhealthyResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_unhealthy_get)
    failed = await health_check_service.verify_recovery(inc_id, max_retries=1, retry_delay_seconds=0.01)
    assert failed is False

    inc_after_failure = await incident_repo.get_by_id(inc_id)
    assert inc_after_failure["status"] == "escalated"
    assert "Recovery verification failed" in inc_after_failure["escalationReason"]

@pytest.mark.asyncio
async def test_audit_log_append_only():
    log_id = await audit_service.log_event(
        action="TEST_ACTION",
        actor="admin",
        role="admin",
        entity_type="system",
        entity_id="sys-1",
        details={"key": "value"}
    )
    assert log_id is not None

    logs = await audit_service.list_audit_logs(actor="admin", limit=10)
    assert len(logs) >= 1
    found = next((l for l in logs if l.get("action") == "TEST_ACTION"), None)
    assert found is not None
    assert found["details"]["key"] == "value"
