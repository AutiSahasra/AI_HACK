# MongoDB Schema Specification & ML Copilot Architecture

Implementation-ready documentation for the **AI Root Cause Analysis & Intelligent Ticket Resolution Copilot**, implementing the full MongoDB schema specification, MiniLM semantic embeddings, XGBoost classification, and Redis operational caching/streaming.

---

## 1. Application Stack & ML Architecture

| Layer | Component | Specification |
|---|---|---|
| **Durable Store** | MongoDB | Primary source of truth for incidents, normalized logs, runbooks, and model metadata. |
| **Operational Caching / Stream** | Redis | Transient caching of inference predictions (`TTL=300s`) and log event streams (`stream:log_events`). Graceful fallback if offline. |
| **Semantic Embedding** | MiniLM | `sentence-transformers/all-MiniLM-L6-v2` producing 384-dimensional normalized vectors ($L_2=1.0$) with in-Python Cosine Similarity. |
| **Structured Classifier** | XGBoost | Multi-class tree booster classifying incidents into 7 categories using 7 strictly ordered metrics with native `NaN` missing-value handling. |
| **Backend API** | FastAPI | Python 3.11+ async REST API with Pydantic validation and RBAC guards. |
| **Frontend UI** | React + Vite | Clean 2-tier dashboard (Support Engineer & Senior Approver). |

---

## 2. Recommended Database Collections & Schemas

### 1. `incidents`
Stores grouped incident cases, labels, symptoms, telemetry metrics, and verified root causes.
- `_id`: ObjectId primary key.
- `incident_key`: Human-readable unique key (e.g. `INC-000001`); unique index.
- `title`: Short incident summary.
- `description`: Narrative context (redacted secrets).
- `service`: Sub-document containing `name` and `environment` (`development`, `staging`, `production`, `synthetic`).
- `severity`: `low`, `medium`, `high`, `critical`.
- `status`: `open`, `investigating`, `mitigated`, `resolved`, `closed`.
- `category_label`: Target label for XGBoost (`database`, `network`, `compute`, `memory`, `authentication`, `dependency`, `unknown`).
- `root_cause`: Sub-document containing `label`, `explanation`, and `confirmation_status` (`synthetic_ground_truth`, `confirmed`, `suspected`, `unconfirmed`).
- `metrics`:
  - `cpu_usage_pct`: $0.0 - 100.0$ or `null`.
  - `memory_usage_pct`: $0.0 - 100.0$ or `null`.
  - `error_count_1m`: $\ge 0$ integer count or `null`.
  - `db_timeout_count_1m`: $\ge 0$ integer count or `null`.
  - `response_time_ms`: $\ge 0.0$ milliseconds or `null`.
  - `network_error_count_1m`: $\ge 0$ integer count or `null`.
  - `connection_pool_usage_pct`: $0.0 - 100.0$ or `null`.
- `symptoms`: Array of observed symptom strings.
- `resolution`: Sub-document containing `summary`, `actions` array, and `verified` boolean flag.
- `source`: `synthetic`, `application`, `monitoring`, `manual`.
- `is_synthetic`: Boolean flag (true for generated data).
- `label_source`: `synthetic_rule`, `human_verified`, `imported_verified`, `unknown`.
- `created_at`, `updated_at`, `resolved_at`: UTC timestamps.

### 2. `log_events`
Individual structured log events linked to incidents.
- `_id`: ObjectId primary key.
- `event_id`: Unique collector event identifier.
- `incident_id`: Reference to `incidents.incident_key` once grouped.
- `timestamp`: UTC event timestamp.
- `service_name`: Source microservice name.
- `environment`: `development`, `staging`, `production`, `synthetic`.
- `level`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- `message`: Redacted log message.
- `error_type`: Exception class (e.g. `DatabaseException`).
- `request_id`: Tracing correlation identifier.
- `metrics_snapshot`: Telemetry metrics at event time.
- `fingerprint`: Stable hash of normalized message/service to deduplicate alerts.
- `embedding`: 384-dimensional MiniLM float vector.
- `embedding_model`: `sentence-transformers/all-MiniLM-L6-v2`.
- `is_synthetic`: Boolean flag.
- `created_at`: Ingestion UTC timestamp.

### 3. `knowledge_articles`
Curated troubleshooting runbooks and guides with MiniLM semantic vectors.
- `_id`: ObjectId primary key.
- `article_id`: Unique stable article ID (e.g. `KB-DB-001`).
- `title`: Runbook title.
- `content`: Guidance text for semantic search.
- `category`: Category label matching XGBoost taxonomy.
- `service_names`: List of applicable microservices.
- `resolution_steps`: Ordered recovery actions.
- `embedding`: 384-dimensional MiniLM vector.
- `embedding_model`: `sentence-transformers/all-MiniLM-L6-v2`.
- `content_version`: Integer incremented on text edits to trigger re-embedding.
- `verified`: Boolean review flag.
- `source`: `synthetic`, `internal_runbook`, `manually_authored`.
- `created_at`, `updated_at`: UTC timestamps.

