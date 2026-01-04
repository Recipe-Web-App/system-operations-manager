"""Kong API entity models.

This package contains Pydantic models for all Kong Admin API entities.
"""

from system_operations_manager.integrations.kong.models.base import (
    KongEntityBase,
    KongEntityReference,
    PaginatedResponse,
)
from system_operations_manager.integrations.kong.models.config import (
    ApplyOperation,
    ConfigDiff,
    ConfigDiffSummary,
    ConfigValidationError,
    ConfigValidationResult,
    DeclarativeConfig,
    HealthFailure,
    PercentileMetrics,
)
from system_operations_manager.integrations.kong.models.consumer import (
    ACLGroup,
    BasicAuthCredential,
    Consumer,
    Credential,
    HMACAuthCredential,
    JWTCredential,
    KeyAuthCredential,
    OAuth2Credential,
)
from system_operations_manager.integrations.kong.models.observability import (
    MetricsSummary,
    NodeStatus,
    PrometheusMetric,
    TargetHealthDetail,
    UpstreamHealthSummary,
)
from system_operations_manager.integrations.kong.models.plugin import (
    AvailablePlugin,
    KongPluginEntity,
    PluginSchema,
)
from system_operations_manager.integrations.kong.models.route import (
    Route,
    RouteSummary,
)
from system_operations_manager.integrations.kong.models.service import (
    Service,
    ServiceSummary,
)
from system_operations_manager.integrations.kong.models.upstream import (
    Target,
    Upstream,
    UpstreamHealth,
)

__all__ = [
    "ACLGroup",
    "ApplyOperation",
    "AvailablePlugin",
    "BasicAuthCredential",
    "ConfigDiff",
    "ConfigDiffSummary",
    "ConfigValidationError",
    "ConfigValidationResult",
    "Consumer",
    "Credential",
    "DeclarativeConfig",
    "HMACAuthCredential",
    "HealthFailure",
    "JWTCredential",
    "KeyAuthCredential",
    "KongEntityBase",
    "KongEntityReference",
    "KongPluginEntity",
    "MetricsSummary",
    "NodeStatus",
    "OAuth2Credential",
    "PaginatedResponse",
    "PercentileMetrics",
    "PluginSchema",
    "PrometheusMetric",
    "Route",
    "RouteSummary",
    "Service",
    "ServiceSummary",
    "Target",
    "TargetHealthDetail",
    "Upstream",
    "UpstreamHealth",
    "UpstreamHealthSummary",
]
