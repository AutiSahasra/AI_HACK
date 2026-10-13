import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data
from app.core.config import settings
from app.repositories.incident_repo import incident_repo

@pytest.fixture(autouse=True)
async def setup_test_env():
    settings.USE_IN_MEMORY_DB = True
    await DatabaseManager.connect()
    await seed_all_data()
    yield
    await DatabaseManager.disconnect()

async def get_user_headers(client: AsyncClient, username: str, password: str = "password123"):
    # seeder sets username + "password123" e.g. adminpassword123, approverpassword123, supportpassword123
    resp = await client.post("/api/auth/login", json={"username": username, "password": f"{username}password123"})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

async def create_test_incident(incident_id: str):
    now = datetime.now(timezone.utc)
    doc = {
        "_id": incident_id,
        "title": "Database Connection Pool Timeout",
        "severity": "CRITICAL",
        "service": "order-service",
        "status": "awaiting_approval",
        "eventRefs": [],
        "eventCount": 1,
        "firstSeen": now,
        "lastSeen": now,
        "createdAt": now,
        "updatedAt": now
    }
    await incident_repo.create(doc)
    return doc

# =========================================================================
# 1. SUPPORT ENGINEER TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_support_engineer_permissions_and_restrictions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        support_headers = await get_user_headers(client, "support")

        # ALLOWED:
        # a) Dashboard metrics
        dash_res = await client.get("/api/admin/dashboard/stats", headers=support_headers)
        assert dash_res.status_code == 200

        # b) Log query
        logs_res = await client.get("/api/logs", headers=support_headers)
        assert logs_res.status_code == 200

        # c) View incidents
        inc_res = await client.get("/api/incidents", headers=support_headers)
        assert inc_res.status_code == 200

        # d) Request remediation action
        inc_id = str(uuid.uuid4())
        await create_test_incident(inc_id)
        req_res = await client.post(
            "/api/remediation/request",
            json={"incidentId": inc_id, "actionName": "restart_demo_service"},
            headers=support_headers
        )
        assert req_res.status_code == 200
        approval_id = req_res.json()["id"]

        # DENIED (HTTP 403):
        # 1. Cannot view approvals queue
        appr_queue_res = await client.get("/api/remediation/approvals", headers=support_headers)
        assert appr_queue_res.status_code == 403

        # 2. Cannot decide on approval
        decide_res = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved"},
            headers=support_headers
        )
        assert decide_res.status_code == 403

        # 3. Cannot execute remediation
        exec_res = await client.post(f"/api/remediation/execute/{approval_id}", headers=support_headers)
        assert exec_res.status_code == 403

        # 4. Cannot access audit trail
        audit_res = await client.get("/api/audit", headers=support_headers)
        assert audit_res.status_code == 403

        # 5. Cannot list or create log sources
        sources_get = await client.get("/api/admin/sources", headers=support_headers)
        assert sources_get.status_code == 403
        sources_post = await client.post("/api/admin/sources", json={"name": "test-src"}, headers=support_headers)
        assert sources_post.status_code == 403

        # 6. Cannot view or configure detection rules
        rules_get = await client.get("/api/admin/rules", headers=support_headers)
        assert rules_get.status_code == 403
        rules_patch = await client.patch("/api/admin/rules/rule_error_rate_spike", json={"enabled": False}, headers=support_headers)
        assert rules_patch.status_code == 403

        # 7. Cannot execute retention cleanup
        retention_res = await client.post("/api/admin/retention/cleanup?days=30", headers=support_headers)
        assert retention_res.status_code == 403

        # 8. Cannot trigger demo fault or reset
        fault_res = await client.post("/api/admin/demo/inject-fault", json={"faultType": "db_timeout"}, headers=support_headers)
        assert fault_res.status_code == 403

# =========================================================================
# 2. APPROVER TESTS (DUAL AUTHORIZATION & SELF-APPROVAL POLICY)
# =========================================================================

