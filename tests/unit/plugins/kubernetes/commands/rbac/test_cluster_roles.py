"""Unit tests for Kubernetes cluster role commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.rbac import (
    register_rbac_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterRoleCommands:
    """Tests for cluster role commands."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with cluster role commands."""
        app = typer.Typer()
        register_rbac_commands(app, get_rbac_manager)
        return app

    def test_list_cluster_roles(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """list should list cluster roles."""
        mock_rbac_manager.list_cluster_roles.return_value = []

        result = cli_runner.invoke(app, ["cluster-roles", "list"])

        assert result.exit_code == 0
        mock_rbac_manager.list_cluster_roles.assert_called_once_with(label_selector=None)

    def test_get_cluster_role(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """get should retrieve a cluster role."""
        result = cli_runner.invoke(app, ["cluster-roles", "get", "test-cluster-role"])

        assert result.exit_code == 0
        mock_rbac_manager.get_cluster_role.assert_called_once_with("test-cluster-role")

    def test_create_cluster_role(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """create should create a cluster role."""
        rule_json = '{"verbs":["get","list"],"api_groups":[""],"resources":["nodes"]}'

        result = cli_runner.invoke(
            app, ["cluster-roles", "create", "test-cluster-role", "--rule", rule_json]
        )

        assert result.exit_code == 0
        mock_rbac_manager.create_cluster_role.assert_called_once()
        call_args = mock_rbac_manager.create_cluster_role.call_args
        assert call_args.args[0] == "test-cluster-role"
        assert len(call_args.kwargs["rules"]) == 1

    def test_delete_cluster_role_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["cluster-roles", "delete", "test-cluster-role", "--force"])

        assert result.exit_code == 0
        mock_rbac_manager.delete_cluster_role.assert_called_once_with("test-cluster-role")
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_rbac_manager.get_cluster_role.side_effect = KubernetesNotFoundError(
            resource_type="ClusterRole", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["cluster-roles", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
