import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.models.incident import Incident, IncidentStatus
from app.repositories.incident_repo import incident_repo
from app.services.detection import MatchedDetection

logger = logging.getLogger(__name__)

class GroupingService:
    def __init__(self):
        self._rca_hook = None

    def register_rca_hook(self, hook):
        self._rca_hook = hook

    async def correlate_and_group(self, matches: List[MatchedDetection]) -> List[str]:
        incident_ids: List[str] = []

        for match in matches:
            if not match.matched_events:
                continue

            # Group events within this match by (service, fingerprint)
            clusters: Dict[tuple, List[Dict[str, Any]]] = {}
            for ev in match.matched_events:
                key = (ev.get("service", "unknown"), ev.get("fingerprint", "default"))
                clusters.setdefault(key, []).append(ev)

            for (service, fingerprint), ev_list in clusters.items():
                ev_ids = [e["_id"] for e in ev_list]
                source_type = ev_list[0].get("source", {}).get("type", "manual_upload")
                first_seen = min(e.get("timestamp", datetime.now(timezone.utc)) for e in ev_list)
                last_seen = max(e.get("timestamp", datetime.now(timezone.utc)) for e in ev_list)
                representative_msg = ev_list[0].get("message", "Incident detected").split("\n")[0][:120]

                # 1. Check for existing open incident within window (Deduplication)
                open_incident = await incident_repo.find_matching_open_incident(
                    service=service,
                    fingerprint=fingerprint,
                    window_minutes=15
                )

                if open_incident:
                    incident_id = str(open_incident["_id"])
                    await incident_repo.add_events_to_incident(
                        incident_id=incident_id,
                        event_ids=ev_ids,
                        source=source_type,
                        last_seen=last_seen
                    )
                    # Add matched rule name if not present
                    if match.rule_name not in open_incident.get("matchedRules", []):
                        col = incident_repo.col
                        await col.update_one(
                            {"_id": incident_id},
                            {"$addToSet": {"matchedRules": match.rule_name}}
                        )
                    incident_ids.append(incident_id)
                    logger.info(f"Deduplicated {len(ev_ids)} events into open incident {incident_id}")
                    continue

                # 2. Check for recently resolved incident (Repeated Incident reopening)
                resolved_incident = await incident_repo.find_recently_resolved_incident(
                    service=service,
                    fingerprint=fingerprint,
                    window_minutes=15
                )

                if resolved_incident:
                    resolved_at = resolved_incident.get("resolvedAt") or resolved_incident.get("updatedAt")
                    if resolved_at:
                        if isinstance(resolved_at, str):
                            try:
                                resolved_at = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
                            except Exception:
                                resolved_at = None
                    # If log event was timestamped before resolution (buffered in-flight log), do not falsely escalate
                    if resolved_at and last_seen <= resolved_at + timedelta(seconds=5):
                        logger.info(f"Ignoring buffered pre-resolution log event for resolved incident {resolved_incident['_id']}")
                        continue

                    incident_id = str(resolved_incident["_id"])
                    await incident_repo.update(
                        incident_id=incident_id,
                        updates={
                            "status": IncidentStatus.ESCALATED.value,
                            "isRepeated": True,
                            "escalationReason": f"Repeated incident: Reoccurred within 15 minutes of resolution. Rule: {match.rule_name}",
                            "lastSeen": last_seen,
                        }
                    )
                    await incident_repo.add_events_to_incident(
                        incident_id=incident_id,
                        event_ids=ev_ids,
                        source=source_type,
                        last_seen=last_seen
                    )
                    incident_ids.append(incident_id)
                    logger.info(f"Reopened recently resolved incident {incident_id} as repeated (escalated)")
                    continue

                # 3. Create brand new Incident
                new_id = str(uuid.uuid4())
                title = f"{service}: {match.rule_name}"
                now = datetime.now(timezone.utc)

                from app.services.tickets import ticket_service
                ticket_id = await ticket_service.create_ticket_for_incident(new_id, title, match.severity)

                incident_doc = {
                    "_id": new_id,
                    "title": title,
                    "severity": match.severity,
                    "service": service,
                    "status": IncidentStatus.NEW.value,
                    "sources": [source_type],
                    "eventRefs": ev_ids,
                    "eventCount": len(ev_ids),
                    "firstSeen": first_seen,
                    "lastSeen": last_seen,
                    "matchedRules": [match.rule_name],
                    "fingerprint": fingerprint,
                    "probableCauses": [],
                    "observedFacts": [],
                    "aiInferences": [],
                    "diagnosticChecks": [],
                    "recommendedRunbookIds": [],
                    "overallUncertainty": None,
                    "insufficientEvidence": False,
                    "ticketId": ticket_id,
                    "escalationReason": None,
                    "isRepeated": False,
                    "createdAt": now,
                    "updatedAt": now
                }
                await incident_repo.create(incident_doc)
                incident_ids.append(new_id)
                logger.info(f"Created new incident {new_id} for {service}")

                # Trigger RCA background analysis if registered
                if self._rca_hook:
                    try:
                        import asyncio
                        if asyncio.iscoroutinefunction(self._rca_hook):
                            asyncio.create_task(self._rca_hook(new_id))
                        else:
                            self._rca_hook(new_id)
                    except Exception as e:
                        logger.error(f"Failed to schedule RCA hook: {e}")

        return incident_ids

grouping_service = GroupingService()
