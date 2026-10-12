import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

SCENARIO_DEFINITIONS = [
    {
        "id": "db_connection_timeout",
        "service": "order-service",
        "has_incident": True,
        "verified_cause": "Database connection pool exhaustion due to leaked unclosed sessions",
        "expected_remediation": "restart_demo_service",
        "expected_rule": "db_pool_timeout_rule",
        "indicator_keywords": ["ConnectionPoolTimeout", "Timeout waiting for connection", "Pool exhausted"],
        "manual_baseline_mttr_seconds": 1800.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Order service initialized successfully on port 8000"},
            {"offset_sec": 10, "level": "INFO", "message": "GET /orders/1029 HTTP/1.1 200 OK duration=12ms"},
            {"offset_sec": 30, "level": "WARN", "message": "Connection pool usage at 85% capacity (17/20 active sessions)"},
            {"offset_sec": 45, "level": "WARN", "message": "High query wait time: 450ms for query 'SELECT * FROM orders'"},
            {"offset_sec": 60, "level": "ERROR", "message": "ConnectionPoolTimeout: Timeout waiting for connection from pool after 30000ms. Active: 20/20, Waiting: 14"},
            {"offset_sec": 62, "level": "ERROR", "message": "Traceback (most recent call last):\n  File '/app/db.py', line 89, in get_connection\n    raise ConnectionPoolTimeoutError('Pool exhausted')\nConnectionPoolTimeoutError: Pool exhausted"},
            {"offset_sec": 70, "level": "ERROR", "message": "ConnectionPoolTimeout: Timeout waiting for connection from pool after 30000ms. Active: 20/20, Waiting: 22"},
            {"offset_sec": 75, "level": "CRITICAL", "message": "Fatal: Database connection pool fully saturated. Unable to process incoming checkout requests"}
        ]
    },
    {
        "id": "memory_leak",
        "service": "catalog-service",
        "has_incident": True,
        "verified_cause": "Unbounded cache retention causing memory leak and JVM/process heap exhaustion",
        "expected_remediation": "restart_demo_service",
        "expected_rule": "oom_killer_rule",
        "indicator_keywords": ["OutOfMemoryError", "heap space", "Memory limit exceeded"],
        "manual_baseline_mttr_seconds": 2400.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Catalog worker started. JVM Heap max: 1024MB"},
            {"offset_sec": 15, "level": "WARN", "message": "Heap memory usage reached 82% (840MB/1024MB)"},
            {"offset_sec": 30, "level": "WARN", "message": "Garbage collection pause took 1850ms, reclaiming only 12MB"},
            {"offset_sec": 50, "level": "ERROR", "message": "java.lang.OutOfMemoryError: Java heap space. Memory limit exceeded (1024MB)"},
            {"offset_sec": 52, "level": "ERROR", "message": "Worker thread Thread-4 crashed with OutOfMemoryError during cache ingestion"},
            {"offset_sec": 65, "level": "CRITICAL", "message": "Process killed by OOM killer or heap exhaustion. Service unreachable"}
        ]
    },
    {
        "id": "bad_config_deploy",
        "service": "payment-service",
        "has_incident": True,
        "verified_cause": "Missing required database encryption secret in configuration deployment",
        "expected_remediation": "rollback_demo_config",
        "expected_rule": "config_validation_error_rule",
        "indicator_keywords": ["ConfigValidationError", "Missing required database encryption key", "KeyError"],
        "manual_baseline_mttr_seconds": 1500.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Deploying release v2.4.1 to payment-service"},
            {"offset_sec": 10, "level": "INFO", "message": "Loading configuration from /etc/payment/config.yaml"},
            {"offset_sec": 15, "level": "ERROR", "message": "ConfigValidationError: Missing required database encryption key 'DB_SECRET_KEY' in configuration deployment"},
            {"offset_sec": 16, "level": "ERROR", "message": "KeyError: 'DB_SECRET_KEY' required for payload encryption during startup"},
            {"offset_sec": 20, "level": "CRITICAL", "message": "Application startup halted due to invalid configuration: DB_SECRET_KEY is null"}
        ]
    },
    {
        "id": "auth_failure_spike",
        "service": "auth-service",
        "has_incident": True,
        "verified_cause": "Expired signing key or credential stuffing attack causing sudden spike of 401s",
        "expected_remediation": "clear_demo_cache",
        "expected_rule": "auth_failure_spike_rule",
        "indicator_keywords": ["Authentication failure spike", "401 Unauthorized", "Invalid JWT"],
        "manual_baseline_mttr_seconds": 1200.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Auth service running normal JWT verification"},
            {"offset_sec": 10, "level": "WARN", "message": "401 Unauthorized: Failed login attempt for user user_491 from 198.51.100.12"},
            {"offset_sec": 20, "level": "ERROR", "message": "Authentication failure spike: 250 failed token authentications in 60s. Invalid JWT signature"},
            {"offset_sec": 25, "level": "ERROR", "message": "401 Unauthorized: Invalid signature on bearer token for /api/v1/profile"},
            {"offset_sec": 30, "level": "ERROR", "message": "Authentication failure spike: 410 failed logins in 60s. Rate limit throttling engaged"}
        ]
    },
    {
        "id": "downstream_503",
        "service": "checkout-service",
        "has_incident": True,
        "verified_cause": "Downstream payment gateway outage returning HTTP 503 Service Unavailable",
        "expected_remediation": "restart_demo_service",
        "expected_rule": "downstream_dependency_503_rule",
        "indicator_keywords": ["503 Service Unavailable", "Downstream payment gateway returned 503", "timeout"],
        "manual_baseline_mttr_seconds": 2100.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Checkout service processing order queue"},
            {"offset_sec": 10, "level": "WARN", "message": "Downstream payment gateway response latency exceeded 5000ms"},
            {"offset_sec": 25, "level": "ERROR", "message": "HTTP 503 Service Unavailable received from payment gateway: Gateway timeout after 10000ms"},
            {"offset_sec": 28, "level": "ERROR", "message": "Payment processing failed for order 88410: Downstream payment gateway returned 503"},
            {"offset_sec": 35, "level": "ERROR", "message": "Circuit breaker OPEN for payment-gateway. All orders failing with 503"}
        ]
    },
    {
        "id": "disk_full",
        "service": "storage-service",
        "has_incident": True,
        "verified_cause": "Root filesystem storage partition 100% full preventing writes",
        "expected_remediation": "clear_demo_cache",
        "expected_rule": "disk_space_exhaustion_rule",
        "indicator_keywords": ["No space left on device", "Errno 28", "Disk full"],
        "manual_baseline_mttr_seconds": 1800.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Storage worker starting periodic snapshot dump"},
            {"offset_sec": 10, "level": "WARN", "message": "Disk space warning: /var/data partition at 94% utilization"},
            {"offset_sec": 25, "level": "ERROR", "message": "OSError: [Errno 28] No space left on device: '/var/data/snapshot_98.db'"},
            {"offset_sec": 27, "level": "ERROR", "message": "Failed to persist transaction log: Disk full. Write operations suspended"},
            {"offset_sec": 35, "level": "CRITICAL", "message": "Volume write failure: Cannot allocate block. No space left on device"}
        ]
    },
    {
        "id": "thread_deadlock",
        "service": "order-service",
        "has_incident": True,
        "verified_cause": "Circular lock acquisition across concurrent inventory and reservation transactions",
        "expected_remediation": "restart_demo_service",
        "expected_rule": "deadlock_detected_rule",
        "indicator_keywords": ["Deadlock detected", "Thread lock contention", "DeadlockDetected"],
        "manual_baseline_mttr_seconds": 2700.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Transaction coordinator initialized with 32 worker threads"},
            {"offset_sec": 15, "level": "WARN", "message": "Thread-12 waiting on Lock<Inventory:109> held by Thread-28 for >15000ms"},
            {"offset_sec": 20, "level": "WARN", "message": "Thread-28 waiting on Lock<Reservation:44> held by Thread-12 for >15000ms"},
            {"offset_sec": 30, "level": "ERROR", "message": "Deadlock detected: Circular dependency between Thread-12 and Thread-28. Transaction aborted"},
            {"offset_sec": 35, "level": "ERROR", "message": "DeadlockDetected: All 32 worker threads in wait state. Thread pool deadlock lock contention"}
        ]
    },
    {
        "id": "cert_expired",
        "service": "api-gateway",
        "has_incident": True,
        "verified_cause": "Expired SSL/TLS x509 leaf certificate on upstream internal endpoint",
        "expected_remediation": "restart_demo_service",
        "expected_rule": "cert_expired_rule",
        "indicator_keywords": ["SSLError", "Certificate has expired", "TLS handshake failed"],
        "manual_baseline_mttr_seconds": 1600.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Gateway forwarding traffic to upstream endpoints"},
            {"offset_sec": 10, "level": "WARN", "message": "TLS negotiation warning: upstream cert expires in 0 days"},
            {"offset_sec": 20, "level": "ERROR", "message": "SSLError: Certificate has expired on api.upstream.internal (NotAfter: 2026-10-12T00:00:00Z)"},
            {"offset_sec": 22, "level": "ERROR", "message": "TLS handshake failed for upstream proxy: [SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired"},
            {"offset_sec": 30, "level": "CRITICAL", "message": "Upstream TLS connection aborted: Certificate expired"}
        ]
    },
    {
        "id": "rate_limit_exhaustion",
        "service": "notification-service",
        "has_incident": True,
        "verified_cause": "Third-party SMS/Email provider quota exhausted returning 429 Too Many Requests",
        "expected_remediation": "clear_demo_cache",
        "expected_rule": "rate_limit_rule",
        "indicator_keywords": ["429 Too Many Requests", "Rate limit quota exceeded", "RateLimitExceeded"],
        "manual_baseline_mttr_seconds": 1400.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Notification dispatcher queue running with 5 workers"},
            {"offset_sec": 10, "level": "WARN", "message": "Provider rate limit quota approaching 95% (950/1000 requests per minute)"},
            {"offset_sec": 20, "level": "ERROR", "message": "RateLimitExceeded: 429 Too Many Requests from SMS provider. Rate limit quota exceeded"},
            {"offset_sec": 25, "level": "ERROR", "message": "HTTP 429: Retry-After: 60s. Dropping non-critical notification delivery batches"}
        ]
    },
    {
        "id": "benign_healthy_traffic",
        "service": "web-frontend-service",
        "has_incident": False,
        "verified_cause": "N/A - Clean operational traffic",
        "expected_remediation": "none",
        "expected_rule": None,
        "indicator_keywords": [],
        "manual_baseline_mttr_seconds": 0.0,
        "logs": [
            {"offset_sec": 0, "level": "INFO", "message": "Web server listening on 0.0.0.0:80"},
            {"offset_sec": 5, "level": "INFO", "message": "GET / HTTP/1.1 200 OK duration=4ms"},
            {"offset_sec": 10, "level": "DEBUG", "message": "Session cache lookup for user 4410"},
            {"offset_sec": 15, "level": "INFO", "message": "GET /products HTTP/1.1 200 OK duration=18ms"},
            {"offset_sec": 20, "level": "WARN", "message": "Cache miss for product key 'prod_882', fetching from database"},
            {"offset_sec": 25, "level": "INFO", "message": "GET /cart HTTP/1.1 200 OK duration=8ms"},
            {"offset_sec": 30, "level": "INFO", "message": "POST /analytics HTTP/1.1 204 No Content duration=3ms"}
        ]
    }
]

