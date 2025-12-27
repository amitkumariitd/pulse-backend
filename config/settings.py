import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for pulse-backend.

    Common defaults live here; environment variables override per environment.

    This module is intentionally simple: no YAML/JSON files, only env vars.
    """

    # --- Core ---
    environment: str  # required
    service_name: str = "pulse-backend"  # only field with default

    # --- HTTP server ---
    app_host: str  # required
    app_port: int  # required

    # --- Logging / tracing ---
    log_level: str  # required
    tracing_enabled: bool  # required

    # --- Database (PostgreSQL) ---
    pulse_db_host: str  # required
    pulse_db_port: int  # required
    pulse_db_user: str  # required
    pulse_db_password: str  # required
    pulse_db_name: str  # required

    # --- Internal service URLs (optional) ---
    gapi_base_url: str | None = None
    pulse_api_base_url: str | None = None

    model_config = SettingsConfigDict(
        # Always try to load .env files if they exist
        # .env.common: shared defaults (committed)
        # .env.local: local overrides (gitignored)
        # Stage/prod won't have these files, so they'll use real env vars from ECS/SSM
        env_file=(".env.common", ".env.local"),
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance. Call this instead of instantiating Settings directly."""
    return Settings()


# For convenience, expose a function to get settings
# Usage: from config.settings import get_settings; settings = get_settings()
settings = get_settings

