"""Unit tests for Kong enterprise models."""

from __future__ import annotations

import pytest

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


class TestWorkspace:
    """Tests for Workspace model."""

    @pytest.mark.unit
    def test_create_workspace(self) -> None:
        """Should create workspace with name."""
        workspace = Workspace(name="production")

        assert workspace.name == "production"
        assert workspace.comment is None
        assert workspace.config is None

    @pytest.mark.unit
    def test_create_workspace_with_comment(self) -> None:
        """Should create workspace with comment."""
        workspace = Workspace(
            name="staging",
            comment="Staging environment",
        )

        assert workspace.name == "staging"
        assert workspace.comment == "Staging environment"

    @pytest.mark.unit
    def test_create_workspace_with_config(self) -> None:
        """Should create workspace with config."""
        config = WorkspaceConfig(portal=True, portal_auth="basic-auth")
        workspace = Workspace(
            name="portal-ws",
            config=config,
        )

        assert workspace.config is not None
        assert workspace.config.portal is True


class TestWorkspaceConfig:
    """Tests for WorkspaceConfig model."""

    @pytest.mark.unit
    def test_create_config(self) -> None:
        """Should create workspace config."""
        config = WorkspaceConfig(
            portal=True,
            portal_auth="key-auth",
            portal_cors_origins=["https://example.com"],
        )

        assert config.portal is True
        assert config.portal_auth == "key-auth"
        assert config.portal_cors_origins == ["https://example.com"]

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values."""
        config = WorkspaceConfig()

        assert config.portal is False
        assert config.portal_auth is None


class TestRBACRole:
    """Tests for RBACRole model."""

    @pytest.mark.unit
    def test_create_role(self) -> None:
        """Should create role with name."""
        role = RBACRole(name="admin")

        assert role.name == "admin"
        assert role.comment is None
        assert role.is_default is False

    @pytest.mark.unit
    def test_create_default_role(self) -> None:
        """Should create default role."""
        role = RBACRole(
            name="super-admin",
            comment="Full access",
            is_default=True,
        )

        assert role.is_default is True
        assert role.comment == "Full access"


class TestRBACEndpointPermission:
    """Tests for RBACEndpointPermission model."""

    @pytest.mark.unit
    def test_create_permission(self) -> None:
        """Should create permission."""
        perm = RBACEndpointPermission(
            endpoint="/services/*",
            actions=["read", "create", "update", "delete"],
        )

        assert perm.endpoint == "/services/*"
        assert len(perm.actions) == 4
        assert perm.negative is False

    @pytest.mark.unit
    def test_create_deny_permission(self) -> None:
        """Should create deny permission."""
        perm = RBACEndpointPermission(
            endpoint="/admin/*",
            actions=["read"],
            negative=True,
        )

        assert perm.negative is True


class TestRBACUser:
    """Tests for RBACUser model."""

    @pytest.mark.unit
    def test_create_user(self) -> None:
        """Should create user with username."""
        user = RBACUser(username="alice")

        assert user.username == "alice"
        assert user.status == "active"
        assert user.email is None

    @pytest.mark.unit
    def test_create_user_with_email(self) -> None:
        """Should create user with email."""
        user = RBACUser(
            username="bob",
            email="bob@example.com",
            status="invited",
        )

        assert user.email == "bob@example.com"
        assert user.status == "invited"


class TestRBACUserRole:
    """Tests for RBACUserRole model."""

    @pytest.mark.unit
    def test_create_user_role(self) -> None:
        """Should create user-role assignment."""
        assignment = RBACUserRole(
            user_id="user-123",
            role_id="role-456",
            workspace="production",
        )

        assert assignment.user_id == "user-123"
        assert assignment.role_id == "role-456"
        assert assignment.workspace == "production"


class TestVault:
    """Tests for Vault model."""

    @pytest.mark.unit
    def test_create_vault(self) -> None:
        """Should create vault."""
        vault = Vault(
            name="hcv-prod",
            prefix="hcv",
            config={"host": "vault.example.com"},
        )

        assert vault.name == "hcv-prod"
        assert vault.prefix == "hcv"
        assert vault.config["host"] == "vault.example.com"

    @pytest.mark.unit
    def test_create_vault_with_description(self) -> None:
        """Should create vault with description."""
        vault = Vault(
            name="aws-secrets",
            prefix="aws",
            description="Production AWS secrets",
            config={"region": "us-east-1"},
        )

        assert vault.description == "Production AWS secrets"


class TestHashiCorpVaultConfig:
    """Tests for HashiCorpVaultConfig model."""

    @pytest.mark.unit
    def test_create_config(self) -> None:
        """Should create HCV config."""
        config = HashiCorpVaultConfig(
            host="vault.example.com",
            mount="secret",
        )

        assert config.host == "vault.example.com"
        assert config.port == 8200
        assert config.protocol == "https"
        assert config.kv == "v2"
        assert config.auth_method == "token"

    @pytest.mark.unit
    def test_create_config_with_all_options(self) -> None:
        """Should create config with all options."""
        config = HashiCorpVaultConfig(
            host="vault.example.com",
            port=8201,
            protocol="http",
            mount="kv",
            kv="v1",
            token="s.xxx",
            namespace="admin",
            auth_method="kubernetes",
        )

        assert config.port == 8201
        assert config.protocol == "http"
        assert config.token == "s.xxx"


class TestAWSSecretsConfig:
    """Tests for AWSSecretsConfig model."""

    @pytest.mark.unit
    def test_create_config(self) -> None:
        """Should create AWS config."""
        config = AWSSecretsConfig(region="us-east-1")

        assert config.region == "us-east-1"
        assert config.endpoint_url is None
        assert config.role_arn is None

    @pytest.mark.unit
    def test_create_config_with_role(self) -> None:
        """Should create config with role ARN."""
        config = AWSSecretsConfig(
            region="us-west-2",
            role_arn="arn:aws:iam::123456789:role/vault",
        )

        assert config.role_arn is not None


class TestGCPSecretsConfig:
    """Tests for GCPSecretsConfig model."""

    @pytest.mark.unit
    def test_create_config(self) -> None:
        """Should create GCP config."""
        config = GCPSecretsConfig(project_id="my-project")

        assert config.project_id == "my-project"


class TestAzureVaultConfig:
    """Tests for AzureVaultConfig model."""

    @pytest.mark.unit
    def test_create_config(self) -> None:
        """Should create Azure config."""
        config = AzureVaultConfig(vault_uri="https://myvault.vault.azure.net")

        assert config.vault_uri == "https://myvault.vault.azure.net"
        assert config.client_id is None
        assert config.tenant_id is None

    @pytest.mark.unit
    def test_create_config_with_credentials(self) -> None:
        """Should create config with credentials."""
        config = AzureVaultConfig(
            vault_uri="https://myvault.vault.azure.net",
            client_id="client-123",
            tenant_id="tenant-456",
        )

        assert config.client_id == "client-123"
        assert config.tenant_id == "tenant-456"


class TestEnvVaultConfig:
    """Tests for EnvVaultConfig model."""

    @pytest.mark.unit
    def test_create_config(self) -> None:
        """Should create env vault config."""
        config = EnvVaultConfig(prefix="KONG_SECRET_")

        assert config.prefix == "KONG_SECRET_"

    @pytest.mark.unit
    def test_default_prefix(self) -> None:
        """Should use default prefix."""
        config = EnvVaultConfig()

        assert config.prefix == "KONG_"


class TestDevPortalStatus:
    """Tests for DevPortalStatus model."""

    @pytest.mark.unit
    def test_create_enabled_status(self) -> None:
        """Should create enabled status."""
        status = DevPortalStatus(
            enabled=True,
            portal_gui_host="portal.example.com",
            portal_api_uri="https://api.example.com",
            portal_auth="basic-auth",
            portal_auto_approve=True,
        )

        assert status.enabled is True
        assert status.portal_gui_host == "portal.example.com"
        assert status.portal_auto_approve is True

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values."""
        status = DevPortalStatus()

        assert status.enabled is False
        assert status.portal_auto_approve is False