def generate_scenario_dataset(base_time: datetime = None) -> List[Dict[str, Any]]:
    if base_time is None:
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)

    scenarios = []
    for sc_def in SCENARIO_DEFINITIONS:
        sc_id = sc_def["id"]
        service = sc_def["service"]
        trace_id = str(uuid.uuid4())[:8]
        start_time = base_time + timedelta(minutes=int(sc_def["manual_baseline_mttr_seconds"] % 60))

        raw_events = []
        for log_item in sc_def["logs"]:
            event_time = start_time + timedelta(seconds=log_item["offset_sec"])
            raw_events.append({
                "timestamp": event_time.isoformat(),
                "service": service,
                "severity": log_item["level"],
                "message": log_item["message"],
                "traceId": trace_id,
                "source": {
                    "type": "scenario_eval",
                    "sourceId": sc_id
                }
            })

        scenario_doc = {
            "scenarioId": sc_id,
            "service": service,
            "hasIncident": sc_def["has_incident"],
            "incidentStartTime": start_time.isoformat(),
            "verifiedCause": sc_def["verified_cause"],
            "expectedRemediation": sc_def["expected_remediation"],
            "expectedRule": sc_def["expected_rule"],
            "indicatorKeywords": sc_def["indicator_keywords"],
            "manualBaselineMttrSeconds": sc_def["manual_baseline_mttr_seconds"],
            "events": raw_events
        }
        scenarios.append(scenario_doc)

    return scenarios

if __name__ == "__main__":
    datasets = generate_scenario_dataset()
    print(f"Generated {len(datasets)} synthetic scenario datasets:")
    for ds in datasets:
        print(f" - {ds['scenarioId']} (service: {ds['service']}, incident: {ds['hasIncident']}, events: {len(ds['events'])})")
    
    with open("eval/labeled_scenarios.json", "w", encoding="utf-8") as f:
        json.dump(datasets, f, indent=2)
    print("Saved to eval/labeled_scenarios.json")
