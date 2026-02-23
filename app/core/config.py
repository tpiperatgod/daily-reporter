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
    X_PROVIDER: str = "MOCK"  # "APIFY", "TWITTER_API", or "MOCK"
    APIFY_API_TOKEN: Optional[str] = None
    APIFY_ACTOR_TIMEOUT_SECONDS: int = 300

    # Twitter API Configuration
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_BASE_URL: str = "https://api.twitterapi.io"
    TWITTER_API_TIMEOUT_SECONDS: int = 30
    TWITTER_API_MAX_PAGES: int = 5  # 5 pages * 20 tweets = 100 max

    # LLM Chat API Configuration (for digest generation)
    LLM_CHAT_BASE_URL: str
    LLM_CHAT_MODEL: str
    LLM_CHAT_API_KEY: str

    # Embedding Provider Selection
    LLM_EMBEDDING_PROVIDER: str = "openai"  # "openai" or "ollama"

    # OpenAI-Compatible Embedding Provider (GLM, OpenAI, etc.)
    OPENAI_EMBEDDING_BASE_URL: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: Optional[str] = None
    OPENAI_EMBEDDING_API_KEY: Optional[str] = None

    # Ollama Embedding Provider
    OLLAMA_EMBEDDING_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "bge-m3:567m"

    # LLM Shared Configuration
    LLM_MAX_TOKENS: int = 12000

    # Embedding API Rate Limiting
    LLM_EMBEDDING_BATCH_SIZE: int = 64  # Max items per batch request
    LLM_EMBEDDING_RETRY_MAX_ATTEMPTS: int = 5  # Retry attempts on 429
    LLM_EMBEDDING_RETRY_INITIAL_BACKOFF: float = 1.0  # Initial backoff (seconds)

    # SMTP Configuration
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    FROM_EMAIL: str
    EMAIL_LOG_ONLY: bool = True  # Set to False to send actual emails (defaults to True for safety)

    # Application
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "X-News-Digest"
    APP_VERSION: str = "0.1.0"

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Timezone for cron expressions (default: CST/Asia/Shanghai)
    CRON_TIMEZONE: str = "Asia/Shanghai"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
