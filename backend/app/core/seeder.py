import logging
import uuid
from datetime import datetime, timezone
from app.repositories.user_repo import user_repo
from app.models.user import UserCreate, UserRole
from app.core.database import DatabaseManager

logger = logging.getLogger(__name__)

async def migrate_admin_accounts():
    try:
        users_col = DatabaseManager.get_collection("users")
        res = await users_col.update_many({"role": "admin"}, {"$set": {"role": "approver"}})
        if res.modified_count > 0:
            logger.info(f"Migrated {res.modified_count} legacy admin users to approver role.")
        
        actions_col = DatabaseManager.get_collection("remediationActions")
        await actions_col.update_many({"allowedRoles": "admin"}, {"$addToSet": {"allowedRoles": "approver"}})
        await actions_col.update_many({}, {"$pull": {"allowedRoles": "admin"}})
    except Exception as e:
        logger.warning(f"Admin account migration notice: {e}")

async def seed_all_data():
    logger.info("Initializing database seeds...")
    await migrate_admin_accounts()
    await seed_users()
    await seed_detection_rules()
    await seed_runbooks()
    await seed_remediation_actions()
    await seed_historical_incidents()
    logger.info("Seeding completed successfully.")

async def seed_users():
    default_users = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "adminpassword123",
            "role": UserRole.APPROVER,
            "full_name": "System Administrator",
        },
        {
            "username": "approver",
            "email": "approver@example.com",
            "password": "approverpassword123",
            "role": UserRole.APPROVER,
            "full_name": "Senior SRE Approver",
        },
        {
            "username": "support",
            "email": "support@example.com",
            "password": "supportpassword123",
            "role": UserRole.SUPPORT_ENGINEER,
            "full_name": "Tier 1 Support Engineer",
        },
    ]

    for u in default_users:
        existing = await user_repo.get_by_username(u["username"])
        if not existing:
            await user_repo.create(UserCreate(**u))
            logger.info(f"Seeded user: {u['username']} ({u['role'].value})")
        elif existing.get("role") == "admin":
            users_col = DatabaseManager.get_collection("users")
            await users_col.update_one({"_id": existing["_id"]}, {"$set": {"role": "approver"}})
            logger.info(f"Migrated existing user {u['username']} to approver role.")

