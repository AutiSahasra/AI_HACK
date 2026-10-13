import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from app.models.schema_spec import (
    IncidentDoc,
    LogEventDoc,
    KnowledgeArticleDoc,
    EnvironmentEnum,
    SeverityEnum,
    IncidentStatusEnum,
    CategoryLabelEnum,
    ConfirmationStatusEnum,
    LogLevelEnum,
    SourceEnum,
    LabelSourceEnum,
    ServiceMeta,
    RootCauseMeta,
    IncidentMetrics,
    ResolutionMeta,
    ResolutionAction,
)
from app.services.minilm_service import minilm_service, MODEL_ID

SERVICES = [
    "payments-api",
    "auth-service",
    "inventory-service",
    "order-service",
    "billing-gateway",
]

CATEGORIES = [
    CategoryLabelEnum.database,
    CategoryLabelEnum.network,
    CategoryLabelEnum.compute,
    CategoryLabelEnum.memory,
    CategoryLabelEnum.authentication,
    CategoryLabelEnum.dependency,
    CategoryLabelEnum.unknown,
]

CATEGORY_PATTERNS = {
    CategoryLabelEnum.database: {
        "titles": [
            "PostgreSQL Connection Pool Exhaustion Spike",
            "Read-Replica Query Timeout Overload",
            "Deadlock Spike on Transactions Ledger",
            "Database Connection Acquired Latency Spike",
        ],
        "symptoms": [
            "Client connection backlog exceeding pool maximum",
            "Database queries timing out after 30000ms",
            "Active connections hovering near 100% capacity",
            "Spike in 500 error responses during checkout writes",
        ],
        "root_causes": (
            "db_connection_pool_saturation",
            "Long-running analytical query held table lock, leading to connection pool starvation across web workers.",
        ),
        "remediation": "Scaled database connection pool max connections and killed stuck lock-holding transaction PID.",
        "metric_ranges": {
            "cpu_usage_pct": (25.0, 60.0),
            "memory_usage_pct": (40.0, 75.0),
            "error_count_1m": (15, 95),
            "db_timeout_count_1m": (12, 60),
            "response_time_ms": (1200.0, 8500.0),
            "network_error_count_1m": (0, 5),
            "connection_pool_usage_pct": (85.0, 99.5),
        },
    },
    CategoryLabelEnum.memory: {
        "titles": [
            "JVM Old Gen Heap Saturation Out-Of-Memory",
            "Node.js Buffer Allocation Memory Leak",
            "Container cgroup OOMKilled Event on Worker",
            "High Garbage Collection Pause Time Spike",
        ],
        "symptoms": [
            "Resident set size steadily climbing without release",
            "Major GC pause times exceeding 4500ms",
            "Worker processes terminating unexpectedly due to signal 9",
            "Requests hanging during large payload processing",
        ],
        "root_causes": (
            "heap_memory_leak_unbounded_cache",
            "Unbounded in-memory session cache caused progressive heap saturation leading to kernel OOM kill.",
        ),
        "remediation": "Evicted cached session objects and configured LRU eviction with max size limit.",
        "metric_ranges": {
            "cpu_usage_pct": (30.0, 70.0),
            "memory_usage_pct": (88.0, 99.0),
            "error_count_1m": (10, 80),
            "db_timeout_count_1m": (0, 3),
            "response_time_ms": (800.0, 4500.0),
            "network_error_count_1m": (0, 4),
            "connection_pool_usage_pct": (20.0, 60.0),
        },
    },
    CategoryLabelEnum.compute: {
        "titles": [
            "High CPU Utilization and Thread Starvation",
            "Cryptographic Hashing Thread Lock Spike",
            "Infinite Loop in Data Serialization Worker",
            "Container CPU Throttling Alert Exceeded",
        ],
        "symptoms": [
            "CPU utilization pinned at 98%+ across all cores",
            "Worker thread pool queue length growing exponentially",
            "Kubernetes CPU CFS throttle periods spiked to 45%",
            "Heartbeat check failures on health endpoints",
        ],
        "root_causes": (
            "cpu_saturation_thread_contention",
            "Unindexed regex evaluation on user search query saturated CPU thread pools.",
        ),
        "remediation": "Optimized regex pattern and deployed worker autoscaling replica increase.",
        "metric_ranges": {
            "cpu_usage_pct": (90.0, 100.0),
            "memory_usage_pct": (40.0, 70.0),
            "error_count_1m": (12, 75),
            "db_timeout_count_1m": (0, 5),
            "response_time_ms": (1500.0, 6000.0),
            "network_error_count_1m": (1, 8),
            "connection_pool_usage_pct": (25.0, 65.0),
        },
    },
    CategoryLabelEnum.network: {
        "titles": [
            "Ingress TCP Connection Reset Rate Spike",
            "Inter-Pod DNS Resolution Latency Anomaly",
            "Service Mesh Envoy Proxy 504 Gateway Timeout",
            "Socket Descriptors Exhaustion on API Gateway",
        ],
        "symptoms": [
            "Upstream socket timeout and connection reset errors",
            "DNS lookup failures resolving internal service hostnames",
            "Elevated packet drops and syn backlog saturation",
            "502 and 504 status codes returned to ingress clients",
        ],
        "root_causes": (
            "dns_conntrack_table_exhaustion",
            "Kernel conntrack table exhaustion caused intermittent packet drops between gateway and pods.",
        ),
        "remediation": "Increased netfilter conntrack maximum limit and restarted kube-proxy.",
        "metric_ranges": {
            "cpu_usage_pct": (20.0, 55.0),
            "memory_usage_pct": (30.0, 60.0),
            "error_count_1m": (20, 110),
            "db_timeout_count_1m": (0, 4),
            "response_time_ms": (2500.0, 9500.0),
            "network_error_count_1m": (25, 90),
            "connection_pool_usage_pct": (15.0, 50.0),
        },
    },
    CategoryLabelEnum.authentication: {
        "titles": [
            "JWT Verification Public Key Rotation Spike",
            "OAuth Token Introspection Latency Spike",
            "High Rate of HTTP 401 Unauthorized Responses",
            "Session Signature Key Mismatch Anomaly",
        ],
        "symptoms": [
            "Spike in HTTP 401 and 403 responses across public endpoints",
            "JWT verification failing due to signature key mismatch",
            "Auth cache misses causing elevated load on identity provider",
            "User login failure rate exceeding 15%",
        ],
        "root_causes": (
            "jwks_stale_public_key_cache",
            "Identity provider rotated verification keys while API gateway cached stale JWKS certificates.",
        ),
        "remediation": "Flushed stale JWKS public key cache and forced key set refresh from IDP.",
        "metric_ranges": {
            "cpu_usage_pct": (15.0, 45.0),
            "memory_usage_pct": (25.0, 55.0),
            "error_count_1m": (40, 150),
            "db_timeout_count_1m": (0, 2),
            "response_time_ms": (300.0, 1200.0),
            "network_error_count_1m": (0, 3),
            "connection_pool_usage_pct": (10.0, 40.0),
        },
    },
    CategoryLabelEnum.dependency: {
        "titles": [
            "Third-Party Payment Gateway 503 Outage",
            "SMS Verification Provider Webhook Failure",
            "Cloud Storage Bucket S3 Rate Limit Exceeded",
            "External Fraud Screening Service Timeout",
        ],
        "symptoms": [
            "Downstream HTTP 503 and 429 status codes from external partner",
            "Outbound payment authorization calls timing out after 10s",
            "Circuit breaker open state triggered for payment processor",
            "Transaction pending queues accumulating unconfirmed orders",
        ],
        "root_causes": (
            "upstream_vendor_api_degradation",
            "Payment gateway experienced regional outage returning persistent HTTP 503 Service Unavailable.",
        ),
        "remediation": "Tripped circuit breaker to activate backup payment provider routing.",
        "metric_ranges": {
            "cpu_usage_pct": (20.0, 50.0),
            "memory_usage_pct": (30.0, 60.0),
            "error_count_1m": (30, 120),
            "db_timeout_count_1m": (0, 3),
            "response_time_ms": (3500.0, 10000.0),
            "network_error_count_1m": (10, 45),
            "connection_pool_usage_pct": (20.0, 55.0),
        },
    },
    CategoryLabelEnum.unknown: {
        "titles": [
            "Intermittent Sporadic Latency Jitter",
            "Ambiguous Multithread Synchronization Warning",
            "Noisy Telemetry Metric Anomaly",
            "Unclassified Error Signature in Batch Worker",
        ],
        "symptoms": [
            "Telemetry jitter without distinct error pattern",
            "Intermittent latency spikes observed across random endpoints",
            "Partial metrics missing due to logging agent restart",
            "No clear error stack trace available in log stream",
        ],
        "root_causes": (
            "unconfirmed_environmental_noise",
            "Telemetry anomaly caused by transient infrastructure jitter without persistent service defect.",
        ),
        "remediation": "Monitored telemetry trends; metrics stabilized within normal operating parameters.",
        "metric_ranges": {
            "cpu_usage_pct": (10.0, 45.0),
            "memory_usage_pct": (20.0, 50.0),
            "error_count_1m": (2, 18),
            "db_timeout_count_1m": (0, 2),
            "response_time_ms": (200.0, 1500.0),
            "network_error_count_1m": (0, 4),
            "connection_pool_usage_pct": (10.0, 35.0),
        },
    },
}

