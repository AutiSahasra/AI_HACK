import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.database import DatabaseManager
from app.core.db_indexes import initialize_all_indexes
from app.models.schema_spec import (
    IncidentMetrics,
    CategoryLabelEnum,
    AnalysisRunDoc,
    XGBoostPredictionMeta,
    MiniLMMatchesMeta,
)
from app.services.minilm_service import minilm_service, MODEL_ID
from app.services.xgboost_service import xgboost_service
from app.services.synthetic_generator import generate_synthetic_dataset
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["Machine Learning & Copilot Pipeline"])


class GenerateSyntheticRequest(BaseModel):
    count: int = Field(350, ge=10, le=2000, description="Number of synthetic incidents to generate")
    seed: int = Field(42, description="Fixed random seed for deterministic generation")
    clear_existing: bool = Field(True, description="Whether to clear existing synthetic data before inserting")


class TrainXGBoostRequest(BaseModel):
    test_size: float = Field(0.2, ge=0.05, le=0.5, description="Fraction of records reserved for test evaluation")
    random_state: int = Field(42, description="Random split seed")


class AnalyzeIncidentRequest(BaseModel):
    incident_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    service_name: Optional[str] = None
    metrics: Optional[IncidentMetrics] = None


class SemanticRetrievalRequest(BaseModel):
    query: str = Field(..., description="Query symptom or problem description for semantic search")
    top_k: int = Field(5, ge=1, le=20)
    category: Optional[str] = None
    service: Optional[str] = None


@router.post("/db/init-indexes")
async def init_indexes():
    """
    Idempotent initialization script for MongoDB collections and indexes specified in PDF.
    """
    results = await initialize_all_indexes()
    return {
        "status": "success",
        "message": "Indexes initialized across all 5 collections",
        "indexes": results,
    }


@router.post("/synthetic/generate")
async def generate_synthetic_data(payload: GenerateSyntheticRequest):
    """
    Generate deterministic synthetic incidents, log events, and knowledge articles (Section 9 & 13).
    """
    incidents, log_events, knowledge_articles = generate_synthetic_dataset(
        count=payload.count,
        seed=payload.seed,
    )

    inc_col = DatabaseManager.get_collection("incidents")
    logs_col = DatabaseManager.get_collection("log_events")
    kb_col = DatabaseManager.get_collection("knowledge_articles")

    if payload.clear_existing:
        await inc_col.delete_many({"is_synthetic": True})
        await logs_col.delete_many({"is_synthetic": True})
        await kb_col.delete_many({"is_synthetic": True})

    await inc_col.insert_many(incidents)
    await logs_col.insert_many(log_events)
    await kb_col.insert_many(knowledge_articles)

    return {
        "status": "success",
        "seed": payload.seed,
        "counts": {
            "incidents": len(incidents),
            "log_events": len(log_events),
            "knowledge_articles": len(knowledge_articles),
        },
        "sample_incident_key": incidents[0]["incident_key"] if incidents else None,
    }


@router.post("/xgboost/train")
async def train_xgboost_model(payload: TrainXGBoostRequest):
    """
    Train XGBoost category classifier on structured metrics features and record in model_registry.
    """
    inc_col = DatabaseManager.get_collection("incidents")
    records = await inc_col.find({"is_synthetic": True}).to_list(2000)

    if len(records) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient training records. Please call /api/ml/synthetic/generate first.",
        )

    results = xgboost_service.train_and_evaluate(
        training_records=records,
        test_size=payload.test_size,
        random_state=payload.random_state,
    )

    registry_doc = await xgboost_service.register_model(
        train_results=results,
        dataset_version=f"synth-seed-{payload.random_state}",
    )

    return {
        "status": "success",
        "training_results": results,
        "model_registry_entry": registry_doc,
    }


