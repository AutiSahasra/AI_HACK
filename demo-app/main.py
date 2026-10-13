import os
import json
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Response
from pydantic import BaseModel

LOG_DIR = os.environ.get("LOG_DIR", os.path.join(os.path.dirname(__file__), "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.environ.get("LOG_FILE", os.path.join(LOG_DIR, "demo_app.log"))

class AppState:
    current_fault: Optional[str] = None
    service_name: str = "order-service"
    memory_buffer: list = []
    fault_task: Optional[asyncio.Task] = None

state = AppState()

def write_log(message: str, level: str = "INFO", service: str = "order-service", structured: bool = True):
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if structured:
                payload = {
                    "timestamp": now_iso,
                    "severity": level,
                    "service": service,
                    "message": message,
                    "host": "demo-host-01"
                }
                f.write(json.dumps(payload) + "\n")
            else:
                f.write(f"{now_iso} [{level}] [{service}] {message}\n")
    except Exception as e:
        print(f"Failed to write log: {e}")

async def background_log_emitter():
    counter = 0
    while True:
        await asyncio.sleep(2.0)
        counter += 1
        if not state.current_fault:
            # Emit normal traffic
            if counter % 2 == 0:
                write_log(f"Processed order checkout #ORD-{1000 + counter} successfully", level="INFO", service="order-service")
            else:
                write_log(f"Cache hit for product catalog inventory check item #{500 + counter}", level="DEBUG", service="inventory-service")
        else:
            # Emit logs corresponding to active fault
            if state.current_fault == "db_connection_timeout":
                write_log("Connection to database replica timed out after 5000ms for worker pool", level="ERROR", service="order-service")
                write_log("Database connection pool exhausted. Active: 20/20, Waiters: 15", level="CRITICAL", service="order-service")
            elif state.current_fault == "memory_leak":
                state.memory_buffer.append("X" * 1024 * 512)  # allocate memory
                write_log("java.lang.OutOfMemoryError: Java heap space saturated. GC overhead limit exceeded", level="CRITICAL", service="payment-service")
            elif state.current_fault == "bad_config_deploy":
                write_log("ConfigError: Failed to parse configuration: missing mandatory environment variable DB_HOST in yaml", level="ERROR", service="inventory-service")
            elif state.current_fault == "auth_failure_spike":
                write_log("401 Unauthorized: Invalid credentials provided for user client-981", level="WARN", service="auth-service")
            elif state.current_fault == "downstream_503":
                write_log("503 Service Unavailable received from downstream billing-gateway", level="ERROR", service="order-service")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    write_log("Demo app initialized and ready to serve traffic", level="INFO")
    state.fault_task = asyncio.create_task(background_log_emitter())
    yield
    if state.fault_task:
        state.fault_task.cancel()

app = FastAPI(
    title="Demo Microservice App",
    description="Simulated production microservice emitting structured & plain logs with triggerable faults and admin endpoints.",
    lifespan=lifespan
)

@app.get("/health")
async def health(response: Response):
    if state.current_fault:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "active_fault": state.current_fault,
            "service": state.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    return {
        "status": "healthy",
        "service": state.service_name,
        "active_fault": None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/faults/{fault_type}")
async def inject_fault(fault_type: str):
    valid_faults = {
        "db_connection_timeout",
        "memory_leak",
        "bad_config_deploy",
        "auth_failure_spike",
        "downstream_503"
    }
    if fault_type not in valid_faults:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown fault type '{fault_type}'. Supported: {list(valid_faults)}"
        )
    state.current_fault = fault_type
    write_log(f"ALERT: Fault injection triggered: {fault_type}", level="CRITICAL")
    return {"status": "fault_injected", "fault": fault_type}

# Admin endpoints used strictly by allow-listed remediation executors
@app.post("/admin/restart")
async def admin_restart():
    state.current_fault = None
    state.memory_buffer = []
    write_log("Service gracefully restarted by admin remediation. Database connection pool recycled.", level="INFO")
    return {"status": "restarted", "recovered": True}

@app.post("/admin/clear-cache")
async def admin_clear_cache():
    state.memory_buffer = []
    if state.current_fault == "memory_leak":
        state.current_fault = None
    write_log("Application cache flushed and memory buffer released.", level="INFO")
    return {"status": "cache_cleared", "recovered": True}

@app.post("/admin/rollback-config")
async def admin_rollback_config():
    if state.current_fault == "bad_config_deploy":
        state.current_fault = None
    write_log("Configuration rolled back to stable release v1.4.2.", level="INFO")
    return {"status": "config_rolled_back", "recovered": True}

@app.post("/admin/reset-fault")
async def admin_reset():
    state.current_fault = None
    state.memory_buffer = []
    write_log("Fault cleared manually.", level="INFO")
    return {"status": "cleared", "recovered": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
