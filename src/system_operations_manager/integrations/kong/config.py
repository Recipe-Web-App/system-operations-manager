"""Kong Gateway configuration models."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from system_operations_manager.integrations.observability.config import (
        ObservabilityStackConfig,
    )


class KongConnectionConfig(BaseModel):
    """Kong Admin API connection configuration."""

    model_config = ConfigDict(extra="forbid")

    base_url: str = "http://localhost:8001"
    timeout: int = 30
    verify_ssl: bool = True
    retries: int = 3

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v

    @field_validator("retries")
    @classmethod
    def validate_retries(cls, v: int) -> int:
        """Validate retries is non-negative."""
        if v < 0:
            raise ValueError("retries must be non-negative")
        return v


class KongAuthConfig(BaseModel):
    """Kong Admin API authentication configuration."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["none", "api_key", "mtls"] = "none"
    api_key: str | None = None
    header_name: str = "Kong-Admin-Token"
    cert_path: str | None = None
    key_path: str | None = None
    ca_path: str | None = None

    @field_validator("type")
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        """Validate authentication type."""
        valid_types = {"none", "api_key", "mtls"}
        if v not in valid_types:
            raise ValueError(f"auth type must be one of: {', '.join(sorted(valid_types))}")
        return v


class KongEnterpriseConfig(BaseModel):
    """Kong Enterprise-specific configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False


class KongPluginConfig(BaseModel):
    """Complete Kong plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    connection: KongConnectionConfig = KongConnectionConfig()
    auth: KongAuthConfig = KongAuthConfig()
    output_format: Literal["table", "json", "yaml"] = "table"
    default_workspace: str = "default"
    enterprise: KongEnterpriseConfig = KongEnterpriseConfig()
    observability: ObservabilityStackConfig | None = None

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        """Validate output format."""
        valid_formats = {"table", "json", "yaml"}
        if v not in valid_formats:
            raise ValueError(f"output_format must be one of: {', '.join(sorted(valid_formats))}")
        return v

    @classmethod
    def from_env(cls, base_config: dict[str, Any] | None = None) -> KongPluginConfig:
        """Create configuration with environment variable overrides.

        Environment variables take precedence over base_config values.

        Supported environment variables:
            OPS_KONG_BASE_URL: Kong Admin API base URL
            OPS_KONG_API_KEY: API key for authentication
            OPS_KONG_AUTH_TYPE: Authentication type (none, api_key, mtls)
            OPS_KONG_WORKSPACE: Default workspace name
            OPS_KONG_OUTPUT: Output format (table, json, yaml)

        Observability environment variables:
            OPS_PROMETHEUS_URL: Prometheus server URL
            OPS_ELASTICSEARCH_HOSTS: Comma-separated Elasticsearch hosts
            OPS_ELASTICSEARCH_INDEX: Elasticsearch index pattern
            OPS_LOKI_URL: Grafana Loki URL
            OPS_JAEGER_URL: Jaeger Query API URL
            OPS_ZIPKIN_URL: Zipkin API URL
        """
        # Import here to avoid circular imports
        from system_operations_manager.integrations.observability.config import (
            ObservabilityStackConfig,
        )

        config_dict = base_config.copy() if base_config else {}

        # Ensure nested dicts exist
        if "connection" not in config_dict:
            config_dict["connection"] = {}
        if "auth" not in config_dict:
            config_dict["auth"] = {}

        # Connection overrides
        if base_url := os.environ.get("OPS_KONG_BASE_URL"):
            config_dict["connection"]["base_url"] = base_url

        # Auth overrides
        if api_key := os.environ.get("OPS_KONG_API_KEY"):
            config_dict["auth"]["api_key"] = api_key
            # Auto-set auth type to api_key if key is provided
            if "type" not in config_dict["auth"] or config_dict["auth"]["type"] == "none":
                config_dict["auth"]["type"] = "api_key"

        if auth_type := os.environ.get("OPS_KONG_AUTH_TYPE"):
            config_dict["auth"]["type"] = auth_type

        # Plugin-level overrides
        if workspace := os.environ.get("OPS_KONG_WORKSPACE"):
            config_dict["default_workspace"] = workspace

        if output_format := os.environ.get("OPS_KONG_OUTPUT"):
            config_dict["output_format"] = output_format

        # Handle observability config from env
        obs_base_config = config_dict.pop("observability", None)
        if isinstance(obs_base_config, dict) or any(
            os.environ.get(var)
            for var in [
                "OPS_PROMETHEUS_URL",
                "OPS_ELASTICSEARCH_HOSTS",
                "OPS_LOKI_URL",
                "OPS_JAEGER_URL",
                "OPS_ZIPKIN_URL",
            ]
        ):
            obs_config = ObservabilityStackConfig.from_env(
                obs_base_config if isinstance(obs_base_config, dict) else None
            )
            config_dict["observability"] = obs_config

        return cls.model_validate(config_dict)
