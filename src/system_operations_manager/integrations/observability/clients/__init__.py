"""Observability system clients.

Provides HTTP clients for external observability backends:
- Prometheus: Metrics queries
- Elasticsearch: Log search
- Loki: Log queries
- Jaeger: Distributed tracing
- Zipkin: Distributed tracing
"""

from system_operations_manager.integrations.observability.clients.base import (
    BaseObservabilityClient,
    ObservabilityAuthError,
    ObservabilityClientError,
    ObservabilityConnectionError,
    ObservabilityNotFoundError,
)
from system_operations_manager.integrations.observability.clients.elasticsearch import (
    ElasticsearchClient,
    ElasticsearchQueryError,
)
from system_operations_manager.integrations.observability.clients.jaeger import (
    JaegerClient,
    JaegerQueryError,
)
from system_operations_manager.integrations.observability.clients.loki import (
    LokiClient,
    LokiQueryError,
)
from system_operations_manager.integrations.observability.clients.prometheus import (
    PrometheusClient,
    PrometheusQueryError,
)
from system_operations_manager.integrations.observability.clients.zipkin import (
    ZipkinClient,
    ZipkinQueryError,
)

__all__ = [
    # Base
    "BaseObservabilityClient",
    # Elasticsearch
    "ElasticsearchClient",
    "ElasticsearchQueryError",
    # Jaeger
    "JaegerClient",
    "JaegerQueryError",
    # Loki
    "LokiClient",
    "LokiQueryError",
    "ObservabilityAuthError",
    "ObservabilityClientError",
    "ObservabilityConnectionError",
    "ObservabilityNotFoundError",
    # Prometheus
    "PrometheusClient",
    "PrometheusQueryError",
    # Zipkin
    "ZipkinClient",
    "ZipkinQueryError",
]