### 4. `analysis_runs`
Diagnostic record produced for each incident evaluation.
- `_id`: ObjectId primary key.
- `incident_id`: Associated incident identifier.
- `created_at`: Evaluation UTC timestamp.
- `input_fingerprint`: Hash of normalized telemetry input features.
- `xgboost`: Object containing `model_version`, `predicted_category`, `class_probabilities`, and `feature_schema_version`.
- `minilm`: Object containing `model_id` and `top_matches` (article IDs and similarity scores).
- `final_assessment`: Template-based summary avoiding ungrounded certainty claims.
- `actual_category`: Confirmed category after engineer verification.
- `feedback`: Reviewer notes and accuracy tags.
- `is_synthetic`: Boolean flag.

### 5. `model_registry`
Auditable metadata tracking ML versions and evaluation benchmarks.
- `_id`: ObjectId primary key.
- `model_name`: e.g. `xgboost-category-classifier` or `minilm-incident-embeddings`.
- `model_type`: `classifier` or `embedding`.
- `version`: Version identifier (e.g. `1.0.1791875755`).
- `source_model_id`: Model artifact filename or Hugging Face repository ID.
- `feature_names`: Strictly ordered list of 7 input features.
- `label_names`: Taxonomy of 7 known target categories.
- `metrics`: Evaluation results (Macro-F1, per-class precision/recall, sample counts).
- `training_data_version`: Dataset identifier / generation seed.
- `created_at`: UTC registration timestamp.
- `is_active`: Boolean flag indicating active production model.

---

## 3. Database Indexes

| Collection | Indexes Configured |
|---|---|
| `incidents` | Unique index on `incident_key`<br>Single field indexes on `status`, `severity`, `category_label`, `service.name`, `created_at`, `is_synthetic` |
| `log_events` | Unique index on `event_id`<br>Indexes on `timestamp`, compound `(service_name, timestamp)`, `incident_id`, `fingerprint` |
| `knowledge_articles` | Unique index on `article_id`<br>Indexes on `category`, `verified` |
| `analysis_runs` | Compound index on `(incident_id, created_at)`<br>Index on `xgboost.predicted_category` |
| `model_registry` | Unique compound index on `(model_name, version)`<br>Index on `is_active` |

---

## 4. MiniLM & XGBoost Pipeline Specifications

### MiniLM 384-Dimensional Embedding Service
- Generates 384-dimensional unit vectors with $L_2$ norm $= 1.0$.
- In-memory Cosine Similarity for fast retrieval without external vector DB dependencies:
  $$\text{CosineSimilarity}(\mathbf{u}, \mathbf{v}) = \sum_{i=1}^{384} u_i \cdot v_i$$
- Embedded across incident descriptions and knowledge article content.

### XGBoost Classifier Feature Schema (`v1.0`)
Strictly ordered list of 7 numeric telemetry features:
1. `cpu_usage_pct`
2. `memory_usage_pct`
3. `error_count_1m`
4. `db_timeout_count_1m`
5. `response_time_ms`
6. `network_error_count_1m`
7. `connection_pool_usage_pct`

> **Missing Value Policy**: Missing metrics are mapped to `np.nan` rather than silently replaced with 0. XGBoost natively evaluates split directions for missing values.

---

## 5. CLI Commands

### 1. Initialize MongoDB Collections & Indexes
```powershell
.\.venv\Scripts\python.exe backend/scripts/init_db.py
```

### 2. Generate Deterministic Synthetic Dataset (Seed 42)
Generates 350 coherent incidents across all 7 categories with correlated log events and knowledge articles:
```powershell
.\.venv\Scripts\python.exe backend/scripts/generate_synthetic.py --count 350 --seed 42
```

### 3. Train & Evaluate XGBoost Classifier
Trains on synthetic data, performs train/test split, calculates Macro-F1 and per-class precision/recall, and registers the active model in `model_registry`:
```powershell
.\.venv\Scripts\python.exe backend/scripts/train_xgboost.py
```

### 4. Semantic Similarity Retrieval Demo
Queries knowledge articles and past incidents using 384-dimensional MiniLM embeddings:
```powershell
.\.venv\Scripts\python.exe backend/scripts/semantic_query.py --query "database connection pool exhausted during high load" --top_k 3
```

### 5. Run Test Suite
Run the 16 ML unit and integration tests:
```powershell
.\.venv\Scripts\pytest -q backend/tests/test_ml_schemas_and_validation.py backend/tests/test_ml_synthetic_and_indexes.py backend/tests/test_ml_minilm_and_retrieval.py backend/tests/test_ml_xgboost_pipeline.py backend/tests/test_ml_redis_and_api.py
```

Run the entire system test suite (50 tests):
```powershell
.\.venv\Scripts\pytest -q
```

---

## 6. REST API Endpoints

- `POST /api/ml/db/init-indexes`: Idempotently initialize all 5 collection indexes.
- `POST /api/ml/synthetic/generate`: Trigger synthetic dataset generation (`count`, `seed`).
- `POST /api/ml/xgboost/train`: Trigger XGBoost training, evaluation, and registry recording.
- `POST /api/ml/analyze`: Full Copilot diagnostic run with Redis caching, XGBoost prediction, and MiniLM semantic runbook matching.
- `POST /api/ml/retrieve`: Query semantically similar runbooks and incidents by freeform symptom description.
- `GET /api/ml/models`: View registered models and active evaluation metrics.