@pytest.mark.asyncio
async def test_approver_dual_auth_and_no_self_approval(monkeypatch):
    async def mock_exec(*args, **kwargs):
        return True, {"status": "ok"}
    monkeypatch.setattr("app.api.remediation.remediation_executor.execute_allow_listed_action", mock_exec)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        approver_headers = await get_user_headers(client, "approver")
        support_headers = await get_user_headers(client, "support")

        # ALLOWED:
        # a) Approver can view approvals queue & audit trail
        appr_list = await client.get("/api/remediation/approvals", headers=approver_headers)
        assert appr_list.status_code == 200
        audit_list = await client.get("/api/audit", headers=approver_headers)
        assert audit_list.status_code == 200

        # Scenario A: Support requests action -> Approver approves -> Approver executes
        inc_id1 = str(uuid.uuid4())
        await create_test_incident(inc_id1)
        req_res1 = await client.post(
            "/api/remediation/request",
            json={"incidentId": inc_id1, "actionName": "restart_demo_service"},
            headers=support_headers
        )
        assert req_res1.status_code == 200
        appr_id1 = req_res1.json()["id"]

        # Approver approves request made by support -> SUCCESS
        decision_res = await client.post(
            f"/api/remediation/approvals/{appr_id1}/decision",
            json={"decision": "approved"},
            headers=approver_headers
        )
        assert decision_res.status_code == 200
        assert decision_res.json()["status"] == "approved"
        assert decision_res.json()["approvedBy"] == "approver"

        # Approver executes approved action -> SUCCESS
        exec_res = await client.post(f"/api/remediation/execute/{appr_id1}", headers=approver_headers)
        assert exec_res.status_code == 200

        # Scenario B: Approver cannot create approval requests
        inc_id2 = str(uuid.uuid4())
        await create_test_incident(inc_id2)
        req_res2 = await client.post(
            "/api/remediation/request",
            json={"incidentId": inc_id2, "actionName": "restart_demo_service"},
            headers=approver_headers
        )
        assert req_res2.status_code == 403

        # Scenario C: Self-approval policy test (if a request has requestedBy = approver)
        col = DatabaseManager.get_collection("actionApprovals")
        self_doc = {
            "_id": "self-req-test-1",
            "incidentId": inc_id1,
            "actionName": "restart_demo_service",
            "status": "pending",
            "requestedBy": "approver",
            "requestedByRole": "approver",
            "parameters": {},
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc),
            "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        await col.insert_one(self_doc)

        self_approve_res = await client.post(
            "/api/remediation/approvals/self-req-test-1/decision",
            json={"decision": "approved"},
            headers=approver_headers
        )
        assert self_approve_res.status_code == 403
        assert "Self-approval policy violation" in self_approve_res.text

        # Rejection requires mandatory rationale
        no_reason_rej = await client.post(
            f"/api/remediation/approvals/{appr_id1}/decision",
            json={"decision": "rejected", "reason": ""},
            headers=approver_headers
        )
        assert no_reason_rej.status_code == 400

        # DENIED: Approver cannot configure log sources, detection rules, retention, or demo faults
        assert (await client.get("/api/admin/sources", headers=approver_headers)).status_code == 403
        assert (await client.get("/api/admin/rules", headers=approver_headers)).status_code == 403
        assert (await client.post("/api/admin/retention/cleanup", headers=approver_headers)).status_code == 403
        assert (await client.post("/api/admin/demo/inject-fault", json={"faultType": "x"}, headers=approver_headers)).status_code == 403

# =========================================================================
# 3. ADMIN TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_admin_permissions_and_safety_controls():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        admin_headers = await get_user_headers(client, "admin")

        # ALLOWED:
        # a) Manage sources & API keys
        sources_res = await client.get("/api/admin/sources", headers=admin_headers)
        assert sources_res.status_code == 200
        # Secrets in GET must be masked
        sources_list = sources_res.json()
        if len(sources_list) > 0 and "apiKey" in sources_list[0]:
            assert "..." in sources_list[0]["apiKey"] or "src_***" in sources_list[0]["apiKey"]

        # b) Manage detection rules
        rules_res = await client.get("/api/admin/rules", headers=admin_headers)
        assert rules_res.status_code == 200

        # c) Retention cleanup
        retention_res = await client.post("/api/admin/retention/cleanup?days=60", headers=admin_headers)
        assert retention_res.status_code == 200
        assert "Pruned logs" in retention_res.json()["message"]

        # d) Check audit trail has recorded admin operations
        audit_res = await client.get("/api/audit?actor=admin", headers=admin_headers)
        assert audit_res.status_code == 200
        entries = audit_res.json()
        assert len(entries) > 0

        # e) Admin can submit approval requests and view their own submitted requests
        inc_id = str(uuid.uuid4())
        await create_test_incident(inc_id)
        admin_req = await client.post(
            "/api/remediation/request",
            json={"incidentId": inc_id, "actionName": "restart_demo_service"},
            headers=admin_headers
        )
        assert admin_req.status_code == 200
        approval_id = admin_req.json()["id"]

        my_reqs = await client.get("/api/remediation/my-requests", headers=admin_headers)
        assert my_reqs.status_code == 200
        assert any(r["id"] == approval_id for r in my_reqs.json())

        # f) Admin CANNOT view Approvals queue or decide on approvals
        admin_queue = await client.get("/api/remediation/approvals", headers=admin_headers)
        assert admin_queue.status_code == 403

        admin_decide = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved"},
            headers=admin_headers
        )
        assert admin_decide.status_code == 403

# =========================================================================
# 4. CONCURRENCY & SECURITY EDGE CASES
# =========================================================================

@pytest.mark.asyncio
async def test_concurrency_and_security_controls(monkeypatch):
    async def mock_exec(*args, **kwargs):
        return True, {"status": "ok"}
    monkeypatch.setattr("app.api.remediation.remediation_executor.execute_allow_listed_action", mock_exec)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        admin_headers = await get_user_headers(client, "admin")
        approver_headers = await get_user_headers(client, "approver")
        support_headers = await get_user_headers(client, "support")

        # 1. Unauthenticated requests return 401
        unauth_res = await client.get("/api/audit")
        assert unauth_res.status_code == 401

        # 2. Concurrency-safe double decision: second decision on same item fails
        inc_id = str(uuid.uuid4())
        await create_test_incident(inc_id)
        req = await client.post(
            "/api/remediation/request",
            json={"incidentId": inc_id, "actionName": "restart_demo_service"},
            headers=support_headers
        )
        approval_id = req.json()["id"]

        first_dec = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved"},
            headers=approver_headers
        )
        assert first_dec.status_code == 200

        # Immediate second approval attempt -> 409 Conflict
        second_dec = await client.post(
            f"/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved"},
            headers=approver_headers
        )
        assert second_dec.status_code in (409, 400)

        # 3. Concurrency-safe double execution: second execution attempt fails
        first_exec = await client.post(f"/api/remediation/execute/{approval_id}", headers=approver_headers)
        assert first_exec.status_code == 200

        second_exec = await client.post(f"/api/remediation/execute/{approval_id}", headers=approver_headers)
        assert second_exec.status_code in (409, 403, 400)
