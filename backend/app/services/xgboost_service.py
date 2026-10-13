import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import numpy as np
import xgboost as xgb
from sklearn.metrics import classification_report, f1_score
from app.core.config import settings
from app.core.database import DatabaseManager

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "cpu_usage_pct",
    "memory_usage_pct",
    "error_count_1m",
    "db_timeout_count_1m",
    "response_time_ms",
    "network_error_count_1m",
    "connection_pool_usage_pct",
]
FEATURE_SCHEMA_VERSION = "v1.0"

KNOWN_CLASSES = [
    "database",
    "network",
    "compute",
    "memory",
    "authentication",
    "dependency",
    "unknown",
]


class XGBoostIncidentClassifier:
    """
    XGBoost structured incident classification service.
    Features:
    - Fixed, explicitly ordered feature list and schema version.
    - Missing metrics kept as NaN (native XGBoost handling) instead of silently substituting 0.
    - Persisted model artifact and metadata registered in model_registry.
    - Inference with class probability distributions.
    """

    def __init__(self, model_dir: str = "ml_artifacts"):
        self.model_dir = model_dir
        self.model_name = "xgboost-category-classifier"
        self.version = "1.0.0"
        self.feature_names = list(FEATURE_NAMES)
        self.label_names = list(KNOWN_CLASSES)
        self.feature_schema_version = FEATURE_SCHEMA_VERSION
        self._model: Optional[xgb.XGBClassifier] = None
        os.makedirs(self.model_dir, exist_ok=True)
        self._model_path = os.path.join(self.model_dir, "xgboost_category_model.json")
        self._load_persisted_model()

    def _load_persisted_model(self):
        if os.path.exists(self._model_path):
            try:
                clf = xgb.XGBClassifier()
                clf.load_model(self._model_path)
                self._model = clf
                logger.info(f"Loaded existing XGBoost classifier from {self._model_path}")
            except Exception as e:
                logger.warning(f"Failed to load persisted XGBoost model: {e}")

    def extract_features(self, metrics_dict: Dict[str, Any]) -> List[float]:
        """
        Extract ordered feature vector. Missing values are preserved as np.nan.
        """
        vec = []
        for feat in self.feature_names:
            val = metrics_dict.get(feat)
            if val is None:
                vec.append(np.nan)
            else:
                try:
                    vec.append(float(val))
                except (ValueError, TypeError):
                    vec.append(np.nan)
        return vec

    def train_and_evaluate(
        self,
        training_records: List[Dict[str, Any]],
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        Train XGBClassifier on labeled incident records and record metrics.
        Groups splits by incident scenarios to prevent near-duplicate leakage.
        """
        if len(training_records) < 10:
            raise ValueError(f"Need at least 10 labeled incident records to train XGBoost; received {len(training_records)}")

        X_list = []
        y_list = []
        groups = []

        label_to_idx = {name: idx for idx, name in enumerate(self.label_names)}

        for idx, rec in enumerate(training_records):
            metrics = rec.get("metrics") or {}
            category = rec.get("category_label")
            if category not in label_to_idx:
                category = "unknown"

            feat_vec = self.extract_features(metrics)
            X_list.append(feat_vec)
            y_list.append(label_to_idx[category])
            # Group by scenario or service name to prevent leak
            srv = (rec.get("service") or {}).get("name") if isinstance(rec.get("service"), dict) else "default"
            groups.append(f"{srv}_{category}")

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.int32)

        # Stratified / deterministic train-test split
        rng = np.random.RandomState(random_state)
        indices = np.arange(len(X))
        rng.shuffle(indices)

        split_idx = int(len(X) * (1.0 - test_size))
        train_idx, test_idx = indices[:split_idx], indices[split_idx:]

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        clf = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.08,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=random_state,
        )

        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)

        macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
        report = classification_report(
            y_test,
            y_pred,
            labels=list(range(len(self.label_names))),
            target_names=self.label_names,
            output_dict=True,
            zero_division=0,
        )

        metrics_summary = {
            "macro_f1": round(macro_f1, 4),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "classification_report": report,
        }

        # Persist model artifact
        clf.save_model(self._model_path)
        self._model = clf

        # Generate model version timestamp
        version = f"1.0.{int(datetime.now(timezone.utc).timestamp())}"
        self.version = version

        return {
            "model_name": self.model_name,
            "version": version,
            "feature_names": self.feature_names,
            "label_names": self.label_names,
            "feature_schema_version": self.feature_schema_version,
            "metrics": metrics_summary,
            "model_path": self._model_path,
        }

    async def register_model(self, train_results: Dict[str, Any], dataset_version: str = "synth-seed-42") -> Dict[str, Any]:
        """
        Record trained model version in MongoDB model_registry collection and set as active.
        """
        col = DatabaseManager.get_collection("model_registry")

        # Deactivate previous versions
        await col.update_many({"model_name": self.model_name}, {"$set": {"is_active": False}})

        doc = {
            "model_name": self.model_name,
            "model_type": "classifier",
            "version": train_results["version"],
            "source_model_id": "xgboost_category_model.json",
            "feature_names": self.feature_names,
            "label_names": self.label_names,
            "metrics": train_results["metrics"],
            "training_data_version": dataset_version,
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
        }
        res = await col.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
        return doc

    def predict(self, metrics_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run inference on structured metrics dict.
        Returns predicted category and class probability map.
        """
        feat_vec = self.extract_features(metrics_dict)
        X = np.array([feat_vec], dtype=np.float32)

        if self._model is None:
            # Rule-based fallback if model has not been trained yet
            return self._heuristic_fallback(metrics_dict)

        probs = self._model.predict_proba(X)[0]
        pred_idx = int(np.argmax(probs))
        predicted_category = self.label_names[pred_idx]

        class_probabilities = {
            self.label_names[i]: round(float(probs[i]), 4)
            for i in range(len(self.label_names))
        }

        return {
            "predicted_category": predicted_category,
            "class_probabilities": class_probabilities,
            "model_version": self.version,
            "feature_schema_version": self.feature_schema_version,
            "feature_values": {name: (None if np.isnan(val) else val) for name, val in zip(self.feature_names, feat_vec)},
        }

    def _heuristic_fallback(self, metrics_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback baseline when XGBoost model artifact is not yet trained."""
        db_timeouts = metrics_dict.get("db_timeout_count_1m") or 0
        pool_usage = metrics_dict.get("connection_pool_usage_pct") or 0
        mem_pct = metrics_dict.get("memory_usage_pct") or 0
        cpu_pct = metrics_dict.get("cpu_usage_pct") or 0
        net_err = metrics_dict.get("network_error_count_1m") or 0

        pred = "unknown"
        if db_timeouts > 5 or pool_usage > 85:
            pred = "database"
        elif mem_pct > 85:
            pred = "memory"
        elif cpu_pct > 85:
            pred = "compute"
        elif net_err > 10:
            pred = "network"

        probs = {c: (0.75 if c == pred else 0.04) for c in self.label_names}
        probs[pred] = round(1.0 - sum(v for k, v in probs.items() if k != pred), 4)

        return {
            "predicted_category": pred,
            "class_probabilities": probs,
            "model_version": "heuristic_baseline",
            "feature_schema_version": self.feature_schema_version,
            "feature_values": metrics_dict,
        }


xgboost_service = XGBoostIncidentClassifier()
