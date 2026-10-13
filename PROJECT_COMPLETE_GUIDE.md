# AI Root Cause Analysis & Intelligent Ticket Resolution Copilot
## Comprehensive Project Documentation & Architecture Guide

---

### Executive Summary

The **AI Root Cause Analysis & Intelligent Ticket Resolution Copilot** is an enterprise-grade site reliability and incident management platform. Modern cloud microservices emit millions of log lines daily. When outages occur, engineers suffer from **alert fatigue**, waste hours sifting through noisy logs, and risk taking dangerous unverified actions in production.

This platform automates the entire incident lifecycle:
1. **Ingests** live streaming microservice logs and manual historical dumps (CSV, JSON, JSONL, Syslog, Raw).
2. **Normalizes, stacks multi-line exceptions, and redacts sensitive data** (PII, credentials, bearer tokens).
3. **Deduplicates & groups** recurring error bursts into cohesive, actionable **Incidents** via deterministic template fingerprinting and rolling anomaly detection.
4. **Retrieves approved runbooks and past resolutions** from a vector/text knowledge base.
5. **Generates Grounded Root Cause Analysis (RCA)** using AI with strict anti-hallucination verification (enforcing strict separation between *Observed Facts* from actual logs vs. *AI Hypotheses*).
6. **Enforces Dual-Gated Remediation Governance**: Support Engineers propose allow-listed fixes, Senior Managers approve high-risk remediations, and the system automatically runs post-execution health verification before closing tickets.
7. **Maintains an immutable, append-only audit trail** for total compliance and post-mortem evaluation.

---

## 1. End-to-End Architectural Workflow

The platform operates through an automated 11-step pipeline connecting the fault generator, collectors, backend engines, and frontend dashboard:

```
+--------------------------------------------------------------------------------------------------+
|                                      THE 11-STEP WORKFLOW                                        |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
| [1] Microservice Emits Logs & Faults (Demo App: /checkout, /pay, /orders)                        |
|                                     │                                                            |
|                                     ▼                                                            |
| [2] Live Log Tailer & Forwarder (Collector Daemon: collector/tailer.py)                          |
|                                     │                                                            |
|                                     ▼                                                            |
| [3] Ingestion & Multi-line Stacking (/api/ingest & /api/uploads)                                 |
|                                     │                                                            |
|                                     ▼                                                            |
| [4] Schema Normalization & Sensitive Data Redaction (Tokens, Passwords, PII masked)               |
|                                     │                                                            |
|                                     ▼                                                            |
| [5] Deterministic Template Fingerprinting (Variable extraction -> Stable Hash)                   |
|                                     │                                                            |
|                                     ▼                                                            |
| [6] Anomaly Detection, Rule Evaluation & Deduplication Grouping (Incident Created)               |
|                                     │                                                            |
|                                     ▼                                                            |
| [7] Historical Runbook Retrieval & Grounded AI RCA (Facts vs Hypotheses)                         |
|                                     │                                                            |
|                                     ▼                                                            |
| [8] Ticketing & Priority Assignment (P1-P4 assigned, blast radius computed)                      |
|                                     │                                                            |
|                                     ▼                                                            |
| [9] Dual-Gated Governance: Support Requests -> Senior Manager Approves                           |
|                                     │                                                            |
|                                     ▼                                                            |
| [10] Safe Allow-listed Action Execution + Automated Recovery Health Checks                       |
|                                     │                                                            |
|                                     ▼                                                            |
| [11] Immutable Audit Logging & Analytics Dashboard                                               |
+--------------------------------------------------------------------------------------------------+
```

---

### Step-by-Step Breakdown

#### Step 1: Log Emission & Fault Generation (Demo App)
- **What happens**: A simulated e-commerce microservice suite runs endpoints representing checkout, payment gateway, inventory management, and database connections. Faults can be triggered automatically or manually (e.g., connection pool exhaustion, memory exhaustion, third-party gateway timeouts, syntax configuration errors).
- **Technology used**:
  - **Framework**: Python 3.13, FastAPI, Uvicorn (Port 8001).
  - **Logging**: Python `logging` module writing structured JSON and unstructured raw logs to disk (`demo-app/app.log`).