KNOWLEDGE_ARTICLES_DATA = [
    {
        "article_id": "KB-DB-001",
        "title": "PostgreSQL Connection Pool Tuning and Starvation Resolution",
        "category": CategoryLabelEnum.database,
        "content": "When application response times spike accompanied by database timeout errors, inspect active connections against the database max_connections limit. Common causes include unindexed queries, long transactions holding locks, and missing connection timeouts in connection poolers.",
        "service_names": ["payments-api", "order-service"],
        "resolution_steps": [
            "Check pg_stat_activity for queries waiting on lock acquisition.",
            "Terminate long-running query PID blocking connection pool.",
            "Scale pool size or restart pooler service.",
        ],
    },
    {
        "article_id": "KB-MEM-002",
        "title": "Diagnosing Java & Node.js Memory Leaks and OOMKilled Pods",
        "category": CategoryLabelEnum.memory,
        "content": "Container terminates with exit code 137 when resident memory exceeds cgroup limit. Inspect heap memory trends and major garbage collection duration. Unbounded in-memory collections and static references prevent GC reclamation.",
        "service_names": ["payments-api", "inventory-service"],
        "resolution_steps": [
            "Capture heap dump or trace heap memory growth profile.",
            "Restart affected service replica to immediately clear saturated memory.",
            "Deploy hotfix restricting maximum cache size.",
        ],
    },
    {
        "article_id": "KB-NET-003",
        "title": "Resolving Ingress Gateway 504 Timeouts and DNS Latency",
        "category": CategoryLabelEnum.network,
        "content": "HTTP 502/504 errors from ingress proxies often indicate socket exhaustion or DNS conntrack table saturation. Verify CoreDNS request latency and host network connection limits.",
        "service_names": ["billing-gateway", "auth-service"],
        "resolution_steps": [
            "Verify CoreDNS cluster latency and upstream DNS resolution.",
            "Inspect socket states (netstat/ss) for TIME_WAIT port exhaustion.",
            "Restart gateway envoy proxy or increase conntrack limits.",
        ],
    },
    {
        "article_id": "KB-AUTH-004",
        "title": "Handling Stale JWKS Public Keys and 401 Spikes",
        "category": CategoryLabelEnum.authentication,
        "content": "Sudden increases in HTTP 401 Unauthorized errors across services typically occur when the identity provider rotates signing keys but client APIs cache stale public keys.",
        "service_names": ["auth-service", "payments-api"],
        "resolution_steps": [
            "Force refresh of cached JWKS key set from identity provider.",
            "Verify issuer URL and audience claims match token payload.",
            "Check client certificate validity dates.",
        ],
    },
    {
        "article_id": "KB-DEP-005",
        "title": "Tripping Downstream Circuit Breakers for 3rd-Party Outages",
        "category": CategoryLabelEnum.dependency,
        "content": "When external SaaS or payment APIs fail with 503 or persistent timeouts, trip service circuit breakers to prevent thread pool exhaustion and activate fallback routing.",
        "service_names": ["billing-gateway", "payments-api"],
        "resolution_steps": [
            "Check external partner status page for active incident.",
            "Trip circuit breaker to divert traffic to secondary provider.",
            "Verify pending queue drain once upstream service recovers.",
        ],
    },
]


