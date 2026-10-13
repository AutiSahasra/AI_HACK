import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.redis_service import redis_service


def test_redis_cache_key_generation_and_secret_redaction():
    features = {
        "cpu_usage_pct": 50.0,
        "password": "super_secret_db_password",  # must be redacted
        "auth_token": "bearer_12345",  # must be redacted
        "memory_usage_pct": 70.0,
    }
    key = redis_service.make_cache_key(features, model_version="1.0.0")
    assert key.startswith("rca:cache:")
    assert "super_secret_db_password" not in key
    assert "bearer_12345" not in key


def test_redis_cache_and_stream_workflow():
    test_key = "rca:cache:test_key_123:1.0:v1:v1"
    data = {"predicted_category": "database", "confidence": 0.95}

    # Store in cache
    assert redis_service.cache_analysis(test_key, data, ttl_seconds=60) is True
    # Retrieve from cache
    cached = redis_service.get_cached_analysis(test_key)
    assert cached is not None
    assert cached["predicted_category"] == "database"

    # Stream event publishing & reading
    event = {"service": "payments-api", "error": "pool_timeout"}
    eid = redis_service.publish_log_event(event)
    assert eid is not None
    events = redis_service.read_log_events(count=5)
    assert len(events) > 0


@pytest.mark.asyncio
async def test_ml_api_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Initialize Indexes
        init_res = await client.post("/api/ml/db/init-indexes")
        assert init_res.status_code == 200
        assert "indexes" in init_res.json()

        # 2. Generate Synthetic Dataset
        gen_res = await client.post("/api/ml/synthetic/generate", json={"count": 25, "seed": 42})
        assert gen_res.status_code == 200
        data = gen_res.json()
        assert data["counts"]["incidents"] == 25
        assert data["counts"]["log_events"] > 25

        # 3. Train XGBoost Model
        train_res = await client.post("/api/ml/xgboost/train", json={"test_size": 0.2, "random_state": 42})
        assert train_res.status_code == 200
        t_data = train_res.json()
        assert "macro_f1" in t_data["training_results"]["metrics"]

        # 4. Analyze Incident (with Redis Cache & MiniLM matches)
        analysis_res = await client.post(
            "/api/ml/analyze",
            json={
                "title": "PostgreSQL connection timeout",
                "description": "Database pool saturated",
                "metrics": {
                    "cpu_usage_pct": 35.0,
                    "memory_usage_pct": 50.0,
                    "error_count_1m": 25,
                    "db_timeout_count_1m": 20,
                    "response_time_ms": 3500.0,
                    "connection_pool_usage_pct": 98.0,
                },
            },
        )
        assert analysis_res.status_code == 200
        a_data = analysis_res.json()
        assert a_data["xgboost"]["predicted_category"] == "database"
        assert len(a_data["minilm"]["top_matches"]) > 0

        # Second call hits cache
        cached_analysis_res = await client.post(
            "/api/ml/analyze",
            json={
                "title": "PostgreSQL connection timeout",
                "description": "Database pool saturated",
                "metrics": {
                    "cpu_usage_pct": 35.0,
                    "memory_usage_pct": 50.0,
                    "error_count_1m": 25,
                    "db_timeout_count_1m": 20,
                    "response_time_ms": 3500.0,
                    "connection_pool_usage_pct": 98.0,
                },
            },
        )
        assert cached_analysis_res.status_code == 200
        assert cached_analysis_res.json().get("cache_hit") is True

        # 5. Semantic Retrieval
        ret_res = await client.post(
            "/api/ml/retrieve",
            json={"query": "database connection pool timeout", "top_k": 3},
        )
        assert ret_res.status_code == 200
        r_data = ret_res.json()
        assert r_data["dimension"] == 384
        assert len(r_data["matches"]) > 0

        # 6. List Model Registry
        models_res = await client.get("/api/ml/models")
        assert models_res.status_code == 200
        m_data = models_res.json()
        assert len(m_data["models"]) > 0
        assert len(m_data["feature_schema"]) == 7
