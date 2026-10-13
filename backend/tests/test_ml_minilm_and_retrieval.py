import pytest
import math
from app.services.minilm_service import minilm_service, MODEL_ID


def test_minilm_vector_dimension_and_normalization():
    vec = minilm_service.encode("PostgreSQL database connection pool exhaustion timeout")
    assert len(vec) == 384
    # Vector should be unit-normalized (L2 norm approx 1.0)
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 0.01


def test_cosine_similarity_identity_and_orthogonality():
    v1 = [1.0, 0.0] + [0.0] * 382
    v2 = [1.0, 0.0] + [0.0] * 382
    v3 = [0.0, 1.0] + [0.0] * 382

    # Identity similarity = 1.0
    assert abs(minilm_service.cosine_similarity(v1, v2) - 1.0) < 1e-4
    # Orthogonal vectors = 0.0
    assert abs(minilm_service.cosine_similarity(v1, v3) - 0.0) < 1e-4


def test_semantic_retrieval_ranking():
    corpus = [
        {
            "id": "KB-DB",
            "title": "PostgreSQL Connection Pool Tuning",
            "category": "database",
            "content": "Database pool connections timing out and query lock contention",
            "embedding": minilm_service.encode("PostgreSQL database connection pool timeout and query lock contention"),
        },
        {
            "id": "KB-MEM",
            "title": "Java Heap Out of Memory OOM",
            "category": "memory",
            "content": "JVM garbage collection pauses and memory leak heap saturation",
            "embedding": minilm_service.encode("JVM garbage collection pauses and memory leak heap saturation"),
        },
        {
            "id": "KB-NET",
            "title": "DNS Latency and Socket Timeouts",
            "category": "network",
            "content": "TCP connection reset and DNS lookup failures",
            "embedding": minilm_service.encode("TCP connection reset and DNS lookup failures"),
        },
    ]

    # Query for database
    matches = minilm_service.retrieve_top_matches(
        query_text="database connection pool timeout during checkout",
        corpus=corpus,
        top_k=2,
    )
    assert len(matches) > 0
    # Top match should be KB-DB
    assert matches[0]["id"] == "KB-DB"
    assert matches[0]["category"] == "database"
    assert matches[0]["similarity_score"] > 0.3
