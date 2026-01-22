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
from system_operations_manager.integrations.kong.models.enterprise import (
    AWSSecretsConfig,
    AzureVaultConfig,
    Developer,
    DevPortalFile,
    DevPortalSpec,
    DevPortalStatus,
    EnvVaultConfig,
    GCPSecretsConfig,
    HashiCorpVaultConfig,
    RBACEndpointPermission,
    RBACRole,
    RBACUser,
    RBACUserRole,
    Vault,
    Workspace,
    WorkspaceConfig,
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
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
    detect_drift,
    merge_entities,
)
from system_operations_manager.integrations.kong.models.upstream import (
    Target,
    Upstream,
    UpstreamHealth,
)

__all__ = [
    "ACLGroup",
    "AWSSecretsConfig",
    "ApplyOperation",
    "AvailablePlugin",
    "AzureVaultConfig",
    "BasicAuthCredential",
    "ConfigDiff",
    "ConfigDiffSummary",
    "ConfigValidationError",
    "ConfigValidationResult",
    "Consumer",
    "Credential",
    "DeclarativeConfig",
    "DevPortalFile",
    "DevPortalSpec",
    "DevPortalStatus",
    "Developer",
    "EntitySource",
    "EnvVaultConfig",
    "GCPSecretsConfig",
    "HMACAuthCredential",
    "HashiCorpVaultConfig",
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
    "RBACEndpointPermission",
    "RBACRole",
    "RBACUser",
    "RBACUserRole",
    "Route",
    "RouteSummary",
    "Service",
    "ServiceSummary",
    "Target",
    "TargetHealthDetail",
    "UnifiedEntity",
    "UnifiedEntityList",
    "Upstream",
    "UpstreamHealth",
    "UpstreamHealthSummary",
    "Vault",
    "Workspace",
    "WorkspaceConfig",
    "detect_drift",
    "merge_entities",
]