@router.post("/analyze")
async def analyze_incident(payload: AnalyzeIncidentRequest):
    """
    Perform full Copilot Root Cause Analysis:
    1. Check Redis cache by input features / model version.
    2. XGBoost classification on structured metrics.
    3. MiniLM 384-dimensional semantic similarity retrieval over knowledge articles.
    4. Store run in analysis_runs and cache in Redis.
    """
    inc_col = DatabaseManager.get_collection("incidents")
    kb_col = DatabaseManager.get_collection("knowledge_articles")
    runs_col = DatabaseManager.get_collection("analysis_runs")

    target_incident = None
    if payload.incident_id:
        target_incident = await inc_col.find_one({"_id": payload.incident_id})
        if not target_incident:
            target_incident = await inc_col.find_one({"incident_key": payload.incident_id})

    # Prepare metrics and text
    metrics_data: Dict[str, Any] = {}
    if target_incident:
        metrics_data = target_incident.get("metrics") or {}
        text_for_search = f"{target_incident.get('title', '')}. {target_incident.get('description', '')}"
        incident_id_str = str(target_incident.get("_id") or target_incident.get("incident_key"))
    else:
        if payload.metrics:
            metrics_data = payload.metrics.model_dump(exclude_none=False)
        text_for_search = f"{payload.title or ''}. {payload.description or ''}"
        incident_id_str = payload.incident_id or "adhoc_incident"

    # 1. Check Redis Cache
    cache_key = redis_service.make_cache_key(
        incident_features=metrics_data,
        model_version=xgboost_service.version,
    )
    cached_run = redis_service.get_cached_analysis(cache_key)
    if cached_run:
        cached_run["cache_hit"] = True
        return cached_run

    # 2. XGBoost Structured Classification
    xgb_pred = xgboost_service.predict(metrics_data)

    # 3. MiniLM Semantic Retrieval against Knowledge Articles
    articles = await kb_col.find({}).to_list(100)
    top_matches = minilm_service.retrieve_top_matches(
        query_text=text_for_search,
        corpus=articles,
        top_k=3,
    )

    # 4. Final Assessment (Template/Rule-based, avoids claiming certainty as per PDF Section 7)
    pred_cat = xgb_pred["predicted_category"]
    top_prob = xgb_pred["class_probabilities"].get(pred_cat, 0.0)
    assessment = (
        f"AI Copilot Assessment: Incident metrics strongly correlate with '{pred_cat}' category "
        f"(confidence: {round(top_prob*100, 1)}%). Recommended action: consult retrieved runbooks."
    )

    analysis_doc = {
        "incident_id": incident_id_str,
        "created_at": datetime.now(timezone.utc),
        "input_fingerprint": cache_key.split(":")[2],
        "xgboost": {
            "model_version": xgb_pred["model_version"],
            "predicted_category": pred_cat,
            "class_probabilities": xgb_pred["class_probabilities"],
            "feature_schema_version": xgb_pred["feature_schema_version"],
        },
        "minilm": {
            "model_id": MODEL_ID,
            "top_matches": top_matches,
        },
        "final_assessment": assessment,
        "actual_category": target_incident.get("category_label") if target_incident else None,
        "feedback": None,
        "is_synthetic": True,
    }

    # Persist in analysis_runs
    insert_res = await runs_col.insert_one(analysis_doc)
    analysis_doc["_id"] = str(insert_res.inserted_id)
    analysis_doc["cache_hit"] = False

    # Store in Redis Cache with TTL
    redis_service.cache_analysis(cache_key, analysis_doc, ttl_seconds=300)

    return analysis_doc


@router.post("/retrieve")
async def semantic_retrieval(payload: SemanticRetrievalRequest):
    """
    Retrieve semantically similar incidents and knowledge articles using MiniLM 384-dimensional embeddings.
    """
    kb_col = DatabaseManager.get_collection("knowledge_articles")
    inc_col = DatabaseManager.get_collection("incidents")

    # Fetch articles
    kb_filter: Dict[str, Any] = {}
    if payload.category:
        kb_filter["category"] = payload.category
    articles = await kb_col.find(kb_filter).to_list(50)

    # Fetch recent incidents
    inc_filter: Dict[str, Any] = {}
    if payload.category:
        inc_filter["category_label"] = payload.category
    if payload.service:
        inc_filter["service.name"] = payload.service
    incidents = await inc_col.find(inc_filter).limit(50).to_list(50)

    # Encode any incidents on the fly if not cached
    corpus = list(articles)
    for inc in incidents:
        emb = minilm_service.encode(f"{inc.get('title', '')} {inc.get('description', '')}")
        corpus.append({
            "id": inc.get("incident_key"),
            "title": inc.get("title"),
            "category": inc.get("category_label"),
            "match_type": "incident",
            "embedding": emb,
            "description": inc.get("description"),
        })

    matches = minilm_service.retrieve_top_matches(
        query_text=payload.query,
        corpus=corpus,
        top_k=payload.top_k,
    )

    return {
        "query": payload.query,
        "model_id": MODEL_ID,
        "dimension": 384,
        "matches_count": len(matches),
        "matches": matches,
    }


@router.get("/models")
async def list_models():
    """
    List model registry entries, active models, and evaluation metrics.
    """
    col = DatabaseManager.get_collection("model_registry")
    models = await col.find({}).sort("created_at", -1).to_list(50)
    for m in models:
        if "_id" in m:
            m["_id"] = str(m["_id"])
    return {
        "models": models,
        "active_xgboost_version": xgboost_service.version,
        "minilm_model_id": MODEL_ID,
        "feature_schema": xgboost_service.feature_names,
    }
