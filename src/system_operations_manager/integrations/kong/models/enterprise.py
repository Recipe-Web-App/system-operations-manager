"""Kong Enterprise entity models.

This module provides Pydantic models for Kong Enterprise-only entities:
- Workspaces (multi-tenancy)
- RBAC (Role-Based Access Control)
- Vaults (secret management)
- Developer Portal
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kong.models.base import KongEntityBase

# =============================================================================
# Workspace Models
# =============================================================================


class WorkspaceConfig(BaseModel):
    """Workspace-specific configuration.

    Attributes:
        portal: Whether Developer Portal is enabled for this workspace.
        portal_auth: Portal authentication method.
        portal_cors_origins: Allowed CORS origins for portal.
    """

    model_config = ConfigDict(extra="allow")

    portal: bool = False
    portal_auth: str | None = None
    portal_cors_origins: list[str] | None = None


class Workspace(KongEntityBase):
    """Kong Enterprise workspace entity.

    Workspaces provide multi-tenancy by isolating Kong configurations.
    Each workspace has its own services, routes, consumers, and plugins.

    Attributes:
        name: Unique workspace name.
        comment: Optional description.
        config: Workspace-specific configuration.
        meta: Additional metadata.
    """

    _entity_name: ClassVar[str] = "workspace"

    name: str = Field(..., description="Unique workspace name")
    comment: str | None = Field(default=None, description="Workspace description")
    config: WorkspaceConfig | None = Field(default=None, description="Workspace configuration")
    meta: dict[str, Any] | None = Field(default=None, description="Additional metadata")


# =============================================================================
# RBAC Models
# =============================================================================


class RBACRole(KongEntityBase):
    """RBAC role entity.

    Roles define sets of permissions that can be assigned to users.

    Attributes:
        name: Unique role name.
        comment: Optional description.
        is_default: Whether this is a default system role.
    """

    _entity_name: ClassVar[str] = "rbac_role"

    name: str = Field(..., description="Unique role name")
    comment: str | None = Field(default=None, description="Role description")
    is_default: bool = Field(default=False, description="Whether this is a default role")


class RBACEndpointPermission(KongEntityBase):
    """RBAC endpoint permission entity.

    Defines what actions a role can perform on specific endpoints.

    Attributes:
        endpoint: API endpoint pattern (e.g., "/services/*").
        actions: Allowed actions (read, create, update, delete).
        negative: Whether this is a negative (deny) permission.
        workspace: Workspace this permission applies to.
        comment: Optional description.
    """

    _entity_name: ClassVar[str] = "rbac_permission"

    endpoint: str = Field(..., description="API endpoint pattern")
    actions: list[str] = Field(
        default_factory=list,
        description="Allowed actions: read, create, update, delete",
    )
    negative: bool = Field(default=False, description="Deny permission if true")
    workspace: str | None = Field(default=None, description="Workspace scope")
    comment: str | None = Field(default=None, description="Permission description")


RBACUserStatus = Literal["active", "invited", "disabled"]


class RBACUser(KongEntityBase):
    """RBAC admin user entity.

    Represents an administrator who can access Kong Admin API.

    Attributes:
        username: Unique username.
        custom_id: External ID reference.
        email: User email address.
        status: Account status (active, invited, disabled).
        rbac_token_enabled: Whether RBAC token is enabled.
        comment: Optional description.
    """

    _entity_name: ClassVar[str] = "rbac_user"

    username: str = Field(..., description="Unique username")
    custom_id: str | None = Field(default=None, description="External ID")
    email: str | None = Field(default=None, description="Email address")
    status: RBACUserStatus = Field(default="active", description="Account status")
    rbac_token_enabled: bool = Field(default=False, description="RBAC token enabled")
    comment: str | None = Field(default=None, description="User description")


class RBACUserRole(BaseModel):
    """RBAC user-role assignment.

    Represents the assignment of a role to a user.

    Attributes:
        user_id: User ID.
        role_id: Role ID.
        workspace: Workspace scope.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., description="User ID")
    role_id: str = Field(..., description="Role ID")
    workspace: str | None = Field(default=None, description="Workspace scope")


# =============================================================================
# Vault Models
# =============================================================================


VaultType = Literal["env", "hcv", "aws", "gcp", "azure"]


class Vault(KongEntityBase):
    """Kong Enterprise vault entity.

    Vaults provide secret management integration for Kong.
    Secrets can be referenced in plugin configurations using vault:// URIs.

    Attributes:
        name: Unique vault name.
        prefix: Vault prefix for secret references.
        description: Optional description.
        config: Vault-specific configuration.
    """

    _entity_name: ClassVar[str] = "vault"

    name: str = Field(..., description="Unique vault name")
    prefix: str = Field(..., description="Vault prefix for references")
    description: str | None = Field(default=None, description="Vault description")
    config: dict[str, Any] = Field(default_factory=dict, description="Vault configuration")


