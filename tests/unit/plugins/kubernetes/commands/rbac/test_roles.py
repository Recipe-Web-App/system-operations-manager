"""Unit tests for Kubernetes role commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.rbac import (
    register_rbac_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRoleCommands:
    """Tests for role commands."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with role commands."""
        app = typer.Typer()
        register_rbac_commands(app, get_rbac_manager)
        return app

    def test_list_roles(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """list should list roles."""
        mock_rbac_manager.list_roles.return_value = []

        result = cli_runner.invoke(app, ["roles", "list"])

        assert result.exit_code == 0
        mock_rbac_manager.list_roles.assert_called_once_with(namespace=None, label_selector=None)

    def test_get_role(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """get should retrieve a role."""
        result = cli_runner.invoke(app, ["roles", "get", "test-role"])

        assert result.exit_code == 0
        mock_rbac_manager.get_role.assert_called_once_with("test-role", namespace=None)

    def test_create_role(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """create should create a role."""
        rule_json = '{"verbs":["get","list"],"api_groups":[""],"resources":["pods"]}'

        result = cli_runner.invoke(app, ["roles", "create", "test-role", "--rule", rule_json])

        assert result.exit_code == 0
        mock_rbac_manager.create_role.assert_called_once()
        call_args = mock_rbac_manager.create_role.call_args
        assert call_args.args[0] == "test-role"
        assert len(call_args.kwargs["rules"]) == 1

    def test_delete_role_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["roles", "delete", "test-role", "--force"])

        assert result.exit_code == 0
        mock_rbac_manager.delete_role.assert_called_once_with("test-role", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_rbac_manager.get_role.side_effect = KubernetesNotFoundError(
            resource_type="Role", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["roles", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_list_roles_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """list should handle KubernetesError."""
        mock_rbac_manager.list_roles.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["roles", "list"])

        assert result.exit_code == 1

    def test_create_role_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """create should handle KubernetesError."""
        mock_rbac_manager.create_role.side_effect = KubernetesError("connection failed")
        rule_json = '{"verbs":["get"],"api_groups":[""],"resources":["pods"]}'

        result = cli_runner.invoke(app, ["roles", "create", "test-role", "--rule", rule_json])

        assert result.exit_code == 1

    def test_delete_role_aborts_without_confirmation(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete without --force should abort when user declines."""
        result = cli_runner.invoke(app, ["roles", "delete", "test-role"], input="n\n")

        assert result.exit_code != 0
        mock_rbac_manager.delete_role.assert_not_called()

    def test_delete_role_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete should handle KubernetesError."""
        mock_rbac_manager.delete_role.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["roles", "delete", "test-role", "--force"])

        assert result.exit_code == 1