#### Step 2: Live Log Collection & Streaming (Collector Daemon)
- **What happens**: The collector daemon continuously tails active log files without blocking the application. It buffers newly written log lines, detects multi-line boundaries, batches log events, and forwards them over HTTP POST to the backend.
- **Technology used**:
  - **Language**: Python 3.13 (`collector/tailer.py`).
  - **Networking**: `httpx` asynchronous HTTP client with API Key authentication (`X-API-Key`).
  - **Resilience**: Exponential backoff reconnects and local buffer queues during backend downtime.

#### Step 3: Multi-Format Ingestion & Multi-line Stack Trace Stacking
- **What happens**: The ingestion API accepts both real-time stream batches (`/api/ingest`) and manual bulk file uploads (`/api/uploads`) supporting:
  - CSV files (with automatic header mapping).
  - JSON arrays and NDJSON / JSON Lines.
  - Linux Syslog and Apache/Nginx web server logs.
  - Raw application logs with complex multi-line Python / Java stack traces.
- When an exception starts with `Traceback (most recent call last):` or `Exception in thread...`, the stack accumulator binds all indented lines into a single coherent event rather than treating each line as a disconnected log.
- **Technology used**:
  - **API**: FastAPI asynchronous route handlers.
  - **Parsing**: Custom regular-expression state machine for stack trace reassembly.

#### Step 4: Schema Normalization & Sensitive Data Redaction
- **What happens**: Every log line is converted into a unified Pydantic `LogEvent` schema. Before database storage, the Redaction Service inspects the message and metadata for sensitive information:
  - Bearer tokens, JWTs, API keys (`X-API-Key: *****`).
  - Passwords and secret parameters (`password=*****`).
  - PII (Email addresses, credit card numbers, IPv4/IPv6 private ranges).
- **Technology used**:
  - **Model**: Pydantic v2 schemas.
  - **Security**: Regex redaction filter preventing secret leakage into database records or LLM prompts.

#### Step 5: Deterministic Template Fingerprinting
- **What happens**: Microservices frequently emit thousands of instances of the same error with minor variable variations (different User IDs, Order IDs, Timestamps, or IP addresses). The Fingerprint Service strips these dynamic tokens and extracts the underlying syntactic code template, computing an immutable MD5/SHA-256 fingerprint (e.g., `ERR_CONN_POOL_TIMEOUT`).
- **Technology used**:
  - **Hashing**: SHA-256 template hashing.
  - **Normalization**: Regex variable extraction.

#### Step 6: Anomaly Detection, Rule Evaluation & Incident Grouping
- **What happens**:
  - **Rule-based Detection**: Evaluates detection rules (e.g., more than 5 `CRITICAL` logs in 2 minutes).
  - **Statistical Anomaly Detection**: Maintains rolling Z-score error rate statistics to flag sudden abnormal volume surges.
  - **Deduplication & Grouping**: Correlates events sharing `(service_name, fingerprint, temporal_window)` into a single parent `Incident` record. Instead of triggering 500 alerts, engineers see **1 Incident** containing 500 correlated occurrences.
- **Technology used**:
  - **Math/Stats**: Rolling window statistical algorithms.
  - **Database**: MongoDB compound indices on `(service, fingerprint, createdAt)`.

#### Step 7: Historical Runbook Retrieval & Grounded AI RCA
- **What happens**:
  - **Retrieval**: The system queries the `knowledge_articles` and `historicalIncidents` collections for past resolved tickets with matching error patterns or service names.
  - **Prompt Construction**: Grounded context is assembled containing:
    1. Sample representative error logs and stack traces.
    2. Past incident resolutions and approved remediation runbooks.
    3. Structural schema instructions.
  - **Inference**: The LLM analyzes the incident and outputs:
    - Root cause summary.
    - **Observed Facts** (verifiable items directly quoted from ingested logs).
    - **AI Inferences** (hypotheses about system behavior, clearly demarcated).
    - Recommended remediations with risk assessment (Low, Medium, High, Critical).
  - **Anti-Hallucination Guardrails**: The backend verifies that citations match actual ingested log IDs before saving the RCA analysis run.
- **Technology used**:
  - **LLMs**: Anthropic Claude / OpenAI / Serverless free-tier HuggingFace API / Deterministic Mock Fallback.
  - **Validation**: Pydantic v2 JSON schema enforcement.

