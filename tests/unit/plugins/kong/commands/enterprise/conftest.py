"""Shared fixtures for Kong enterprise command tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.models.enterprise import (
    Developer,
    DevPortalSpec,
    DevPortalStatus,
    RBACEndpointPermission,
    RBACRole,
    RBACUser,
    Vault,
    Workspace,
)


def _create_mock_entity(data: dict[str, Any]) -> MagicMock:
    """Create a mock entity that behaves like a Pydantic model.

    The formatter calls model_dump() on entities, so we need mocks
    that support this interface.
    """
    mock = MagicMock()
    mock.model_dump.return_value = data
    # Also set attributes for direct access
    for key, value in data.items():
        setattr(mock, key, value)
    return mock


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


# =========================================================================
# Workspace Manager Fixtures
# =========================================================================


@pytest.fixture
def mock_workspace_manager() -> MagicMock:
    """Create a mock WorkspaceManager."""
    manager = MagicMock()

    # Default workspace for operations
    default_workspace = Workspace(id="ws-1", name="default", comment="Default workspace")

    # Configure return values
    manager.list.return_value = (
        [
            Workspace(id="ws-1", name="default", comment="Default workspace"),
            Workspace(id="ws-2", name="production", comment="Production environment"),
        ],
        None,
    )
    manager.get.return_value = default_workspace
    manager.get_current.return_value = default_workspace
    manager.current_workspace = "default"
    manager.create_with_config.return_value = Workspace(
        id="ws-new", name="staging", comment="Staging environment"
    )
    manager.switch_context.return_value = Workspace(
        id="ws-2", name="production", comment="Production environment"
    )
    manager.update.return_value = Workspace(id="ws-1", name="default", comment="Updated comment")
    manager.get_entities_count.return_value = {
        "services": 5,
        "routes": 10,
        "consumers": 3,
    }
    manager.delete.return_value = None

    return manager


@pytest.fixture
def get_workspace_manager(mock_workspace_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock workspace manager."""
    return lambda: mock_workspace_manager


# =========================================================================
# RBAC Manager Fixtures
# =========================================================================


@pytest.fixture
def mock_rbac_manager() -> MagicMock:
    """Create a mock RBACManager."""
    manager = MagicMock()

    # Role operations
    manager.list_roles.return_value = (
        [
            RBACRole(id="role-1", name="admin", comment="Full access"),
            RBACRole(id="role-2", name="developer", comment="Developer access"),
        ],
        None,
    )
    manager.get_role.return_value = RBACRole(id="role-1", name="admin", comment="Full access")
    manager.create_role.return_value = RBACRole(
        id="role-new", name="api-developer", comment="API developer access"
    )
    manager.update_role.return_value = RBACRole(
        id="role-1", name="admin", comment="Updated description"
    )
    manager.delete_role.return_value = None

    # Permission operations
    manager.list_role_permissions.return_value = [
        RBACEndpointPermission(id="perm-1", endpoint="/services/*", actions=["read", "create"]),
        RBACEndpointPermission(id="perm-2", endpoint="/routes/*", actions=["read"]),
    ]
    manager.add_role_permission.return_value = RBACEndpointPermission(
        id="perm-new", endpoint="/consumers/*", actions=["read", "create", "update", "delete"]
    )
    manager.remove_role_permission.return_value = None

    # User operations
    manager.list_users.return_value = (
        [
            RBACUser(id="user-1", username="alice", email="alice@example.com"),
            RBACUser(id="user-2", username="bob", email="bob@example.com"),
        ],
        None,
    )
    manager.get_user.return_value = RBACUser(
        id="user-1", username="alice", email="alice@example.com"
    )
    manager.create_user.return_value = RBACUser(
        id="user-new", username="charlie", email="charlie@example.com"
    )
    manager.update_user.return_value = RBACUser(
        id="user-1", username="alice", email="newemail@example.com"
    )
    manager.delete_user.return_value = None

    # Role assignment operations
    manager.list_user_roles.return_value = [
        RBACRole(id="role-1", name="admin", comment="Full access"),
    ]
    manager.assign_role.return_value = None
    manager.revoke_role.return_value = None
    manager.role_exists.return_value = True
    manager.user_exists.return_value = True

    return manager


