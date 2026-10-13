import logging
from typing import Dict, List, Any
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.core.database import DatabaseManager

logger = logging.getLogger(__name__)

INDEX_SPECIFICATIONS: Dict[str, List[IndexModel]] = {
    "incidents": [
        IndexModel([("incident_key", ASCENDING)], unique=True, name="idx_incidents_key_unique"),
        IndexModel([("status", ASCENDING)], name="idx_incidents_status"),
        IndexModel([("severity", ASCENDING)], name="idx_incidents_severity"),
        IndexModel([("category_label", ASCENDING)], name="idx_incidents_category_label"),
        IndexModel([("service.name", ASCENDING)], name="idx_incidents_service_name"),
        IndexModel([("created_at", DESCENDING)], name="idx_incidents_created_at"),
        IndexModel([("is_synthetic", ASCENDING)], name="idx_incidents_is_synthetic"),
    ],
    "log_events": [
        IndexModel([("event_id", ASCENDING)], unique=True, name="idx_log_events_id_unique"),
        IndexModel([("timestamp", DESCENDING)], name="idx_log_events_timestamp"),
        IndexModel([("service_name", ASCENDING), ("timestamp", DESCENDING)], name="idx_log_events_service_timestamp"),
        IndexModel([("incident_id", ASCENDING)], name="idx_log_events_incident_id"),
        IndexModel([("fingerprint", ASCENDING)], name="idx_log_events_fingerprint"),
    ],
    "knowledge_articles": [
        IndexModel([("article_id", ASCENDING)], unique=True, name="idx_knowledge_article_id_unique"),
        IndexModel([("category", ASCENDING)], name="idx_knowledge_category"),
        IndexModel([("verified", ASCENDING)], name="idx_knowledge_verified"),
    ],
    "analysis_runs": [
        IndexModel([("incident_id", ASCENDING), ("created_at", DESCENDING)], name="idx_analysis_runs_incident_created"),
        IndexModel([("xgboost.predicted_category", ASCENDING)], name="idx_analysis_runs_xgb_category"),
    ],
    "model_registry": [
        IndexModel([("model_name", ASCENDING), ("version", ASCENDING)], unique=True, name="idx_model_registry_name_ver_unique"),
        IndexModel([("is_active", ASCENDING)], name="idx_model_registry_is_active"),
    ],
}


async def initialize_all_indexes() -> Dict[str, List[str]]:
    """
    Idempotent database initialization and index creation for all 5 collections.
    Safe to run repeatedly.
    """
    results: Dict[str, List[str]] = {}
    for collection_name, index_models in INDEX_SPECIFICATIONS.items():
        col = DatabaseManager.get_collection(collection_name)
        created_names = []
        for im in index_models:
            try:
                res = await col.create_indexes([im])
                created_names.extend(res)
            except Exception as e:
                # If already exists with different name, ignore conflict
                if "IndexOptionsConflict" in str(e) or "already exists" in str(e).lower():
                    name = getattr(im, "name", "existing_index")
                    created_names.append(f"{name} (existing)")
                else:
                    logger.warning(f"Index creation note on {collection_name}: {e}")
                    created_names.append(f"err: {e}")
        results[collection_name] = created_names
        logger.info(f"Initialized indexes on collection '{collection_name}': {created_names}")
    return results
