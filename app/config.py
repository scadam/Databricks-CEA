from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Dict


class MissingConfigurationError(RuntimeError):
    """Raised when a required runtime configuration value is missing."""


@dataclass(frozen=True)
class Settings:
    """Strongly-typed configuration for the Azure Function runtime."""

    microsoft_app_id: str
    microsoft_app_type: str
    microsoft_app_tenant_id: str
    microsoft_app_password: str | None
    databricks_token: str
    databricks_base_url: str
    databricks_model_name: str
    system_prompt: str
    max_tokens: int
    temperature: float
    bypass_authentication: bool

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables with validation."""

        def require(name: str) -> str:
            value = os.getenv(name)
            if not value:
                raise MissingConfigurationError(f"Environment variable '{name}' is required.")
            return value

        def optional_int(name: str, default: int) -> int:
            raw = os.getenv(name)
            if not raw:
                return default
            try:
                return int(raw)
            except ValueError as exc:
                raise MissingConfigurationError(
                    f"Environment variable '{name}' must be an integer."
                ) from exc

        def optional_float(name: str, default: float) -> float:
            raw = os.getenv(name)
            if not raw:
                return default
            try:
                return float(raw)
            except ValueError as exc:
                raise MissingConfigurationError(
                    f"Environment variable '{name}' must be a number."
                ) from exc

        system_prompt = (
            os.getenv(
                "SYSTEM_PROMPT",
                "You are an AI assistant that uses Databricks models to help Microsoft 365 users.",
            ).strip()
            or "You are an AI assistant that uses Databricks models to help Microsoft 365 users."
        )

        bypass_authentication = os.getenv("BYPASS_AUTHENTICATION", "false").lower() in (
            "1",
            "true",
            "yes",
        )

        return cls(
            microsoft_app_id=require("MicrosoftAppId"),
            microsoft_app_type=require("MicrosoftAppType"),
            microsoft_app_tenant_id=require("MicrosoftAppTenantId"),
            microsoft_app_password=os.getenv("MicrosoftAppPassword"),
            databricks_token=require("DATABRICKS_TOKEN"),
            databricks_base_url=require("DATABRICKS_BASE_URL"),
            databricks_model_name=os.getenv("DATABRICKS_MODEL_NAME", "databricks-gpt-oss-120b"),
            system_prompt=system_prompt,
            max_tokens=optional_int("OPENAI_MAX_TOKENS", 1024),
            temperature=optional_float("OPENAI_TEMPERATURE", 0.2),
            bypass_authentication=bypass_authentication,
        )

    def to_bot_auth_config(self) -> Dict[str, Any]:
        """Return configuration mapping expected by Bot Framework authentication helper."""

        return {
            "MicrosoftAppId": self.microsoft_app_id,
            "MicrosoftAppType": self.microsoft_app_type,
            "MicrosoftAppTenantId": self.microsoft_app_tenant_id,
            "MicrosoftAppPassword": self.microsoft_app_password,
        }