@pytest.fixture
def get_rbac_manager(mock_rbac_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock RBAC manager."""
    return lambda: mock_rbac_manager


# =========================================================================
# Portal Manager Fixtures
# =========================================================================


@pytest.fixture
def mock_portal_manager() -> MagicMock:
    """Create a mock PortalManager."""
    manager = MagicMock()

    # Status operations
    manager.get_status.return_value = DevPortalStatus(
        enabled=True,
        portal_gui_host="portal.example.com",
        portal_api_uri="https://api.example.com",
        portal_auth="basic-auth",
        portal_auto_approve=False,
    )
    manager.is_enabled.return_value = True

    # Spec operations
    manager.list_specs.return_value = (
        [
            DevPortalSpec(id="spec-1", name="users-api", path="specs/users.yaml"),
            DevPortalSpec(id="spec-2", name="orders-api", path="specs/orders.yaml"),
        ],
        None,
    )
    manager.get_spec.return_value = DevPortalSpec(
        id="spec-1",
        name="users-api",
        path="specs/users.yaml",
        contents="openapi: 3.0.0",
    )
    manager.publish_spec.return_value = DevPortalSpec(
        id="spec-new", name="new-api", path="specs/new-api.yaml"
    )
    manager.update_spec.return_value = DevPortalSpec(
        id="spec-1", name="users-api", path="specs/users.yaml"
    )
    manager.delete_spec.return_value = None

    # Developer operations
    manager.list_developers.return_value = (
        [
            Developer(id="dev-1", email="alice@example.com", status="approved"),
            Developer(id="dev-2", email="bob@example.com", status="pending"),
        ],
        None,
    )
    manager.get_developer.return_value = Developer(
        id="dev-1", email="alice@example.com", status="approved"
    )
    manager.approve_developer.return_value = Developer(
        id="dev-2", email="bob@example.com", status="approved"
    )
    manager.reject_developer.return_value = Developer(
        id="dev-2", email="bob@example.com", status="rejected"
    )
    manager.revoke_developer.return_value = Developer(
        id="dev-1", email="alice@example.com", status="revoked"
    )
    manager.delete_developer.return_value = None

    return manager


@pytest.fixture
def get_portal_manager(mock_portal_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock portal manager."""
    return lambda: mock_portal_manager


# =========================================================================
# Vault Manager Fixtures
# =========================================================================


@pytest.fixture
def mock_vault_manager() -> MagicMock:
    """Create a mock VaultManager."""
    manager = MagicMock()

    # List/Get operations
    manager.list.return_value = (
        [
            Vault(
                id="vault-1", name="hcv-prod", prefix="hcv", config={"host": "vault.example.com"}
            ),
            Vault(id="vault-2", name="aws-secrets", prefix="aws", config={"region": "us-east-1"}),
        ],
        None,
    )
    manager.get.return_value = Vault(
        id="vault-1",
        name="hcv-prod",
        prefix="hcv",
        config={"host": "vault.example.com", "mount": "secret"},
    )

    # Configure operations
    manager.configure_hcv.return_value = Vault(
        id="vault-new",
        name="new-hcv",
        prefix="new-hcv",
        config={"host": "vault.example.com", "mount": "secret"},
    )
    manager.configure_aws.return_value = Vault(
        id="vault-new",
        name="new-aws",
        prefix="new-aws",
        config={"region": "us-west-2"},
    )
    manager.configure_gcp.return_value = Vault(
        id="vault-new",
        name="new-gcp",
        prefix="new-gcp",
        config={"project_id": "my-project"},
    )
    manager.configure_azure.return_value = Vault(
        id="vault-new",
        name="new-azure",
        prefix="new-azure",
        config={"vault_uri": "https://myvault.vault.azure.net"},
    )
    manager.configure_env.return_value = Vault(
        id="vault-new",
        name="new-env",
        prefix="new-env",
        config={"prefix": "KONG_SECRET_"},
    )

    # Other operations
    manager.delete.return_value = None
    manager.get_vault_type.return_value = "hcv"
    manager.test_vault_connection.return_value = True

    return manager


@pytest.fixture
def get_vault_manager(mock_vault_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock vault manager."""
    return lambda: mock_vault_manager


# =========================================================================
# App Creation Helpers
# =========================================================================


def create_enterprise_app(
    register_func: Callable[..., None],
    *manager_factories: Callable[[], Any],
) -> typer.Typer:
    """Helper to create a Typer app with registered enterprise commands.

    Args:
        register_func: The command registration function.
        *manager_factories: Factory functions for managers.

    Returns:
        Configured Typer app for testing.
    """
    app = typer.Typer()
    register_func(app, *manager_factories)
    return app
