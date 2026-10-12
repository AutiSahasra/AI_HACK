import asyncio
import sys
import os
import time
import httpx
from datetime import datetime, timezone

# Add root and backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def run_e2e_scenario(backend_url: str = "http://localhost:8000", demo_url: str = "http://localhost:8001"):
    print("==========================================================================")
    print("  AI ROOT CAUSE ANALYSIS & COPILOT - END-TO-END SCENARIO VALIDATION     ")
    print("==========================================================================")
    print(f"Backend Target: {backend_url}")
    print(f"Demo App Target: {demo_url}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Verify Service Health
        print("[Step 1/10] Verifying backend and demo app connectivity...")
        try:
            b_resp = await client.get(f"{backend_url}/api/health")
            assert b_resp.status_code == 200, f"Backend health returned {b_resp.status_code}"
            print("  ✓ Backend is healthy (HTTP 200)")

            d_resp = await client.get(f"{demo_url}/health")
            assert d_resp.status_code == 200, f"Demo app health returned {d_resp.status_code}"
            print("  ✓ Demo application is healthy (HTTP 200)")
        except Exception as e:
            print(f"  ✗ Connection failed: {e}")
            print("  Note: If running outside docker, ensure backend and demo-app are started.")
            return False

        # 2. Inject Fault in Demo App
        print("\n[Step 2/10] Injecting fault 'db_connection_timeout' in demo app...")
        fault_resp = await client.post(f"{demo_url}/faults/db_connection_timeout")
        assert fault_resp.status_code == 200, f"Fault injection failed: {fault_resp.text}"
        print("  ✓ Fault injected successfully: 'Database connection pool timeout simulated'")

        # 3. Verify Degraded State
        print("\n[Step 3/10] Verifying demo app health state reflects fault...")
        d_health_post = await client.get(f"{demo_url}/health")
        assert d_health_post.status_code == 503, f"Expected 503 degraded, got {d_health_post.status_code}"
        print(f"  ✓ Demo app health degraded: HTTP {d_health_post.status_code}")

        # 4. Ingest Log Batch via Shared Pipeline (Live Collector)
        print("\n[Step 4/10] Forwarding simulated fault log stream to /api/ingest...")
        collector_key = "dev-live-collector-key-secret"
        now_iso = datetime.now(timezone.utc).isoformat()
        log_payload = {
            "sourceId": "live_demo_app",
            "events": [
                {
                    "timestamp": now_iso,
                    "service": "order-service",
                    "severity": "WARN",
                    "message": "Connection pool usage reached 90% (18/20 active sessions)",
                    "traceId": "tr-e2e-884"
                },
                {
                    "timestamp": now_iso,
                    "service": "order-service",
                    "severity": "ERROR",
                    "message": "ConnectionPoolTimeout: Timeout waiting for connection from pool after 30000ms. Active: 20/20",
                    "traceId": "tr-e2e-884"
                },
                {
                    "timestamp": now_iso,
                    "service": "order-service",
                    "severity": "CRITICAL",
                    "message": "Fatal: Database connection pool fully saturated for order-service",
                    "traceId": "tr-e2e-884"
                }
            ]
        }
        ingest_resp = await client.post(
            f"{backend_url}/api/ingest",
            json=log_payload,
            headers={"X-API-Key": collector_key}
        )
        assert ingest_resp.status_code == 200, f"Ingest failed: {ingest_resp.text}"
        print(f"  ✓ Logs ingested and processed through detection pipeline ({ingest_resp.json().get('ingestedCount')} events)")

        # 5. Wait and Verify Auto-Created Incident
        print("\n[Step 5/10] Checking auto-detected incident for order-service...")
        await asyncio.sleep(1.0)
        
        # Authenticate as Support Engineer
        support_login = await client.post(
            f"{backend_url}/api/auth/login",
            json={"username": "support", "password": "supportpassword123"}
        )
        assert support_login.status_code == 200
        support_token = support_login.json()["access_token"]
        support_headers = {"Authorization": f"Bearer {support_token}"}

        inc_list_resp = await client.get(f"{backend_url}/api/incidents?service=order-service", headers=support_headers)
        assert inc_list_resp.status_code == 200
        incidents = inc_list_resp.json().get("items", [])
        assert len(incidents) > 0, "No incidents found for order-service"
        incident = incidents[0]
        incident_id = incident.get("id") or incident.get("_id")
        print(f"  ✓ Incident auto-created: ID={incident_id}, Title='{incident.get('title')}', Severity={incident.get('severity')}")

        # 6. Verify RCA Findings
        print("\n[Step 6/10] Verifying AI Root Cause Analysis findings...")
        inc_detail_resp = await client.get(f"{backend_url}/api/incidents/{incident_id}", headers=support_headers)
        assert inc_detail_resp.status_code == 200
        inc_data = inc_detail_resp.json()
        causes = inc_data.get("probableCauses", [])
        if not causes:
            # Trigger analysis if not yet run
            analyze_resp = await client.post(f"{backend_url}/api/incidents/{incident_id}/analyze", headers=support_headers)
            inc_data = analyze_resp.json()
            causes = inc_data.get("probableCauses", [])
        
        assert len(causes) > 0, "No root causes generated in RCA"
        top_cause = causes[0]
        print(f"  ✓ Top Root Cause Hypothesis: '{top_cause.get('description')}'")
        print(f"  ✓ Confidence: {top_cause.get('confidence')} ({top_cause.get('confidenceTier')})")
        print(f"  ✓ Observed Facts Count: {len(inc_data.get('observedFacts', []))}")
        print(f"  ✓ AI Inferences Count: {len(inc_data.get('aiInferences', []))}")

        # 7. Support Engineer Requests Remediation Action
        print("\n[Step 7/10] Support engineer requests protected remediation 'restart_demo_service'...")
        req_action_resp = await client.post(
            f"{backend_url}/api/remediation/request",
            json={"incidentId": incident_id, "actionName": "restart_demo_service"},
            headers=support_headers
        )
        assert req_action_resp.status_code == 200
        approval_data = req_action_resp.json()
        approval_id = approval_data.get("id") or approval_data.get("_id")
        assert approval_data.get("status") == "pending"
        print(f"  ✓ Remediation request submitted: Approval ID={approval_id}, Status='pending'")

        # 8. Approver Approves Request
        print("\n[Step 8/10] Senior approver logs in and grants dual-authorization approval...")
        approver_login = await client.post(
            f"{backend_url}/api/auth/login",
            json={"username": "approver", "password": "approverpassword123"}
        )
        assert approver_login.status_code == 200
        approver_token = approver_login.json()["access_token"]
        approver_headers = {"Authorization": f"Bearer {approver_token}"}

        approve_resp = await client.post(
            f"{backend_url}/api/remediation/approvals/{approval_id}/decision",
            json={"decision": "approved", "reason": "Verified DB pool timeout signatures from log evidence"},
            headers=approver_headers
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json().get("status") == "approved"
        print("  ✓ Action authorization approved by 'approver'")

        # 9. Execute Allow-Listed Action
        print("\n[Step 9/10] Executing allow-listed remediation action...")
        exec_resp = await client.post(
            f"{backend_url}/api/remediation/execute/{approval_id}",
            headers=approver_headers
        )
        assert exec_resp.status_code == 200
        print(f"  ✓ Execution response: {exec_resp.json().get('status')} - {exec_resp.json().get('message')}")

        # 10. Verify Post-Action Recovery Verification Loop and Incident Resolution
        print("\n[Step 10/10] Waiting for post-action recovery verification loop...")
        resolved = False
        for attempt in range(12):
            await asyncio.sleep(1.0)
            chk_inc = await client.get(f"{backend_url}/api/incidents/{incident_id}", headers=support_headers)
            if chk_inc.json().get("status") == "resolved":
                resolved = True
                print(f"  ✓ Incident {incident_id} successfully transitioned to 'resolved' after recovery check passed!")
                break
            print(f"  ... Incident status: {chk_inc.json().get('status')} (attempt {attempt + 1}/12)")

        assert resolved, "Incident failed to resolve after recovery verification timeout"

        # Verify Audit Trail
        print("\nVerifying append-only audit trail...")
        audit_resp = await client.get(f"{backend_url}/api/audit/logs?limit=50", headers=approver_headers)
        assert audit_resp.status_code == 200
        audit_items = audit_resp.json().get("items", [])
        action_types = [a.get("action") for a in audit_items]
        print(f"  ✓ Recent audit actions captured: {len(audit_items)} entries")
        for expected in ["REMEDIATION_ACTION_REQUESTED", "APPROVAL_DECISION_APPROVED", "REMEDIATION_ACTION_EXECUTED"]:
            assert expected in action_types, f"Missing audit action {expected}"
            print(f"  ✓ Verified audit event: {expected}")

        print("\n==========================================================================")
        print("  🎉 COMPLETE END-TO-END SCENARIO VALIDATION PASSED SUCCESSFULLY!         ")
        print("==========================================================================\n")
        return True

if __name__ == "__main__":
    b_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    d_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8001"
    success = asyncio.run(run_e2e_scenario(b_url, d_url))
    sys.exit(0 if success else 1)
