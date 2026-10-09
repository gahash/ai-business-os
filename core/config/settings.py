from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, loaded from environment / .env.

    See §146 of the technical specification for the required variable list.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_secret: str = Field(default="", alias="APP_SECRET")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_business_os",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    encryption_key: str = Field(default="", alias="ENCRYPTION_KEY")
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    jwt_access_ttl_minutes: int = Field(default=15, alias="JWT_ACCESS_TTL_MINUTES")
    jwt_refresh_ttl_days: int = Field(default=7, alias="JWT_REFRESH_TTL_DAYS")

    ai_provider: str = Field(default="ollama", alias="AI_PROVIDER")
    ai_model: str = Field(default="llama3.1", alias="AI_MODEL")
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")

    vector_db_url: str = Field(default="", alias="VECTOR_DB_URL")
    email_provider: str = Field(default="", alias="EMAIL_PROVIDER")
    crm_provider: str = Field(default="internal", alias="CRM_PROVIDER")
    storage_path: str = Field(default="./data/storage", alias="STORAGE_PATH")

    # 5s, not 2s: the first asyncpg connection on a cold pool can take >2s by itself (observed
    # locally), which would make /health falsely report "offline" right after a fresh deploy.
    health_check_timeout_seconds: float = Field(default=5.0, alias="HEALTH_CHECK_TIMEOUT_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
