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
from system_operations_manager.integrations.kong.models.upstream import (
    Target,
    Upstream,
    UpstreamHealth,
)

__all__ = [
    # Consumer credentials
    "ACLGroup",
    # Enterprise: Vaults
    "AWSSecretsConfig",
    # Declarative config
    "ApplyOperation",
    # Plugins
    "AvailablePlugin",
    "AzureVaultConfig",
    "BasicAuthCredential",
    "ConfigDiff",
    "ConfigDiffSummary",
    "ConfigValidationError",
    "ConfigValidationResult",
    # Core entities
    "Consumer",
    "Credential",
    "DeclarativeConfig",
    "DevPortalFile",
    "DevPortalSpec",
    "DevPortalStatus",
    # Enterprise: Developer Portal
    "Developer",
    "EnvVaultConfig",
    "GCPSecretsConfig",
    "HMACAuthCredential",
    "HashiCorpVaultConfig",
    "HealthFailure",
    "JWTCredential",
    "KeyAuthCredential",
    # Base models
    "KongEntityBase",
    "KongEntityReference",
    "KongPluginEntity",
    # Observability
    "MetricsSummary",
    "NodeStatus",
    "OAuth2Credential",
    "PaginatedResponse",
    "PercentileMetrics",
    "PluginSchema",
    "PrometheusMetric",
    # Enterprise: RBAC
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
    "Upstream",
    "UpstreamHealth",
    "UpstreamHealthSummary",
    "Vault",
    # Enterprise: Workspaces
    "Workspace",
    "WorkspaceConfig",
]
