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

    # --- Broker Integration (optional) ---
    zerodha_api_key: str | None = None
    zerodha_access_token: str | None = None
    zerodha_use_mock: bool = True  # Use mock mode by default (set to False for production)
    zerodha_mock_scenario: str = "success"  # Mock scenario: success, partial_fill, rejection, network_error, timeout

    model_config = SettingsConfigDict(
        # Do NOT automatically load .env files
        # Use environment variables only (set explicitly or via dotenv CLI)
        # For local development: use scripts/run_tests_local.sh or export env vars manually
        # For stage/prod: use real env vars from ECS/SSM
        env_file=None,
        extra='ignore',  # Ignore extra fields not defined in the model
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance. Call this instead of instantiating Settings directly."""
    return Settings()


# For convenience, expose a function to get settings
# Usage: from config.settings import get_settings; settings = get_settings()
settings = get_settings

