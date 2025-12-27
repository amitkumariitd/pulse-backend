"""Unit tests for central configuration Settings"""

import os
from contextlib import contextmanager

from config.settings import Settings, get_settings


@contextmanager
def temp_env(**env: str | None):
    """Temporarily set environment variables for a test.

    Any key with value None will be removed for the duration of the context.
    Clears the settings cache before and after.
    """
    old = {k: os.environ.get(k) for k in env}
    get_settings.cache_clear()  # Clear cache before setting new env
    try:
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()  # Clear cache after restoring env


def test_service_name_has_default():
    """Only service_name has a default; all other fields must come from env vars or .env files."""
    with temp_env(
        ENVIRONMENT="local",
        APP_HOST="0.0.0.0",
        APP_PORT="8000",
        LOG_LEVEL="INFO",
        TRACING_ENABLED="false",
        PULSE_DB_HOST="localhost",
        PULSE_DB_PORT="5432",
        PULSE_DB_USER="pulse",
        PULSE_DB_PASSWORD="secret",
        PULSE_DB_NAME="pulse",
        SERVICE_NAME=None,  # only field we're testing default for
    ):
        settings = Settings()

    assert settings.service_name == "pulse-backend"  # default applied


def test_env_vars_provide_all_required_values():
    """All required fields must be provided via env vars (or .env files in local)."""
    with temp_env(
        ENVIRONMENT="india-stage1",
        APP_HOST="0.0.0.0",
        APP_PORT="8080",
        LOG_LEVEL="DEBUG",
        TRACING_ENABLED="true",
        PULSE_DB_HOST="db.example",
        PULSE_DB_PORT="5432",
        PULSE_DB_USER="pulse",
        PULSE_DB_PASSWORD="secret",
        PULSE_DB_NAME="pulse",
    ):
        settings = Settings()

    assert settings.environment == "india-stage1"
    assert settings.log_level == "DEBUG"
    assert settings.app_port == 8080
    assert settings.tracing_enabled is True


def test_missing_required_values_fail_fast():
    """Settings should raise when required values are missing."""
    # Missing ENVIRONMENT (provide all other required fields)
    with temp_env(
        ENVIRONMENT=None,
        APP_HOST="0.0.0.0",
        APP_PORT="8000",
        LOG_LEVEL="INFO",
        TRACING_ENABLED="false",
        PULSE_DB_HOST="localhost",
        PULSE_DB_PORT="5432",
        PULSE_DB_USER="pulse",
        PULSE_DB_PASSWORD="secret",
        PULSE_DB_NAME="pulse",
    ):
        raised = False
        try:
            Settings(_env_file=None)  # Disable .env file loading for this test
        except Exception:
            raised = True
    assert raised is True, "Settings() should raise when ENVIRONMENT is missing"

    # Missing DB host/password (provide all other required fields)
    with temp_env(
        ENVIRONMENT="local",
        APP_HOST="0.0.0.0",
        APP_PORT="8000",
        LOG_LEVEL="INFO",
        TRACING_ENABLED="false",
        PULSE_DB_HOST=None,
        PULSE_DB_PORT="5432",
        PULSE_DB_USER="pulse",
        PULSE_DB_PASSWORD=None,
        PULSE_DB_NAME="pulse",
    ):
        raised = False
        try:
            Settings(_env_file=None)  # Disable .env file loading for this test
        except Exception:
            raised = True
    assert raised is True, "Settings() should raise when required DB values are missing"

