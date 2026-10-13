import asyncio
import logging
import uuid
import httpx
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional
from app.core.config import settings
from app.repositories.incident_repo import incident_repo
from app.services.audit import audit_service
from app.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class HealthCheckService:
    async def verify_recovery(
        self,
        incident_id: str,
        ticket_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        health_check_path: str = "/health",
        max_retries: int = 5,
        retry_delay_seconds: float = 1.5
    ) -> bool:
        ticket_col = DatabaseManager.get_collection("tickets")
        approvals_col = DatabaseManager.get_collection("actionApprovals")

        # Resolve ticket_id if not explicitly provided
        if not ticket_id:
            t_doc = await ticket_col.find_one({"incidentId": incident_id})
            if t_doc:
                ticket_id = str(t_doc["_id"])
            else:
                inc_doc = await incident_repo.get_by_id(incident_id)
                if inc_doc and inc_doc.get("ticketId"):
                    ticket_id = inc_doc["ticketId"]

        now = datetime.now(timezone.utc)

        # Move incident and ticket to 'verifying'
        await incident_repo.update(incident_id, {"status": "verifying"})
        if ticket_id:
            verifying_comment = {
                "id": str(uuid.uuid4())[:8],
                "author": "system",
                "authorRole": "system",
                "text": f"Remediation action executed. Commencing automated recovery verification health checks on {health_check_path}...",
                "createdAt": now
            }
            await ticket_col.update_one(
                {"_id": ticket_id},
                {
                    "$set": {"status": "verifying", "updatedAt": now},
                    "$push": {"comments": verifying_comment}
                }
            )

        demo_url = settings.DEMO_APP_URL.rstrip("/")
        target_url = f"{demo_url}{health_check_path}"

        passed = False
        last_error = None

        logger.info(f"Starting recovery verification for incident {incident_id} at {target_url}")

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(target_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("status") == "healthy" and not data.get("active_fault"):
                            passed = True
                            break
                        else:
                            last_error = f"Health endpoint returned active fault: {data.get('active_fault')}"
                    else:
                        last_error = f"HTTP {resp.status_code}"
            except Exception as e:
                # Fallback to 127.0.0.1 in case of localhost resolution discrepancy
                try:
                    alt_url = target_url.replace("localhost", "127.0.0.1")
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(alt_url)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("status") == "healthy" and not data.get("active_fault"):
                                passed = True
                                break
                            else:
                                last_error = f"Health endpoint returned active fault: {data.get('active_fault')}"
                        else:
                            last_error = f"HTTP {resp.status_code}"
                except Exception:
                    last_error = str(e)

            await asyncio.sleep(retry_delay_seconds)

        now = datetime.now(timezone.utc)
        if passed:
            logger.info(f"Recovery verification PASSED for incident {incident_id}")
            # Mark incident and ticket resolved
            await incident_repo.update(incident_id, {
                "status": "resolved",
                "resolvedAt": now
            })
            if ticket_id:
                resolved_comment = {
                    "id": str(uuid.uuid4())[:8],
                    "author": "system",
                    "authorRole": "system",
                    "text": f"Automated recovery verification PASSED: Target service confirmed healthy at {health_check_path}. Incident and Ticket automatically marked resolved.",
                    "createdAt": now
                }
                await ticket_col.update_one(
                    {"_id": ticket_id},
                    {
                        "$set": {"status": "resolved", "resolvedAt": now, "updatedAt": now},
                        "$push": {"comments": resolved_comment}
                    }
                )

            if approval_id:
                await approvals_col.update_one(
                    {"_id": approval_id},
                    {"$set": {"verificationStatus": "verified", "verifiedAt": now, "updatedAt": now}}
                )

            await audit_service.log_event(
                action="RECOVERY_VERIFIED_RESOLVED",
                actor="system",
                role="system",
                entity_type="incident",
                entity_id=incident_id,
                details={"verifiedHealthCheck": health_check_path, "status": "resolved"}
            )
            return True
        else:
            logger.warning(f"Recovery verification FAILED for incident {incident_id}: {last_error}")
            # Escalate incident and ticket
            reason = f"Recovery verification failed: Health check {health_check_path} did not pass after remediation ({last_error})."
            await incident_repo.update(incident_id, {
                "status": "escalated",
                "escalationReason": reason
            })
            if ticket_id:
                escalated_comment = {
                    "id": str(uuid.uuid4())[:8],
                    "author": "system",
                    "authorRole": "system",
                    "text": f"Automated recovery verification FAILED: {reason}. Ticket automatically escalated for emergency intervention.",
                    "createdAt": now
                }
                await ticket_col.update_one(
                    {"_id": ticket_id},
                    {
                        "$set": {"status": "escalated", "updatedAt": now},
                        "$push": {"comments": escalated_comment}
                    }
                )

            if approval_id:
                await approvals_col.update_one(
                    {"_id": approval_id},
                    {"$set": {"verificationStatus": "failed", "verificationError": reason, "updatedAt": now}}
                )

            await audit_service.log_event(
                action="RECOVERY_VERIFICATION_FAILED_ESCALATED",
                actor="system",
                role="system",
                entity_type="incident",
                entity_id=incident_id,
                details={"verifiedHealthCheck": health_check_path, "status": "escalated", "reason": reason}
            )
            return False

health_check_service = HealthCheckService()
