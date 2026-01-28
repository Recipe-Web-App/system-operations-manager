"""Observability integrations for external monitoring systems.

This package provides HTTP clients for external observability systems:
- Prometheus (metrics)
- Elasticsearch (logs)
- Loki (logs)
- Jaeger (traces)
- Zipkin (traces)
"""

from system_operations_manager.integrations.observability.clients import (
    BaseObservabilityClient,
    ElasticsearchClient,
    JaegerClient,
    LokiClient,
    ObservabilityAuthError,
    ObservabilityClientError,
    ObservabilityConnectionError,
    ObservabilityNotFoundError,
    PrometheusClient,
    ZipkinClient,
)
from system_operations_manager.integrations.observability.config import (
    ElasticsearchConfig,
    JaegerConfig,
    LokiConfig,
    ObservabilityStackConfig,
    PrometheusConfig,
    ZipkinConfig,
)

__all__ = [
    # Base client and errors
    "BaseObservabilityClient",
    # Clients
    "ElasticsearchClient",
    # Config
    "ElasticsearchConfig",
    "JaegerClient",
    "JaegerConfig",
    "LokiClient",
    "LokiConfig",
    "ObservabilityAuthError",
    "ObservabilityClientError",
    "ObservabilityConnectionError",
    "ObservabilityNotFoundError",
    "ObservabilityStackConfig",
    "PrometheusClient",
    "PrometheusConfig",
    "ZipkinClient",
    "ZipkinConfig",
]