#### Step 8: Ticketing & Priority Assignment
- **What happens**: The system creates or links a Ticket for the incident:
  - Assigns priority tiers **P1 (Critical)**, **P2 (High)**, **P3 (Medium)**, or **P4 (Low)** based on service criticality, error frequency, and blast radius.
  - Calculates impact scores and populates the Support Engineer Kanban / Table view.
- **Technology used**:
  - **Data Store**: MongoDB `tickets` collection.
  - **Frontend**: React Tickets Board with instant search, priority filtering, and status grouping.

#### Step 9: Dual-Gated Remediation & Role-Based Governance (RBAC)
- **What happens**:
  - **Support Engineer Role**: Reviews the AI root cause analysis and recommendations. Selects an action from an **allow-listed catalog** (e.g., `restart_demo_service`, `clear_demo_cache`, `rollback_demo_config`). Arbitrary shell commands are strictly prohibited.
  - **Risk Assessment**:
    - **Low Risk Actions**: Can be executed directly by Support Engineers if auto-approval policies permit.
    - **High / Critical Risk Actions**: Support Engineer submits an approval request detailing the proposed fix and justification.
  - **Senior Manager / Approver Role**: Receives the request in the dedicated **Approvals Queue**. Reviews the blast radius and risk summary, then clicks **Approve** or **Reject** with mandatory notes.
  - Once approved, the Support Engineer receives notification and executes the remediation.
- **Technology used**:
  - **Authentication**: JWT (JSON Web Tokens) with cryptographically signed payloads.
  - **Authorization**: Backend RBAC middleware enforcing roles (`viewer`, `support`, `approver`, `admin`).

#### Step 10: Safe Action Execution & Automated Health Verification
- **What happens**:
  - When the user triggers an approved action, the backend invokes the target microservice admin endpoint (`POST /admin/actions/execute`).
  - **Automated Health Verification**: The system does NOT blindly mark the ticket resolved. Instead, it runs an automated post-remediation verification routine:
    1. Probes the microservice health endpoint (`GET http://localhost:8001/health`).
    2. Observes a 5-second log quiet period to confirm no new error bursts occur.
  - If health passes: Incident and Ticket state change to `RESOLVED`.
  - If health fails: Escalates to human reviewer and logs the failure.
- **Technology used**:
  - **HTTP Verification**: Asynchronous health probe retry loop.
  - **Database**: Atomic MongoDB state transition updates.

#### Step 11: Immutable Audit Trail & Analytics Dashboard
- **What happens**:
  - Every state change, approval, rejection, log upload, and remediation is recorded to an append-only `audit_logs` collection.
  - The Frontend Dashboard renders real-time KPI metrics: Total Incidents, Active Alerts, MTTR (Mean Time to Resolution), Service Health, Error Rate Spikes, and Severity Breakdown.
- **Technology used**:
  - **UI/UX**: React 18, Vite, Vanilla CSS design tokens based on the modern Paolo minimalist aesthetic.
  - **Audit Storage**: MongoDB append-only collection.

---

## 2. Technology Stack Matrix

| Tier | Component | Technology / Library | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend** | Framework | **React 18** | Modular UI component architecture |
| | Build Tool | **Vite 5** | High-performance bundling and Fast HMR |
| | Language | **TypeScript** | Strict compile-time type safety |
| | Styling | **Vanilla CSS Tokens** | Paolo-inspired clean off-white design system |
| | Icons | **Lucide React** | Modern, lightweight iconography |
| | Routing | **React Router DOM v6** | Client-side routing with RBAC Protected Routes |
| **Backend** | API Engine | **FastAPI (Python 3.13)** | Asynchronous high-throughput REST API |
| | ASGI Server | **Uvicorn** | Fast ASGI web server |
| | Validation | **Pydantic v2** | Strict schema validation and JSON serialization |
| | Database Client | **Motor / PyMongo** | Asynchronous non-blocking MongoDB driver |
| | Security | **PyJWT + bcrypt** | Secure hashing and token-based RBAC |
| | HTTP Client | **HTTPX** | Asynchronous outbound HTTP for LLMs & health checks |
| **Data Layer** | Primary Database | **MongoDB** | Document store for logs, incidents, tickets, audits |
| **Caching & Queue** | In-Memory Engine | **Redis** | Sub-millisecond analysis caching & event streaming |
| **ML Classification**| Gradient Boosting | **XGBoost** | Structured metrics category classification |
| **Embeddings** | Dense Vector Model | **all-MiniLM-L6-v2** | 384-dimensional semantic search & runbook retrieval |
| **Streamer** | Log Tailer | **Python Custom Tailer** | Non-blocking file watcher with buffer batching |
| **Demo App** | Fault Generator | **FastAPI Microservice** | Microservice simulating live traffic & outages |
| **AI Copilot** | LLM Engine | **Anthropic / OpenAI / HF / Mock** | Grounded RAG root cause analysis & evidence validation |

