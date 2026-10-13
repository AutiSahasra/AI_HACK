from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "AI Root Cause Analysis & Intelligent Ticket Resolution Copilot"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "ai_rca_copilot"
    USE_IN_MEMORY_DB: bool = False  # Set to True in test environments if live mongo is not running

    # Security
    JWT_SECRET: str = "dev-secret-key-super-secure-change-in-production-123456789"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Ingestion Limits
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB

    # AI Model Settings
    LLM_PROVIDER: str = "mock"  # "mock", "anthropic", "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_SECONDS: int = 300

    # ML Models
    MINILM_MODEL_ID: str = "sentence-transformers/all-MiniLM-L6-v2"
    MINILM_EMBEDDING_DIM: int = 384
    XGBOOST_MODEL_DIR: str = "ml_artifacts"

    # Live demo app URL (for health checks and safe remediation executor)
    DEMO_APP_URL: str = "http://localhost:8001"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:80",
        "http://frontend:80",
    ]

settings = Settings()
