from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BEMESTAR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "development"
    timezone: str = "America/Sao_Paulo"
    public_base_url: str = "http://localhost:8787"
    database_url: str = "sqlite:///./var/bemestar.db"
    raw_dir: Path = Path("./var/raw")
    log_level: str = "INFO"
    trusted_hosts: Annotated[list[str], NoDecode] = ["localhost", "127.0.0.1"]
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    max_webhook_bytes: int = 25 * 1024 * 1024
    raw_retention_days: int = 180
    min_free_disk_bytes: int = 1024 * 1024 * 1024

    webhook_token: str = "CHANGE_ME"
    mcp_token: str = "CHANGE_ME"
    session_secret: str = "CHANGE_ME"
    dashboard_username: str = "admin"
    dashboard_password_hash: str = "CHANGE_ME"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 30

    notification_webhook_url: str = ""
    notification_webhook_token: str = ""

    worker_poll_seconds: int = 3
    recompute_lookback_days: int = 90

    session_ttl_seconds: int = 43_200
    login_rate_limit: int = 5
    login_rate_window_seconds: int = 60
    api_rate_limit: int = 180
    api_rate_window_seconds: int = 60
    webhook_rate_limit: int = 180
    webhook_rate_window_seconds: int = 60
    rate_limiter_max_keys: int = 10_000
    worker_lease_seconds: int = 900

    @field_validator("trusted_hosts", "cors_origins", mode="before")
    @classmethod
    def parse_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def ensure_runtime_dirs(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite:///"):
            raw = self.database_url.removeprefix("sqlite:///")
            if raw != ":memory:":
                Path(raw).parent.mkdir(parents=True, exist_ok=True)

    def validate_production_secrets(self) -> None:
        if self.env.lower() not in {"production", "prod"}:
            return
        bad = []
        for name in ("webhook_token", "mcp_token", "session_secret", "dashboard_password_hash"):
            value = getattr(self, name)
            if not value or value == "CHANGE_ME":
                bad.append(name)
        if bad:
            joined = ", ".join(bad)
            raise RuntimeError(f"Production secrets are not configured: {joined}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    settings.validate_production_secrets()
    return settings
