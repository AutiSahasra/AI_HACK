import logging
from typing import List, Dict, Any, Optional
from app.models.remediation import RemediationRecommendation, ActionRiskLevel
from app.repositories.incident_repo import incident_repo
from app.repositories.log_event_repo import log_event_repo
from app.services.retrieval import retriever_service
from app.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class RecommendationService:
    async def get_recommendations_for_incident(self, incident_id: str) -> List[RemediationRecommendation]:
        incident = await incident_repo.get_by_id(incident_id)
        if not incident:
            return []

        service = incident.get("service", "demo-app")
        title = incident.get("title", "")
        event_ids = incident.get("eventRefs", [])
        
        # Collect actual log messages for grounded evidence
        raw_events = await log_event_repo.get_by_ids(event_ids[:30]) if event_ids else []
        messages = [e.get("message", "") for e in raw_events]
        corpus = " ".join(messages).lower() + " " + title.lower()

        # Retrieve allow-listed actions from catalog
        col = DatabaseManager.get_collection("remediationActions")
        catalog_actions = await col.find({}).to_list(100)
        action_map = {a["name"]: a for a in catalog_actions}

        # Retrieve matched runbooks
        matched_runbooks = []
        try:
            matched_runbooks = await retriever_service.retrieve_runbooks(service, title, top_k=2)
        except Exception as e:
            logger.warning(f"Runbook retrieval error: {e}")

        top_runbook_title = matched_runbooks[0].get("title") if matched_runbooks else f"Runbook: {service.capitalize()} Recovery Standard"

        recommendations: List[RemediationRecommendation] = []

        # 1. Pattern: Database connection pool exhaustion / timeouts
        if any(term in corpus for term in ["timeout", "connection", "pool", "exhausted", "database", "5000ms", "waiters"]):
            if "restart_demo_service" in action_map:
                act = action_map["restart_demo_service"]
                ev_snippets = [m for m in messages if any(k in m.lower() for k in ["timeout", "connection", "pool", "exhausted", "database"])][:2]
                if not ev_snippets and messages:
                    ev_snippets = [messages[0]]

                recommendations.append(RemediationRecommendation(
                    actionName="restart_demo_service",
                    actionTitle="Graceful Container & Connection Pool Recycle",
                    relevanceReason=f"Incident exhibits database socket or worker pool exhaustion on '{service}'. Recycling the service container clears hung connections, releases socket backlogs, and reinitializes database connections.",
                    supportingEvidence=ev_snippets or [f"Active outage: {title}"],
                    expectedOutcome="Recycles connection pool (clearing 20/20 active waiters), restores healthy DB connectivity, and recovers HTTP 200 response latency.",
                    riskLevel=ActionRiskLevel(act.get("riskLevel", "medium")),
                    affectedService=service,
                    parameters={"service": service},
                    requiresApproval=act.get("requiresApproval", True),
                    confidence=0.94,
                    runbookReference=top_runbook_title
                ))

        # 2. Pattern: Memory leak / OutOfMemory / Heap Saturation
        if any(term in corpus for term in ["memory", "heap", "outofmemory", "gc overhead", "buffer", "leak"]):
            if "clear_demo_cache" in action_map:
                act = action_map["clear_demo_cache"]
                ev_snippets = [m for m in messages if any(k in m.lower() for k in ["memory", "heap", "outofmemory", "gc", "buffer"])][:2]
                recommendations.append(RemediationRecommendation(
                    actionName="clear_demo_cache",
                    actionTitle="Flush Heap Memory & Application Cache",
                    relevanceReason=f"Diagnostics indicate heap memory saturation and GC overhead limits on '{service}'. Flushing internal cache stores releases buffered memory immediately without requiring service downtime.",
                    supportingEvidence=ev_snippets or [f"Active memory pressure detected in {service}"],
                    expectedOutcome="Frees internal heap buffers, drops resident memory consumption below threshold, and eliminates garbage collection pauses.",
                    riskLevel=ActionRiskLevel(act.get("riskLevel", "low")),
                    affectedService=service,
                    parameters={},
                    requiresApproval=act.get("requiresApproval", False),
                    confidence=0.92,
                    runbookReference=top_runbook_title
                ))

            if "restart_demo_service" in action_map and not any(r.actionName == "restart_demo_service" for r in recommendations):
                act = action_map["restart_demo_service"]
                recommendations.append(RemediationRecommendation(
                    actionName="restart_demo_service",
                    actionTitle="Container Restart to Clear Saturated Memory",
                    relevanceReason=f"Full JVM/worker recycle to completely restore initial heap state if cache flush is insufficient.",
                    supportingEvidence=[messages[0]] if messages else [title],
                    expectedOutcome="Complete memory heap reset to clean baseline allocation.",
                    riskLevel=ActionRiskLevel(act.get("riskLevel", "medium")),
                    affectedService=service,
                    parameters={"service": service},
                    requiresApproval=act.get("requiresApproval", True),
                    confidence=0.86,
                    runbookReference=top_runbook_title
                ))

        # 3. Pattern: Bad Configuration Deployment / Missing Environment Variable
        if any(term in corpus for term in ["config", "environment", "variable", "db_host", "yaml", "deploy"]):
            if "rollback_demo_config" in action_map:
                act = action_map["rollback_demo_config"]
                ev_snippets = [m for m in messages if any(k in m.lower() for k in ["config", "environment", "variable", "db_host", "yaml"])][:2]
                recommendations.append(RemediationRecommendation(
                    actionName="rollback_demo_config",
                    actionTitle="Rollback Configuration to Last Verified Release",
                    relevanceReason=f"Root-cause analysis detected missing or invalid configuration parameters (e.g. DB_HOST). Rolling back deployment environment variables restores the verified stable baseline.",
                    supportingEvidence=ev_snippets or [f"Configuration error detected in {service}"],
                    expectedOutcome="Restores validated environment variables, allowing the application to successfully parse configuration and pass startup checks.",
                    riskLevel=ActionRiskLevel(act.get("riskLevel", "high")),
                    affectedService=service,
                    parameters={},
                    requiresApproval=act.get("requiresApproval", True),
                    confidence=0.96,
                    runbookReference=top_runbook_title
                ))

        # 4. Fallback: If no specific pattern matched or catalog actions remain, include remaining allow-listed actions
        if not recommendations:
            for name, act in action_map.items():
                title_map = {
                    "restart_demo_service": "Restart Microservice Container",
                    "clear_demo_cache": "Clear In-Memory Cache",
                    "rollback_demo_config": "Rollback Configuration"
                }
                recommendations.append(RemediationRecommendation(
                    actionName=name,
                    actionTitle=title_map.get(name, name.replace("_", " ").title()),
                    relevanceReason=f"Allow-listed remediation action available for {service}. Evaluated based on service classification.",
                    supportingEvidence=[messages[0]] if messages else [title],
                    expectedOutcome=act.get("description", "Executes allow-listed remediation handler."),
                    riskLevel=ActionRiskLevel(act.get("riskLevel", "medium")),
                    affectedService=service,
                    parameters={},
                    requiresApproval=act.get("requiresApproval", True),
                    confidence=0.70,
                    runbookReference=top_runbook_title
                ))

        # Sort recommendations by confidence descending
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        return recommendations

recommendation_service = RecommendationService()
