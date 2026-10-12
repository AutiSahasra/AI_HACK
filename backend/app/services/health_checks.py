import asyncio
import logging
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
        health_check_path: str = "/health",
        max_retries: int = 4,
        retry_delay_seconds: float = 1.5
    ) -> bool:
        # Move incident and ticket to 'verifying'
        await incident_repo.update(incident_id, {"status": "verifying"})
        if ticket_id:
            ticket_col = DatabaseManager.get_collection("tickets")
            await ticket_col.update_one({"_id": ticket_id}, {"$set": {"status": "verifying"}})

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
                ticket_col = DatabaseManager.get_collection("tickets")
                await ticket_col.update_one({"_id": ticket_id}, {"$set": {"status": "resolved", "resolvedAt": now}})

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
            # Escalate incident
            reason = f"Recovery verification failed: Health check {health_check_path} did not pass after remediation ({last_error})."
            await incident_repo.update(incident_id, {
                "status": "escalated",
                "escalationReason": reason
            })
            if ticket_id:
                ticket_col = DatabaseManager.get_collection("tickets")
                await ticket_col.update_one({"_id": ticket_id}, {"$set": {"status": "escalated"}})

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