---

## 3. Deep Dive: How Redis, MiniLM, XGBoost & RAG are Used

### 1. Redis (Operational Caching & Event Streaming)
- **Primary Role**: High-speed transient memory boundary preventing redundant ML recalculations and streaming incoming log events to background workers.
- **Where it lives**: `backend/app/services/redis_service.py` (`RedisOperationalService`).
- **Core Mechanisms**:
  1. **Deterministic Feature Cache Keys**: Computes a SHA-256 hash of normalized incident features, XGBoost model version, and rules version:
     `rca:cache:{fp_16}:{model_version}:{rules_version}:{context_version}`
  2. **Sub-Millisecond Inference Retrieval**: When multiple engineers open the same incident, Redis returns the cached ML prediction in `< 2ms` with `cache_hit: true`.
  3. **TTL (Time-To-Live)**: Analysis results expire automatically after 300 seconds (5 minutes) ensuring new metrics trigger fresh re-evaluations.
  4. **Log Event Streaming**: Uses Redis Streams (`XADD`, `XREVRANGE`) to push real-time events (`stream:log_events`) to asynchronous consumers.
  5. **Zero-Secret Guarantee**: Before writing to Redis, keys and payloads are stripped of credentials, tokens, and authorization headers.
  6. **Transparent In-Memory Fallback**: If Redis daemon is not reachable, the service gracefully switches to an in-memory dictionary queue and cache without crashing.

---

