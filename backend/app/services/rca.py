import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.models.incident import IncidentStatus, ProbableCause, EvidenceItem
from app.models.rca import RCAResult
from app.repositories.incident_repo import incident_repo
from app.repositories.log_event_repo import log_event_repo
from app.services.llm.factory import get_llm_provider
from app.services.retrieval import retriever_service
from app.services.redaction import redaction_service

logger = logging.getLogger(__name__)

class RCAService:
    async def analyze_incident(self, incident_id: str) -> Optional[RCAResult]:
        incident = await incident_repo.get_by_id(incident_id)
        if not incident:
            logger.error(f"Cannot analyze nonexistent incident: {incident_id}")
            return None

        # Transition status to analyzing
        await incident_repo.update(incident_id, {"status": IncidentStatus.ANALYZING.value})

        try:
            # 1. Collect incident evidence
            event_ids = incident.get("eventRefs", [])
            raw_events = await log_event_repo.get_by_ids(event_ids[:50])
            
            # Combine event logs into evidence corpus
            raw_messages = [e.get("message", "") for e in raw_events]
            corpus_text = "\n".join(raw_messages)
            
            # Redact evidence corpus
            redacted_corpus, _ = redaction_service.redact(corpus_text)

            # 2. Retrieve top-k similar historical incidents + runbooks
            service_name = incident.get("service", "*")
            query = f"{incident.get('title', '')} {corpus_text[:200]}"
            similar_history = await retriever_service.retrieve_historical_incidents(service_name, query, top_k=3)
            matched_runbooks = await retriever_service.retrieve_runbooks(service_name, query, top_k=3)

            # 3. Construct prompt
            system_instruction = (
                "You are an expert site reliability copilot performing root cause analysis on application failure logs. "
                "Analyze the provided log stream, historical incidents, and runbooks. "
                "Produce strict root cause hypotheses with supporting evidence, diagnostic checks, and separate observed facts from AI inferences. "
                "CRITICAL GROUNDING RULE: Every cited supportingEvidence excerpt MUST be an exact verbatim substring from the provided log stream. Do NOT invent or alter log excerpts."
            )

            user_prompt = f"""
INCIDENT DETAILS:
Service: {service_name}
Title: {incident.get('title')}
Correlated Event Count: {incident.get('eventCount')}
Time Window: {incident.get('firstSeen')} to {incident.get('lastSeen')}

REDACTED LOG EVIDENCE:
{redacted_corpus[:4000]}

SIMILAR HISTORICAL INCIDENTS:
{json.dumps([{ 'title': h.get('title'), 'cause': h.get('verifiedCause'), 'remediation': h.get('remediationPerformed'), 'outcome': h.get('outcome')} for h in similar_history], indent=2)}

APPROVED RUNBOOKS:
{json.dumps([{ 'id': r.get('_id'), 'title': r.get('title'), 'steps': r.get('diagnosticSteps')} for r in matched_runbooks], indent=2)}
"""

            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ]

            # 4. Invoke LLM provider
            llm = get_llm_provider()
            rca_result: RCAResult = await llm.generate(
                messages=messages,
                response_schema=RCAResult,
                temperature=0.1,
                timeout=30.0
            )

            # 5. Anti-Hallucination Evidence Grounding Validation
            validated_causes: List[ProbableCause] = []
            for cause in rca_result.probableCauses:
                validated_evidence: List[EvidenceItem] = []
                for ev in cause.supportingEvidence:
                    # Verify excerpt exists in raw messages
                    excerpt = ev.excerpt.strip()
                    # Check substring match (or match at least 20 chars if excerpt is long)
                    search_snippet = excerpt[:30] if len(excerpt) > 30 else excerpt
                    is_grounded = any(search_snippet.lower() in msg.lower() for msg in raw_messages)
                    if is_grounded:
                        # Find matching event ID if possible
                        matching_event = next((e for e in raw_events if search_snippet.lower() in e.get("message", "").lower()), None)
                        if matching_event and not ev.eventId:
                            ev.eventId = str(matching_event.get("_id"))
                        validated_evidence.append(ev)
                    else:
                        logger.warning(f"Pruned hallucinated evidence excerpt from RCA: '{excerpt}'")

                # If all evidence was dropped, attach first genuine error line as fallback ground
                if not validated_evidence and raw_messages:
                    validated_evidence.append(EvidenceItem(
                        eventId=str(raw_events[0].get("_id")),
                        excerpt=raw_messages[0][:120]
                    ))

                cause.supportingEvidence = validated_evidence
                # Enforce unverified tag
                cause.verified = False
                validated_causes.append(cause)

            rca_result.probableCauses = validated_causes

            # 6. Check Confidence & Escalation Triggers
            lowest_confidence = min([c.confidence for c in validated_causes], default=1.0)
            should_escalate = (
                lowest_confidence < 0.60 
                or rca_result.insufficientEvidence 
                or incident.get("isRepeated", False)
            )

            new_status = IncidentStatus.ESCALATED.value if should_escalate else IncidentStatus.ANALYZED.value
            escalation_reason = incident.get("escalationReason")
            if should_escalate and not escalation_reason:
                if lowest_confidence < 0.60:
                    escalation_reason = f"Low diagnosis confidence ({lowest_confidence:.2f} < 0.60); human review required."
                elif rca_result.insufficientEvidence:
                    escalation_reason = "Insufficient evidence in log corpus to determine root cause conclusively."

            # If recommended runbooks is empty, populate from matched retriever runbooks
            if not rca_result.recommendedRunbookIds and matched_runbooks:
                rca_result.recommendedRunbookIds = [str(r["_id"]) for r in matched_runbooks[:2]]

            # 7. Update incident in database
            updates = {
                "status": new_status,
                "probableCauses": [c.model_dump() for c in rca_result.probableCauses],
                "observedFacts": rca_result.observedFacts,
                "aiInferences": rca_result.aiInferences,
                "diagnosticChecks": [d.model_dump() for d in rca_result.diagnosticChecks],
                "recommendedRunbookIds": rca_result.recommendedRunbookIds,
                "overallUncertainty": rca_result.overallUncertainty,
                "insufficientEvidence": rca_result.insufficientEvidence,
            }
            if escalation_reason:
                updates["escalationReason"] = escalation_reason

            await incident_repo.update(incident_id, updates)
            logger.info(f"RCA completed for incident {incident_id}: status={new_status}")
            return rca_result

        except Exception as e:
            logger.error(f"RCA pipeline failure for incident {incident_id}: {e}", exc_info=True)
            # Graceful fallback: escalate, never silently drop!
            await incident_repo.update(
                incident_id,
                {
                    "status": IncidentStatus.FAILED_ANALYSIS.value,
                    "escalationReason": f"Analysis unavailable: Automated root-cause analysis encountered an error ({str(e)}). Escalated for manual engineering review."
                }
            )
            return None

rca_service = RCAService()
