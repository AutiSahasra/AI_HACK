import pytest
import numpy as np
from app.services.xgboost_service import (
    XGBoostIncidentClassifier,
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    KNOWN_CLASSES,
)
from app.services.synthetic_generator import generate_synthetic_dataset


def test_feature_extraction_order_and_nan_preservation():
    classifier = XGBoostIncidentClassifier(model_dir="ml_artifacts")
    assert classifier.feature_names == FEATURE_NAMES
    assert len(classifier.feature_names) == 7

    # Metric dict with missing values
    metrics = {
        "cpu_usage_pct": 88.5,
        "memory_usage_pct": 45.0,
        "db_timeout_count_1m": None,  # Must be preserved as NaN
        "error_count_1m": 12,
    }

    vec = classifier.extract_features(metrics)
    assert len(vec) == 7
    assert vec[0] == 88.5
    assert vec[1] == 45.0
    assert np.isnan(vec[3])  # db_timeout_count_1m is NaN, NOT 0.0


def test_xgboost_train_evaluate_and_inference():
    classifier = XGBoostIncidentClassifier(model_dir="ml_artifacts")
    incidents, _, _ = generate_synthetic_dataset(count=80, seed=42)

    results = classifier.train_and_evaluate(training_records=incidents, test_size=0.25, random_state=42)
    assert "macro_f1" in results["metrics"]
    assert results["metrics"]["macro_f1"] > 0.60
    assert results["feature_schema_version"] == FEATURE_SCHEMA_VERSION

    # Test inference output parity
    test_metrics = {
        "cpu_usage_pct": 40.0,
        "memory_usage_pct": 50.0,
        "error_count_1m": 45,
        "db_timeout_count_1m": 30,
        "response_time_ms": 4000.0,
        "network_error_count_1m": 2,
        "connection_pool_usage_pct": 95.0,
    }
    pred = classifier.predict(test_metrics)
    assert "predicted_category" in pred
    assert pred["predicted_category"] == "database"
    assert "class_probabilities" in pred
    assert len(pred["class_probabilities"]) == len(KNOWN_CLASSES)
    # Probabilities should sum to approximately 1.0
    total_prob = sum(pred["class_probabilities"].values())
    assert abs(total_prob - 1.0) < 0.05