class TestDevPortalSpec:
    """Tests for DevPortalSpec model."""

    @pytest.mark.unit
    def test_create_spec(self) -> None:
        """Should create spec."""
        spec = DevPortalSpec(
            name="users-api",
            path="specs/users.yaml",
            contents="openapi: 3.0.0",
        )

        assert spec.name == "users-api"
        assert spec.path == "specs/users.yaml"
        assert spec.contents == "openapi: 3.0.0"


class TestDevPortalFile:
    """Tests for DevPortalFile model."""

    @pytest.mark.unit
    def test_create_file(self) -> None:
        """Should create file."""
        file = DevPortalFile(
            name="header",
            path="partials/header.html",
            type="partial",
        )

        assert file.name == "header"
        assert file.type == "partial"

    @pytest.mark.unit
    def test_default_type(self) -> None:
        """Should use default type."""
        file = DevPortalFile(name="home", path="pages/home.html")

        assert file.type == "page"


class TestDeveloper:
    """Tests for Developer model."""

    @pytest.mark.unit
    def test_create_developer(self) -> None:
        """Should create developer."""
        dev = Developer(email="alice@example.com")

        assert dev.email == "alice@example.com"
        assert dev.status == "pending"

    @pytest.mark.unit
    def test_create_approved_developer(self) -> None:
        """Should create approved developer."""
        dev = Developer(
            email="bob@example.com",
            status="approved",
            custom_id="ext-123",
        )

        assert dev.status == "approved"
        assert dev.custom_id == "ext-123"