### 2. MiniLM (384-Dimensional Semantic Search & Embeddings)
- **Primary Role**: Dense vector embedding model (`sentence-transformers/all-MiniLM-L6-v2`) powering semantic similarity search across knowledge base articles and historical incident resolutions.
- **Where it lives**: `backend/app/services/minilm_service.py` (`MiniLMEmbeddingService`).
- **Core Mechanisms**:
  1. **384-Dimensional Vectors**: Transforms error messages, incident descriptions, and runbook content into 384-dimensional unit-normalized float arrays ($L2\text{ norm} = 1.0$).
  2. **In-Python Cosine Similarity**: Measures similarity using normalized dot products:
     $$\text{Cosine Similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$
  3. **Top-k Runbook Retrieval**: Retrieves the top-3 to top-5 most relevant runbooks, even when the exact error wording differs (e.g., `"connection pool exhausted"` correctly matches `"PostgreSQL query lock contention and pool starvation"`).
  4. **Offline Resilient Architecture**: Includes a deterministic 1024-bucket subword bigram projection matrix ($1024 \times 384$) ensuring instant vector generation even when running completely offline without downloading multi-gigabyte models.

---

### 3. XGBoost (Structured Metrics Incident Classifier)
- **Primary Role**: Gradient Boosted Decision Tree (`xgb.XGBClassifier`) for classifying the root cause failure domain based on system metrics.
- **Where it lives**: `backend/app/services/xgboost_service.py` (`XGBoostIncidentClassifier`).
- **Core Mechanisms**:
  1. **Ordered Feature Vector (7 Metrics)**:
     - `cpu_usage_pct`: CPU utilization percentage.
     - `memory_usage_pct`: RAM consumption.
     - `error_count_1m`: Error spike count over the last 1 minute.
     - `db_timeout_count_1m`: Database query acquisition timeouts.
     - `response_time_ms`: Average HTTP latency.
     - `network_error_count_1m`: Socket / connection reset errors.
     - `connection_pool_usage_pct`: Database connection pool saturation.
  2. **Native Missing Value Handling**: Missing telemetry metrics are preserved as `np.nan` instead of arbitrarily filling with 0, leveraging XGBoost's native split-finding algorithm.
  3. **Multi-Class Softmax Probabilities (`multi:softprob`)**: Predicts across categories (`database`, `network`, `compute`, `memory`, `authentication`, `dependency`, `unknown`) and outputs exact confidence distributions (e.g., `database: 89.2%`, `network: 3.8%`).
  4. **Model Lifecycle & Persistence**:
     - Trained on historical records (`POST /api/ml/xgboost/train`).
     - Evaluated with Macro-F1 score and saved as `ml_artifacts/xgboost_category_model.json`.
     - Registered in MongoDB `model_registry` with version timestamps and schema metadata.
  5. **Heuristic Baseline Fallback**: If the model has not been trained yet, a deterministic rule-based heuristic serves predictions so the system is never blocked.

---

### 4. RAG (Retrieval-Augmented Generation & Anti-Hallucination)
- **Primary Role**: Grounding AI Root Cause Analysis in real organizational evidence to eliminate hallucinations.
- **Where it lives**: `backend/app/services/rca.py` (`RCAService`) & `retrieval.py`.
- **Core Mechanisms**:
  1. **Retrieval Phase**:
     - Pulls actual log events and stack traces related to the incident.
     - Performs semantic vector search (MiniLM) and MongoDB text search to retrieve matching historical incidents and approved runbooks.
     - Applies redaction to mask any credentials before sending to LLM.
  2. **Augmentation Phase (Grounded Prompting)**:
     - Assembles the prompt containing: (1) Ingested log evidence, (2) Historical incidents and resolutions, (3) Approved diagnostic runbooks.
     - System prompt strictly instructs: *"Every cited supportingEvidence excerpt MUST be an exact verbatim substring from the provided log stream. Do NOT invent or alter log excerpts."*
  3. **Generation Phase (Schema Enforcement)**:
     - Calls LLM (Claude, OpenAI, Hugging Face, or Mock) enforcing strict Pydantic `RCAResult` schemas.
     - Divides findings into **Observed Facts** (provable statements with log citations) vs **AI Inferences** (probabilistic hypotheses).
  4. **Anti-Hallucination Evidence Grounding Validation**:
     - Post-processes the LLM output: the backend inspects every cited excerpt. If the excerpt cannot be verified as an exact substring in the actual ingested logs, the backend automatically prunes it before saving to the database.

---

## 4. Database Collections & Schemas

### 1. `log_events` Collection
Stores normalized and redacted log entries:
```json
{
  "_id": "670b8a1c9e8d1234567890ab",
  "source": "collector-demo-app",
  "service": "order-service",
  "level": "ERROR",
  "message": "Database connection pool exhausted during transaction commit",
  "raw": "2026-10-13 10:14:02.123 [ERROR] [order-service] Database connection pool exhausted...",
  "timestamp": "2026-10-13T10:14:02.123Z",
  "fingerprint": "a9f3b1e7c84d265e",
  "metadata": {
    "host": "k8s-node-04",
    "environment": "production"
  },
  "redactedFields": ["user_email", "auth_token"],
  "createdAt": "2026-10-13T10:14:05.000Z"
}
```

### 2. `incidents` Collection
Correlated group of deduplicated log errors:
```json
{
  "_id": "INC-20261013-001",
  "title": "Database connection pool exhausted in order-service",
  "service": "order-service",
  "severity": "CRITICAL",
  "status": "OPEN",
  "fingerprint": "a9f3b1e7c84d265e",
  "eventCount": 42,
  "firstSeen": "2026-10-13T10:14:02Z",
  "lastSeen": "2026-10-13T10:18:45Z",
  "rootCauseAnalysis": {
    "summary": "Connection leak caused by unclosed DB sessions during payment timeout cascade.",
    "observedFacts": [
      "Log ID 670b8a1c: 'Database connection pool exhausted'",
      "Log ID 670b8a1f: 'Acquisition timeout after 30000ms'"
    ],
    "inferences": [
      "Previous network timeout in payment gateway prevented transaction rollback execution."
    ],
    "suggestedRemediation": {
      "actionId": "restart_demo_service",
      "risk": "HIGH",
      "description": "Restart order microservice container to reset connection pools."
    }
  }
}
```

### 3. `tickets` Collection
Operational work item linked to an incident:
```json
{
  "_id": "TCK-1042",
  "incidentId": "INC-20261013-001",
  "title": "P1 Incident: order-service DB Pool Exhaustion",
  "priority": "P1",
  "status": "IN_PROGRESS",
  "assignee": "supporter@acme.corp",
  "history": [
    { "status": "OPEN", "timestamp": "2026-10-13T10:15:00Z", "actor": "system" },
    { "status": "IN_PROGRESS", "timestamp": "2026-10-13T10:17:30Z", "actor": "supporter@acme.corp" }
  ]
}
```

### 4. `remediation_approvals` Collection
Governance approvals between Support and Senior Managers:
```json
{
  "_id": "APP-9021",
  "incidentId": "INC-20261013-001",
  "actionId": "restart_demo_service",
  "risk": "HIGH",
  "requestedBy": "supporter@acme.corp",
  "status": "APPROVED",
  "approvedBy": "approver@acme.corp",
  "comments": "Approved. Traffic routed to secondary region.",
  "createdAt": "2026-10-13T10:20:00Z",
  "decidedAt": "2026-10-13T10:21:15Z"
}
```

### 5. `audit_logs` Collection
Immutable record of all platform activities:
```json
{
  "_id": "670b8f449e8d1234567890cc",
  "action": "EXECUTE_REMEDIATION",
  "actor": "supporter@acme.corp",
  "role": "support",
  "target": "order-service:restart_demo_service",
  "status": "SUCCESS",
  "details": {
    "approvalId": "APP-9021",
    "healthCheckResult": "200_OK"
  },
  "timestamp": "2026-10-13T10:22:00Z"
}
```

---

## 4. Role-Based Access Control (RBAC) Matrix

| Capability | Viewer | Support Engineer (`supporter`) | Senior Manager (`approver`) | Administrator (`admin`) |
| :--- | :---: | :---: | :---: | :---: |
| **View Dashboards & Metrics** | Yes | Yes | Yes | Yes |
| **Inspect Incidents & RCA** | Yes | Yes | Yes | Yes |
| **Upload Log Files** | No | Yes | Yes | Yes |
| **Request Low-Risk Remediation** | No | Yes | Yes | Yes |
| **Request High-Risk Remediation** | No | Yes (Sends to Approver) | Yes | Yes |
| **Approve / Reject Requests** | No | No | Yes | Yes |
| **Execute Approved Actions** | No | Yes (After Approval) | Yes | Yes |
| **Register Log Sources & Rules** | No | No | No | Yes |
| **View Audit Trail** | Yes | Yes | Yes | Yes |

---

## 5. How to Run & Demonstrate the Project

### One-Click Startup (PowerShell)
In the repository root, run:
```powershell
.\start-local.ps1
```
This automatically initiates all required services:
1. **Demo App Microservice**: `http://localhost:8001` (Emits simulated logs & faults)
2. **Log Collector Daemon**: Tails `demo-app/app.log` and streams to backend
3. **Backend API**: `http://localhost:8000` (FastAPI + Async Ingestion + RCA Engine)
4. **Frontend UI**: `http://localhost:5173` (React Dashboard styled with Paolo aesthetic)

### Default Demonstration Accounts
- **Support Engineer**:
  - Email: `supporter@acme.corp`
  - Password: `Password123!`
  - Role: `support`
- **Senior Manager / Approver**:
  - Email: `approver@acme.corp`
  - Password: `Password123!`
  - Role: `approver`
- **Administrator**:
  - Email: `admin@acme.corp`
  - Password: `Password123!`
  - Role: `admin`

---

## 6. Key Differentiators for Presentation

1. **Separation of Facts from Hypotheses**: Unlike typical chatbots that hallucinate root causes, our engine strictly validates log citations against actual ingested entries.
2. **Deterministic Fingerprinting**: Eliminates alert fatigue by grouping thousands of identical errors into one unified incident.
3. **Dual-Gated Human Governance**: SRE teams can trust the platform because high-risk actions require manager approval, and no arbitrary shell commands are permitted.
4. **Closed-Loop Verification**: Automatically verifies microservice health post-fix before resolving tickets.
5. **Modern Minimalist UI**: Clean, high-contrast, off-white card design system inspired by top modern enterprise dashboards.