class HashiCorpVaultConfig(BaseModel):
    """HashiCorp Vault configuration.

    Attributes:
        host: Vault server hostname.
        port: Vault server port.
        protocol: HTTP or HTTPS.
        mount: Secret engine mount path.
        kv: Key-Value engine version (v1 or v2).
        token: Authentication token.
        namespace: Vault namespace.
        auth_method: Authentication method.
    """

    model_config = ConfigDict(extra="forbid")

    host: str = Field(..., description="Vault server hostname")
    port: int = Field(default=8200, description="Vault server port")
    protocol: Literal["http", "https"] = Field(default="https", description="Protocol")
    mount: str = Field(default="secret", description="Secret engine mount")
    kv: Literal["v1", "v2"] = Field(default="v2", description="KV engine version")
    token: str | None = Field(default=None, description="Auth token")
    namespace: str | None = Field(default=None, description="Vault namespace")
    auth_method: Literal["token", "approle", "kubernetes"] = Field(
        default="token",
        description="Authentication method",
    )


class AWSSecretsConfig(BaseModel):
    """AWS Secrets Manager configuration.

    Attributes:
        region: AWS region.
        endpoint_url: Custom endpoint URL (for LocalStack, etc.).
        role_arn: IAM role ARN to assume.
    """

    model_config = ConfigDict(extra="forbid")

    region: str = Field(..., description="AWS region")
    endpoint_url: str | None = Field(default=None, description="Custom endpoint URL")
    role_arn: str | None = Field(default=None, description="IAM role ARN")


class GCPSecretsConfig(BaseModel):
    """GCP Secret Manager configuration.

    Attributes:
        project_id: GCP project ID.
    """

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(..., description="GCP project ID")


class AzureVaultConfig(BaseModel):
    """Azure Key Vault configuration.

    Attributes:
        vault_uri: Azure Key Vault URI.
        client_id: Azure AD application ID.
        tenant_id: Azure AD tenant ID.
    """

    model_config = ConfigDict(extra="forbid")

    vault_uri: str = Field(..., description="Key Vault URI")
    client_id: str | None = Field(default=None, description="Azure AD app ID")
    tenant_id: str | None = Field(default=None, description="Azure AD tenant ID")


class EnvVaultConfig(BaseModel):
    """Environment variable vault configuration.

    Attributes:
        prefix: Environment variable prefix.
    """

    model_config = ConfigDict(extra="forbid")

    prefix: str = Field(default="KONG_", description="Environment variable prefix")


# =============================================================================
# Developer Portal Models
# =============================================================================


class DevPortalStatus(BaseModel):
    """Developer Portal status.

    Attributes:
        enabled: Whether the portal is enabled.
        portal_gui_host: Portal GUI hostname.
        portal_api_uri: Portal API URI.
        portal_auth: Authentication method.
        portal_auto_approve: Auto-approve developer registrations.
    """

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="Portal enabled")
    portal_gui_host: str | None = Field(default=None, description="Portal GUI host")
    portal_api_uri: str | None = Field(default=None, description="Portal API URI")
    portal_auth: str | None = Field(default=None, description="Auth method")
    portal_auto_approve: bool = Field(default=False, description="Auto-approve devs")


class DevPortalSpec(KongEntityBase):
    """API specification in Developer Portal.

    Represents an OpenAPI/Swagger specification published to the portal.

    Attributes:
        name: Unique specification name.
        path: File path in the portal.
        contents: Specification contents (YAML/JSON).
        service: Associated Kong service.
    """

    _entity_name: ClassVar[str] = "portal_spec"

    name: str = Field(..., description="Specification name")
    path: str = Field(..., description="File path")
    contents: str | None = Field(default=None, description="Spec contents")
    service: dict[str, str] | None = Field(default=None, description="Associated service")


class DevPortalFile(KongEntityBase):
    """File in Developer Portal.

    Represents a file stored in the Developer Portal.

    Attributes:
        name: File name.
        path: File path.
        type: File type (spec, partial, page).
        checksum: File checksum.
        contents: File contents.
    """

    _entity_name: ClassVar[str] = "portal_file"

    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path")
    type: Literal["spec", "partial", "page"] = Field(default="page", description="File type")
    checksum: str | None = Field(default=None, description="File checksum")
    contents: str | None = Field(default=None, description="File contents")


class Developer(KongEntityBase):
    """Developer Portal developer/user.

    Represents a developer registered in the portal.

    Attributes:
        email: Developer email (unique).
        custom_id: External ID reference.
        status: Account status.
        meta: Additional metadata.
    """

    _entity_name: ClassVar[str] = "developer"

    email: str = Field(..., description="Developer email")
    custom_id: str | None = Field(default=None, description="External ID")
    status: Literal["approved", "pending", "rejected", "revoked"] = Field(
        default="pending",
        description="Account status",
    )
    meta: dict[str, Any] | None = Field(default=None, description="Metadata")
