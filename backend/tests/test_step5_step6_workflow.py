import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data
from app.core.config import settings
from app.repositories.incident_repo import incident_repo
from app.services.tickets import ticket_service
from app.services.health_checks import health_check_service

@pytest.fixture(autouse=True)
async def setup_test_env():
    settings.USE_IN_MEMORY_DB = True
    await DatabaseManager.connect()
    await seed_all_data()
    yield
    await DatabaseManager.disconnect()

async def get_user_headers(client: AsyncClient, username: str):
    resp = await client.post("/api/auth/login", json={"username": username, "password": f"{username}password123"})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_step5_rejection_workflow(monkeypatch):
    """
    Step 5 Rejection:
    - Support requests remediation action. Ticket -> pending_approval.
    - Approver rejects with mandatory explanation.
    - Incident reverts to analyzed, Ticket reverts to in_progress, with rejection comment.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        support_headers = await get_user_headers(client, "support")
        approver_headers = await get_user_headers(client, "approver")

        # 1. Create incident and linked ticket
        inc_id = str(uuid.uuid4())
        ticket_id = await ticket_service.create_ticket_for_incident(
            incident_id=inc_id,
            title="Database Connection Pool Exhausted",
            severity="CRITICAL"
        )
        now = datetime.now(timezone.utc)
        await incident_repo.create({
            "_id": inc_id,
            "title": "Database Connection Pool Exhausted",
            "severity": "CRITICAL",
            "service": "order-service",
            "status": "analyzed",
            "ticketId": ticket_id,
            "eventRefs": [],
            "eventCount": 1,
            "firstSeen": now,
            "lastSeen": now,
            "createdAt": now,
            "updatedAt": now
        })

        # 2. Supporter requests remediation action
        req_res = await client.post(
            "/api/remediation/request",
            json={
                "incidentId": inc_id,
                "actionName": "restart_demo_service",
                "justification": "Pool exhausted, need to recycle workers"
            },
            headers=support_headers
        )
        assert req_res.status_code == 200
        approval_id = req_res.json()["id"]

        # Verify incident and ticket moved to awaiting_approval / pending_approval
        inc_doc = await incident_repo.get_by_id(inc_id)
        assert inc_doc["status"] == "awaiting_approval"

        t_doc = await ticket_service.get_ticket(ticket_id)
        assert t_doc["status"] == "pending_approval"
        assert any("Routed to Senior Approver" in c["text"] for c in t_doc["comments"])

        # 3. Approver rejects WITHOUT reason -> should fail with 400
        rej_fail = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "rejected", "reason": ""},
            headers=approver_headers
        )
        assert rej_fail.status_code == 400

        # 4. Approver rejects WITH explanation
        rej_res = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "rejected", "reason": "Target service has active long-running billing transactions; schedule failover instead."},
            headers=approver_headers
        )
        assert rej_res.status_code == 200
        assert rej_res.json()["status"] == "rejected"
        assert rej_res.json()["rejectionReason"] == "Target service has active long-running billing transactions; schedule failover instead."

        # Verify incident reverted to analyzed
        inc_doc_after = await incident_repo.get_by_id(inc_id)
        assert inc_doc_after["status"] == "analyzed"
        assert "billing transactions" in inc_doc_after["rejectionReason"]

        # Verify ticket reverted to in_progress with detailed comment for supporter
        t_doc_after = await ticket_service.get_ticket(ticket_id)
        assert t_doc_after["status"] == "in_progress"
        last_comment = t_doc_after["comments"][-1]
        assert "REJECTED by Senior Approver @approver" in last_comment["text"]
        assert "billing transactions" in last_comment["text"]


@pytest.mark.asyncio
async def test_step5_approval_and_step6_recovery_verification_success(monkeypatch):
    """
    Step 5 Approval & Step 6 Verification:
    - Support requests remediation action. Ticket -> pending_approval.
    - Approver approves request. Ticket gets notification comment.
    - Approver executes action.
    - Automated recovery verification passes -> Incident -> resolved, Ticket -> resolved.
    """
    # Mock allow-listed action execution
    async def mock_exec(*args, **kwargs):
        return True, {"status": "ok", "restarted": True}
    monkeypatch.setattr("app.api.remediation.remediation_executor.execute_allow_listed_action", mock_exec)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        support_headers = await get_user_headers(client, "support")
        approver_headers = await get_user_headers(client, "approver")

        # Create incident and ticket
        inc_id = str(uuid.uuid4())
        ticket_id = await ticket_service.create_ticket_for_incident(
            incident_id=inc_id,
            title="Database Connection Timeout",
            severity="CRITICAL"
        )
        now = datetime.now(timezone.utc)
        await incident_repo.create({
            "_id": inc_id,
            "title": "Database Connection Timeout",
            "severity": "CRITICAL",
            "service": "order-service",
            "status": "analyzed",
            "ticketId": ticket_id,
            "eventRefs": [],
            "eventCount": 1,
            "firstSeen": now,
            "lastSeen": now,
            "createdAt": now,
            "updatedAt": now
        })

        # Request remediation
        req_res = await client.post(
            "/api/remediation/request",
            json={
                "incidentId": inc_id,
                "actionName": "restart_demo_service",
                "justification": "Clear hung pool connections"
            },
            headers=support_headers
        )
        assert req_res.status_code == 200
        approval_id = req_res.json()["id"]

        # Approver approves
        appr_res = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved"},
            headers=approver_headers
        )
        assert appr_res.status_code == 200
        assert appr_res.json()["status"] == "approved"

        # Verify approval comment added to ticket
        t_doc = await ticket_service.get_ticket(ticket_id)
        assert any("APPROVED by Senior Approver @approver" in c["text"] for c in t_doc["comments"])

        # Mock health check to immediately pass
        class MockHealthResp:
            status_code = 200
            def json(self):
                return {"status": "healthy", "active_fault": None}

        async def mock_health_get(*args, **kwargs):
            return MockHealthResp()

        monkeypatch.setattr("httpx.AsyncClient.get", mock_health_get)

        # Approver executes
        exec_res = await client.post(
            f"/api/remediation/execute/{approval_id}",
            headers=approver_headers
        )
        assert exec_res.status_code == 200

        # Wait briefly for background recovery verification task
        import asyncio
        await asyncio.sleep(0.5)

        # Verify Incident is resolved
        inc_doc = await incident_repo.get_by_id(inc_id)
        assert inc_doc["status"] == "resolved"
        assert inc_doc.get("resolvedAt") is not None

        # Verify Ticket is resolved with resolution comment
        t_doc = await ticket_service.get_ticket(ticket_id)
        assert t_doc["status"] == "resolved"
        assert t_doc.get("resolvedAt") is not None
        assert any("Automated recovery verification PASSED" in c["text"] for c in t_doc["comments"])

        # Verify approval record verificationStatus is verified
        approvals_col = DatabaseManager.get_collection("actionApprovals")
        rec = await approvals_col.find_one({"_id": approval_id})
        assert rec["verificationStatus"] == "verified"


@pytest.mark.asyncio
async def test_step6_recovery_verification_failure_escalates(monkeypatch):
    """
    Step 6 Failure:
    - If health checks fail during recovery verification,
      the incident and ticket automatically shift to escalated status.
    """
    async def mock_exec(*args, **kwargs):
        return True, {"status": "ok"}
    monkeypatch.setattr("app.api.remediation.remediation_executor.execute_allow_listed_action", mock_exec)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        approver_headers = await get_user_headers(client, "approver")
        support_headers = await get_user_headers(client, "support")

        inc_id = str(uuid.uuid4())
        ticket_id = await ticket_service.create_ticket_for_incident(
            incident_id=inc_id,
            title="Unresponsive Microservice",
            severity="CRITICAL"
        )
        now = datetime.now(timezone.utc)
        await incident_repo.create({
            "_id": inc_id,
            "title": "Unresponsive Microservice",
            "severity": "CRITICAL",
            "service": "order-service",
            "status": "analyzed",
            "ticketId": ticket_id,
            "eventRefs": [],
            "eventCount": 1,
            "firstSeen": now,
            "lastSeen": now,
            "createdAt": now,
            "updatedAt": now
        })

        # Request and approve
        req_res = await client.post(
            "/api/remediation/request",
            json={"incidentId": inc_id, "actionName": "restart_demo_service"},
            headers=support_headers
        )
        approval_id = req_res.json()["id"]

        await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved"},
            headers=approver_headers
        )

        # Mock health check to return unhealthy (active_fault still present)
        class MockUnhealthyResp:
            status_code = 503
            def json(self):
                return {"status": "unhealthy", "active_fault": "db_connection_timeout"}

        async def mock_health_unhealthy(*args, **kwargs):
            return MockUnhealthyResp()

        monkeypatch.setattr("httpx.AsyncClient.get", mock_health_unhealthy)

        # Run verification directly with fast retry for test speed
        passed = await health_check_service.verify_recovery(
            incident_id=inc_id,
            ticket_id=ticket_id,
            approval_id=approval_id,
            health_check_path="/health",
            max_retries=2,
            retry_delay_seconds=0.1
        )
        assert passed is False

        # Verify Incident escalated
        inc_doc = await incident_repo.get_by_id(inc_id)
        assert inc_doc["status"] == "escalated"
        assert "Recovery verification failed" in inc_doc["escalationReason"]

        # Verify Ticket escalated with escalation comment
        t_doc = await ticket_service.get_ticket(ticket_id)
        assert t_doc["status"] == "escalated"
        assert any("Automated recovery verification FAILED" in c["text"] for c in t_doc["comments"])

        # Verify approval record verificationStatus is failed
        approvals_col = DatabaseManager.get_collection("actionApprovals")
        rec = await approvals_col.find_one({"_id": approval_id})
        assert rec["verificationStatus"] == "failed"
