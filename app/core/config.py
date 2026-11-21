"""Application settings (12-factor: everything comes from environment variables)."""
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = "postgresql+psycopg://finance:finance@localhost:5432/finance"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = ""  # comma separated; empty = same-origin only

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 20.0

    max_upload_mb: int = 5
    max_import_rows: int = 20000

    max_agent_steps: int = 10
    max_tool_calls: int = 10
    max_retries: int = 2
    max_chat_chars: int = 1000
    llm_polish_responses: bool = True  # one Gemini call per chat message to phrase verified facts

    rate_limit_enabled: bool = True
    auth_rate_limit_per_minute: int = 10
    chat_rate_limit_per_minute: int = 20

    monitor_interval_minutes: int = 60  # 0 disables the background scheduler

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Railway/Render hand out postgres:// or postgresql:// URLs; force psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        if not v.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL (postgresql+psycopg://...)")
        return v

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.is_production:
            if len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
            if "*" in self.cors_origin_list:
                raise ValueError("CORS_ORIGINS must not contain '*' in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