async def seed_detection_rules():
    col = DatabaseManager.get_collection("detectionRules")
    count = await col.count_documents({})
    if count > 0:
        return

    rules = [
        {
            "_id": "rule-db-timeout",
            "name": "Database Connection Timeout Spike",
            "description": "Detects database connection timeouts and pool exhaustion",
            "ruleType": "pattern",
            "service": "order-service",
            "pattern": r"(?i)(database|db|postgres|mysql|mongo).*(timeout|timed[ -]?out)|connection pool exhausted",
            "severity": "CRITICAL",
            "threshold": 3,
            "windowMinutes": 5,
            "enabled": True,
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "rule-oom-leak",
            "name": "Memory Leak / Out of Memory",
            "description": "Detects JVM or Python memory allocation failures and OOM killer",
            "ruleType": "pattern",
            "service": "payment-service",
            "pattern": r"(?i)out of memory|OutOfMemoryError|heap space|memory limit exceeded",
            "severity": "CRITICAL",
            "threshold": 2,
            "windowMinutes": 5,
            "enabled": True,
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "rule-bad-config",
            "name": "Bad Configuration Deployment Failure",
            "description": "Detects invalid config schema, missing env vars, or parse errors on startup",
            "ruleType": "pattern",
            "service": "inventory-service",
            "pattern": r"(?i)config.*error|invalid configuration|missing required env|syntaxerror.*yaml|pydantic\.error",
            "severity": "ERROR",
            "threshold": 1,
            "windowMinutes": 5,
            "enabled": True,
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "rule-auth-spike",
            "name": "Authentication Failure Spike",
            "description": "Detects surge of 401/403 or credential rejection errors",
            "ruleType": "threshold",
            "service": "auth-service",
            "pattern": r"(?i)unauthorized|authentication failed|invalid credentials|token rejected",
            "severity": "WARN",
            "threshold": 5,
            "windowMinutes": 5,
            "enabled": True,
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "rule-downstream-503",
            "name": "Downstream Service 503 Unavailable",
            "description": "Detects downstream dependency outages or 503 responses",
            "ruleType": "pattern",
            "service": "api-gateway",
            "pattern": r"(?i)downstream.*503|service unavailable|upstream connect error|bad gateway",
            "severity": "ERROR",
            "threshold": 3,
            "windowMinutes": 5,
            "enabled": True,
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "rule-generic-error-rate",
            "name": "High Error Rate Anomaly",
            "description": "Z-score spike check on rolling window error frequency",
            "ruleType": "anomaly",
            "service": "*",
            "pattern": "",
            "severity": "ERROR",
            "threshold": 5,
            "windowMinutes": 5,
            "enabled": True,
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    await col.insert_many(rules)
    logger.info(f"Seeded {len(rules)} detection rules")

async def seed_runbooks():
    col = DatabaseManager.get_collection("runbooks")
    count = await col.count_documents({})
    if count > 0:
        return

    runbooks = [
        {
            "_id": "rb-db-recovery",
            "title": "Database Connection Pool Recovery Runbook",
            "service": "order-service",
            "description": "Steps to resolve database pool exhaustion and connection timeouts.",
            "diagnosticSteps": [
                "1. Verify database node reachability and active connection count via metrics.",
                "2. Check if slow queries are locking connection worker threads.",
                "3. Inspect connection leak in order-service query transactions."
            ],
            "remediationSteps": [
                "1. Trigger safe service restart or pool recycling.",
                "2. Verify health recovery at /health endpoint.",
                "3. Monitor subsequent log stream for timeout cessation."
            ],
            "riskLevel": "medium",
            "prerequisites": ["Ensure no active database schema migration is running"],
            "recoveryCheck": "GET /health responds with 200 and healthy connection count",
            "suggestedAction": "restart_demo_service"
        },
        {
            "_id": "rb-mem-leak",
            "title": "Memory Exhaustion and Cache Eviction Runbook",
            "service": "payment-service",
            "description": "Mitigation steps when memory utilization reaches critical threshold.",
            "diagnosticSteps": [
                "1. Inspect resident memory and heap dump metrics.",
                "2. Check for cache accumulation without TTL eviction.",
                "3. Verify GC pause duration."
            ],
            "remediationSteps": [
                "1. Flush ephemeral cache buffers using clear_demo_cache.",
                "2. If heap remains saturated, perform graceful container restart.",
                "3. Verify memory usage normalizes."
            ],
            "riskLevel": "low",
            "prerequisites": ["Confirm upstream requests can tolerate brief cache warmup"],
            "recoveryCheck": "GET /health reports memory within acceptable limits",
            "suggestedAction": "clear_demo_cache"
        },
        {
            "_id": "rb-config-rollback",
            "title": "Bad Deployment / Configuration Rollback Runbook",
            "service": "inventory-service",
            "description": "Standard procedure when a configuration push breaks startup or validation.",
            "diagnosticSteps": [
                "1. Review recent git deployment commits and environment configuration diffs.",
                "2. Identify malformed or missing environment variables from error stack traces."
            ],
            "remediationSteps": [
                "1. Execute automated rollback to previous known-good configuration using rollback_demo_config.",
                "2. Verify service restarts and passes health verification."
            ],
            "riskLevel": "high",
            "prerequisites": ["Senior Approver authorization required"],
            "recoveryCheck": "GET /health confirms configuration version restored",
            "suggestedAction": "rollback_demo_config"
        }
    ]
    await col.insert_many(runbooks)
    logger.info(f"Seeded {len(runbooks)} runbooks")

async def seed_remediation_actions():
    col = DatabaseManager.get_collection("remediationActions")
    count = await col.count_documents({})
    if count > 0:
        return

    actions = [
        {
            "_id": "action-restart",
            "name": "restart_demo_service",
            "description": "Restarts the target demo microservice container and clears hung connections.",
            "riskLevel": "medium",
            "requiresApproval": True,
            "allowedRoles": ["approver"],
            "parametersSchema": {"type": "object", "properties": {"service": {"type": "string"}}},
            "executorKey": "restart_demo_service",
            "associatedHealthCheck": "/health",
            "timeoutSeconds": 30,
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "action-clear-cache",
            "name": "clear_demo_cache",
            "description": "Flushes internal in-memory cache to release heap memory.",
            "riskLevel": "low",
            "requiresApproval": False,
            "allowedRoles": ["support_engineer", "approver"],
            "parametersSchema": {"type": "object", "properties": {}},
            "executorKey": "clear_demo_cache",
            "associatedHealthCheck": "/health",
            "timeoutSeconds": 15,
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "action-rollback",
            "name": "rollback_demo_config",
            "description": "Rolls back faulty deployment environment variables to prior stable configuration.",
            "riskLevel": "high",
            "requiresApproval": True,
            "allowedRoles": ["approver"],
            "parametersSchema": {"type": "object", "properties": {}},
            "executorKey": "rollback_demo_config",
            "associatedHealthCheck": "/health",
            "timeoutSeconds": 30,
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    await col.insert_many(actions)
    logger.info(f"Seeded {len(actions)} remediation actions")

async def seed_historical_incidents():
    col = DatabaseManager.get_collection("historicalIncidents")
    count = await col.count_documents({})
    if count > 0:
        return

    hist = [
        {
            "_id": "hist-inc-101",
            "title": "PostgreSQL connection pool exhaustion on order-service",
            "service": "order-service",
            "summary": "Surge in checkout traffic exhausted max connection pool of 20, leading to database connection timeout errors.",
            "verifiedCause": "Connection pool size too low for burst traffic + transaction block leak.",
            "remediationPerformed": "Restarted order-service with increased pool size.",
            "remediationAction": "restart_demo_service",
            "outcome": "Resolved. Latency returned to 45ms.",
            "logExcerpt": "Connection to database replica timed out after 5000ms\nPoolTimeout: Timeout waiting for connection from pool",
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "hist-inc-102",
            "title": "Unbounded cache retention causing memory limit OOM",
            "service": "payment-service",
            "summary": "Redis cache fallback kept token cache indefinitely, consuming 98% memory.",
            "verifiedCause": "TTL missing on temporary auth tokens cache causing heap saturation.",
            "remediationPerformed": "Cleared application cache and restarted daemon.",
            "remediationAction": "clear_demo_cache",
            "outcome": "Resolved. Memory stabilized at 30%.",
            "logExcerpt": "java.lang.OutOfMemoryError: Java heap space\nProcess killed by kernel OOM killer",
            "createdAt": datetime.now(timezone.utc)
        },
        {
            "_id": "hist-inc-103",
            "title": "Invalid YAML configuration syntax on inventory-service deployment",
            "service": "inventory-service",
            "summary": "CI/CD pipeline pushed invalid database host URL in config map.",
            "verifiedCause": "Missing environment variable DB_HOST in configuration.",
            "remediationPerformed": "Rolled back config to revision v1.4.2.",
            "remediationAction": "rollback_demo_config",
            "outcome": "Resolved. Service initialized successfully.",
            "logExcerpt": "ConfigError: Failed to parse configuration: missing DB_HOST parameter",
            "createdAt": datetime.now(timezone.utc)
        }
    ]
    await col.insert_many(hist)
    logger.info(f"Seeded {len(hist)} historical incidents")
