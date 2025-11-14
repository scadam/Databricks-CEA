import os
import pytest

from app.config import MissingConfigurationError, Settings


def test_missing_env_raises():
    with pytest.raises(MissingConfigurationError):
        Settings.from_env()


def test_valid_env_loads(monkeypatch):
    monkeypatch.setenv("MicrosoftAppId", "123")
    monkeypatch.setenv("MicrosoftAppType", "UserAssignedMSI")
    monkeypatch.setenv("MicrosoftAppTenantId", "tenant")
    monkeypatch.setenv("MicrosoftAppPassword", "secret")
    monkeypatch.setenv("DATABRICKS_TOKEN", "token")
    monkeypatch.setenv("DATABRICKS_BASE_URL", "https://example")
    monkeypatch.setenv("DATABRICKS_MODEL_NAME", "model")
    monkeypatch.setenv("BYPASS_AUTHENTICATION", "true")
    result = Settings.from_env()
    assert result.microsoft_app_id == "123"
    assert result.databricks_model_name == "model"
    assert result.bypass_authentication is True