def generate_synthetic_dataset(
    count: int = 350,
    seed: int = 42,
    base_time: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Deterministic synthetic incident and log event generator (seed=42).
    Generates:
    - `incidents`: coherent structured metrics, symptoms, root cause, resolutions.
    - `log_events`: 2-4 linked structured log events per incident.
    - `knowledge_articles`: curated knowledge articles with 384-dim MiniLM embeddings.
    """
    rng = np.random.RandomState(seed)
    now = base_time or datetime.now(timezone.utc)

    incidents: List[Dict[str, Any]] = []
    log_events: List[Dict[str, Any]] = []

    # 1. Knowledge Articles with MiniLM embeddings
    knowledge_articles: List[Dict[str, Any]] = []
    for ka in KNOWLEDGE_ARTICLES_DATA:
        article_text = f"{ka['title']}. {ka['content']} {' '.join(ka['resolution_steps'])}"
        emb = minilm_service.encode(article_text)
        k_doc = {
            "article_id": ka["article_id"],
            "title": ka["title"],
            "content": ka["content"],
            "category": ka["category"].value,
            "service_names": ka["service_names"],
            "resolution_steps": ka["resolution_steps"],
            "embedding": emb,
            "embedding_model": MODEL_ID,
            "content_version": 1,
            "verified": True,
            "source": "synthetic",
            "is_synthetic": True,
            "created_at": now - timedelta(days=30),
            "updated_at": now - timedelta(days=30),
        }
        knowledge_articles.append(k_doc)

    # 2. Incidents and linked Log Events
    severities = [SeverityEnum.low, SeverityEnum.medium, SeverityEnum.high, SeverityEnum.critical]
    statuses = [IncidentStatusEnum.resolved, IncidentStatusEnum.mitigated, IncidentStatusEnum.open, IncidentStatusEnum.investigating]

    for i in range(1, count + 1):
        incident_key = f"INC-{i:06d}"
        category = CATEGORIES[i % len(CATEGORIES)]
        pattern = CATEGORY_PATTERNS[category]
        service_name = SERVICES[rng.choice(len(SERVICES))]

        # Choose title and symptom
        title_idx = rng.choice(len(pattern["titles"]))
        title = f"[{service_name.upper()}] {pattern['titles'][title_idx]}"
        symptom = pattern["symptoms"][title_idx % len(pattern["symptoms"])]
        root_cause_key, root_cause_explanation = pattern["root_causes"]
        remediation_summary = pattern["remediation"]

        # Vary metrics within range
        metric_ranges = pattern["metric_ranges"]
        metrics_dict: Dict[str, Any] = {}
        for feat, (fmin, fmax) in metric_ranges.items():
            if feat.endswith("_count_1m"):
                val = int(rng.randint(int(fmin), int(fmax) + 1))
            else:
                val = round(float(rng.uniform(fmin, fmax)), 2)

            # Introduce intentional missing values on 10% of records to simulate real-world telemetry loss
            if rng.rand() < 0.10:
                metrics_dict[feat] = None
            else:
                metrics_dict[feat] = val

        # Timestamps
        created_at = now - timedelta(hours=count - i, minutes=int(rng.randint(0, 59)))
        status = statuses[rng.choice(len(statuses))]
        resolved_at = created_at + timedelta(minutes=int(rng.randint(15, 120))) if status in (IncidentStatusEnum.resolved, IncidentStatusEnum.closed) else None
        updated_at = resolved_at or (created_at + timedelta(minutes=10))

        severity = severities[rng.choice(len(severities))]
        if category in (CategoryLabelEnum.database, CategoryLabelEnum.memory) and (metrics_dict.get("error_count_1m") or 0) > 50:
            severity = SeverityEnum.critical

        # Build Incident Document
        incident_doc = {
            "incident_key": incident_key,
            "title": title,
            "description": f"Automated alert detected in {service_name}: {symptom}",
            "service": {
                "name": service_name,
                "environment": EnvironmentEnum.synthetic.value,
            },
            "severity": severity.value,
            "status": status.value,
            "category_label": category.value,
            "root_cause": {
                "label": root_cause_key,
                "explanation": root_cause_explanation,
                "confirmation_status": ConfirmationStatusEnum.synthetic_ground_truth.value,
            },
            "metrics": metrics_dict,
            "symptoms": [symptom, f"Metrics variance alert on {service_name}"],
            "resolution": {
                "summary": remediation_summary if status == IncidentStatusEnum.resolved else None,
                "actions": [
                    {
                        "action": "execute_allow_listed_remediation",
                        "outcome": "completed",
                        "performed_at": updated_at.isoformat(),
                        "verified": True if status == IncidentStatusEnum.resolved else False,
                    }
                ] if status == IncidentStatusEnum.resolved else [],
                "verified": True if status == IncidentStatusEnum.resolved else False,
            },
            "source": SourceEnum.synthetic.value,
            "is_synthetic": True,
            "label_source": LabelSourceEnum.synthetic_rule.value,
            "created_at": created_at,
            "updated_at": updated_at,
            "resolved_at": resolved_at,
        }
        incidents.append(incident_doc)

        # 3. Create 2-4 correlated log events for this incident
        fingerprint = hashlib.md5(f"{service_name}:{category.value}:{title_idx}".encode("utf-8")).hexdigest()
        num_logs = rng.randint(2, 5)

        for log_idx in range(num_logs):
            log_time = created_at - timedelta(seconds=int(rng.randint(10, 180)))
            log_id = f"evt_{incident_key.lower()}_{log_idx+1}"

            level = LogLevelEnum.ERROR if log_idx == num_logs - 1 else LogLevelEnum.WARNING
            msg = f"[{service_name}] {symptom} (trace: {incident_key}, cycle: {log_idx})"

            # Embed log message with MiniLM
            log_emb = minilm_service.encode(msg)

            log_doc = {
                "event_id": log_id,
                "incident_id": incident_key,
                "timestamp": log_time,
                "service_name": service_name,
                "environment": EnvironmentEnum.synthetic.value,
                "level": level.value,
                "message": msg,
                "error_type": f"{category.value.capitalize()}Exception",
                "request_id": f"req_{str(uuid.uuid4())[:8]}",
                "metrics_snapshot": {
                    "cpu_pct": metrics_dict.get("cpu_usage_pct"),
                    "mem_pct": metrics_dict.get("memory_usage_pct"),
                },
                "fingerprint": fingerprint,
                "embedding": log_emb,
                "embedding_model": MODEL_ID,
                "is_synthetic": True,
                "created_at": log_time,
            }
            log_events.append(log_doc)

    return incidents, log_events, knowledge_articles
