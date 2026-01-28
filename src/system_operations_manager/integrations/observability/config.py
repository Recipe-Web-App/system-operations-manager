"""Configuration models for external observability systems.

This module provides Pydantic configuration models for connecting to
external observability backends: Prometheus, Elasticsearch, Loki, Jaeger, and Zipkin.
"""

from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator


class PrometheusConfig(BaseModel):
    """Prometheus server configuration.

    Attributes:
        url: Prometheus server URL.
        timeout: Request timeout in seconds.
        auth_type: Authentication type (none, basic, bearer).
        username: Username for basic auth.
        password: Password for basic auth.
        token: Bearer token for bearer auth.
    """

    model_config = ConfigDict(extra="forbid")

    url: str = "http://localhost:9090"
    timeout: int = 30
    auth_type: Literal["none", "basic", "bearer"] = "none"
    username: str | None = None
    password: str | None = None
    token: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v


class ElasticsearchConfig(BaseModel):
    """Elasticsearch configuration.

    Supports both self-managed Elasticsearch and Elastic Cloud.

    Attributes:
        hosts: List of Elasticsearch host URLs.
        index_pattern: Index pattern for Kong logs.
        username: Username for basic auth.
        password: Password for basic auth.
        api_key: API key for authentication.
        cloud_id: Elastic Cloud deployment ID.
        verify_certs: Whether to verify TLS certificates.
        timeout: Request timeout in seconds.
    """

    model_config = ConfigDict(extra="forbid")

    hosts: list[str] = ["http://localhost:9200"]
    index_pattern: str = "kong-*"
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    cloud_id: str | None = None
    verify_certs: bool = True
    timeout: int = 30

    @field_validator("hosts")
    @classmethod
    def validate_hosts(cls, v: list[str]) -> list[str]:
        """Validate hosts are valid URLs."""
        validated = []
        for host in v:
            if not host.startswith(("http://", "https://")):
                raise ValueError(f"Host must start with http:// or https://: {host}")
            validated.append(host.rstrip("/"))
        return validated

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v


class LokiConfig(BaseModel):
    """Grafana Loki configuration.

    Attributes:
        url: Loki server URL.
        timeout: Request timeout in seconds.
        org_id: Organization ID for multi-tenant Loki.
        username: Username for basic auth.
        password: Password for basic auth.
    """

    model_config = ConfigDict(extra="forbid")

    url: str = "http://localhost:3100"
    timeout: int = 30
    org_id: str | None = None
    username: str | None = None
    password: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v


class JaegerConfig(BaseModel):
    """Jaeger Query API configuration.

    Attributes:
        query_url: Jaeger Query API URL.
        timeout: Request timeout in seconds.
        username: Username for basic auth.
        password: Password for basic auth.
    """

    model_config = ConfigDict(extra="forbid")

    query_url: str = "http://localhost:16686"
    timeout: int = 30
    username: str | None = None
    password: str | None = None

    @field_validator("query_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("query_url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v


class ZipkinConfig(BaseModel):
    """Zipkin API configuration.

    Attributes:
        url: Zipkin server URL.
        timeout: Request timeout in seconds.
    """

    model_config = ConfigDict(extra="forbid")

    url: str = "http://localhost:9411"
    timeout: int = 30

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v


class ObservabilityStackConfig(BaseModel):
    """Combined observability stack configuration.

    Configures connections to external observability systems.
    Each system is optional - only configure what you need.

    Attributes:
        prometheus: Prometheus server configuration.
        elasticsearch: Elasticsearch configuration.
        loki: Grafana Loki configuration.
        jaeger: Jaeger Query API configuration.
        zipkin: Zipkin API configuration.
    """

    model_config = ConfigDict(extra="forbid")

    prometheus: PrometheusConfig | None = None
    elasticsearch: ElasticsearchConfig | None = None
    loki: LokiConfig | None = None
    jaeger: JaegerConfig | None = None
    zipkin: ZipkinConfig | None = None

    @classmethod
    def from_env(cls, base_config: dict[str, Any] | None = None) -> ObservabilityStackConfig:
        """Create configuration with environment variable overrides.

        Environment variables take precedence over base_config values.

        Supported environment variables:
            OPS_PROMETHEUS_URL: Prometheus server URL
            OPS_ELASTICSEARCH_HOSTS: Comma-separated Elasticsearch hosts
            OPS_ELASTICSEARCH_INDEX: Elasticsearch index pattern
            OPS_LOKI_URL: Grafana Loki URL
            OPS_JAEGER_URL: Jaeger Query API URL
            OPS_ZIPKIN_URL: Zipkin API URL
        """
        config_dict = base_config.copy() if base_config else {}

        # Prometheus config from env
        if prometheus_url := os.environ.get("OPS_PROMETHEUS_URL"):
            if "prometheus" not in config_dict:
                config_dict["prometheus"] = {}
            config_dict["prometheus"]["url"] = prometheus_url

        # Elasticsearch config from env
        if es_hosts := os.environ.get("OPS_ELASTICSEARCH_HOSTS"):
            if "elasticsearch" not in config_dict:
                config_dict["elasticsearch"] = {}
            config_dict["elasticsearch"]["hosts"] = [h.strip() for h in es_hosts.split(",")]

        if es_index := os.environ.get("OPS_ELASTICSEARCH_INDEX"):
            if "elasticsearch" not in config_dict:
                config_dict["elasticsearch"] = {}
            config_dict["elasticsearch"]["index_pattern"] = es_index

        # Loki config from env
        if loki_url := os.environ.get("OPS_LOKI_URL"):
            if "loki" not in config_dict:
                config_dict["loki"] = {}
            config_dict["loki"]["url"] = loki_url

        # Jaeger config from env
        if jaeger_url := os.environ.get("OPS_JAEGER_URL"):
            if "jaeger" not in config_dict:
                config_dict["jaeger"] = {}
            config_dict["jaeger"]["query_url"] = jaeger_url

        # Zipkin config from env
        if zipkin_url := os.environ.get("OPS_ZIPKIN_URL"):
            if "zipkin" not in config_dict:
                config_dict["zipkin"] = {}
            config_dict["zipkin"]["url"] = zipkin_url

        return cls.model_validate(config_dict)

    @property
    def has_metrics_backend(self) -> bool:
        """Check if a metrics backend is configured."""
        return self.prometheus is not None

    @property
    def has_logs_backend(self) -> bool:
        """Check if a logs backend is configured."""
        return self.elasticsearch is not None or self.loki is not None

    @property
    def has_tracing_backend(self) -> bool:
        """Check if a tracing backend is configured."""
        return self.jaeger is not None or self.zipkin is not None

    @property
    def configured_backends(self) -> list[str]:
        """Get list of configured backend names."""
        backends = []
        if self.prometheus:
            backends.append("prometheus")
        if self.elasticsearch:
            backends.append("elasticsearch")
        if self.loki:
            backends.append("loki")
        if self.jaeger:
            backends.append("jaeger")
        if self.zipkin:
            backends.append("zipkin")
        return backends
