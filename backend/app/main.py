from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.database import DatabaseManager
from app.core.seeder import seed_all_data

# Routers
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.uploads import router as uploads_router
from app.api.logs import router as logs_router
from app.api.incidents import router as incidents_router

from app.services.ingestion import ingestion_service
from app.workflows.detection_workflow import run_detection_pipeline
from app.services.grouping import grouping_service
from app.services.rca import rca_service

setup_logging()

# Register shared detection pipeline for upload and live events
ingestion_service.register_detection_hook(run_detection_pipeline)
# Register background RCA analysis hook
grouping_service.register_rca_hook(rca_service.analyze_incident)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await DatabaseManager.connect()
    await seed_all_data()
    yield
    # Shutdown
    await DatabaseManager.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise decision-support copilot for IT/DevOps root cause analysis, incident correlation, and safe remediation.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(uploads_router, prefix=settings.API_V1_STR)
app.include_router(logs_router, prefix=settings.API_V1_STR)
app.include_router(incidents_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
        "status": "online"
    }
