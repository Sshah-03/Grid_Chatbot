from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "mysql+asyncmy://chat_user:chat_pass@localhost:3306/chat_app"
    token_ttl_seconds: int = 86_400
    token_salt: str = "change-me"
    httpx_timeout_connect: float = 3.0
    httpx_timeout_read: float = 8.0
    retry_max_attempts: int = 3
    retry_backoff_factor: float = 0.5
    retry_jitter_seconds: float = 0.2
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    log_level: str = "INFO"
    log_file_path: str = "logs/app.log"
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
