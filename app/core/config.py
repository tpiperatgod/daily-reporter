from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str
    DB_PASSWORD: str

    # Redis
    REDIS_URL: str

    # Provider Configuration
    X_PROVIDER: str = "MOCK"  # "APIFY" or "MOCK"
    APIFY_API_TOKEN: Optional[str] = None
    APIFY_ACTOR_TIMEOUT_SECONDS: int = 300

    # LLM Configuration
    LLM_BASE: str
    LLM_MODEL: str
    LLM_EMBEDDING_MODEL: str
    LLM_API_KEY: str
    LLM_MAX_TOKENS: int = 12000

    # SMTP Configuration
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    FROM_EMAIL: str

    # Application
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "X-News-Digest"
    APP_VERSION: str = "0.1.0"

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
