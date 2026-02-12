"""Shared fixtures for Kubernetes RBAC command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_rbac_manager() -> MagicMock:
    """Create a mock RBACManager."""
    manager = MagicMock()

    # Service Accounts
    manager.list_service_accounts.return_value = []
    manager.get_service_account.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-sa",
            "namespace": "default",
            "secrets_count": 1,
        }
    )
    manager.create_service_account.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-sa", "namespace": "default"}
    )
    manager.delete_service_account.return_value = None

    # Roles
    manager.list_roles.return_value = []
    manager.get_role.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-role",
            "namespace": "default",
            "rules_count": 1,
        }
    )
    manager.create_role.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-role", "namespace": "default"}
    )
    manager.delete_role.return_value = None

    # Cluster Roles
    manager.list_cluster_roles.return_value = []
    manager.get_cluster_role.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-cluster-role", "rules_count": 1}
    )
    manager.create_cluster_role.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-cluster-role"}
    )
    manager.delete_cluster_role.return_value = None

    # Role Bindings
    manager.list_role_bindings.return_value = []
    manager.get_role_binding.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-rb",
            "namespace": "default",
            "role_ref_name": "test-role",
        }
    )
    manager.create_role_binding.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-rb", "namespace": "default"}
    )
    manager.delete_role_binding.return_value = None

    # Cluster Role Bindings
    manager.list_cluster_role_bindings.return_value = []
    manager.get_cluster_role_binding.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-crb", "role_ref_name": "test-cluster-role"}
    )
    manager.create_cluster_role_binding.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-crb"}
    )
    manager.delete_cluster_role_binding.return_value = None

    return manager


@pytest.fixture
def get_rbac_manager(mock_rbac_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock RBAC manager."""
    return lambda: mock_rbac_manager
