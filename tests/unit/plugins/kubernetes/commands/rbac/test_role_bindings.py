"""Unit tests for Kubernetes role binding commands."""

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
class TestRoleBindingCommands:
    """Tests for role binding commands."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with role binding commands."""
        app = typer.Typer()
        register_rbac_commands(app, get_rbac_manager)
        return app

    def test_list_role_bindings(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """list should list role bindings."""
        mock_rbac_manager.list_role_bindings.return_value = []

        result = cli_runner.invoke(app, ["role-bindings", "list"])

        assert result.exit_code == 0
        mock_rbac_manager.list_role_bindings.assert_called_once_with(
            namespace=None, label_selector=None
        )

    def test_get_role_binding(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """get should retrieve a role binding."""
        result = cli_runner.invoke(app, ["role-bindings", "get", "test-rb"])

        assert result.exit_code == 0
        mock_rbac_manager.get_role_binding.assert_called_once_with("test-rb", namespace=None)

    def test_create_role_binding(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """create should create a role binding."""
        role_ref_json = (
            '{"kind":"Role","name":"pod-reader","api_group":"rbac.authorization.k8s.io"}'
        )
        subject_json = '{"kind":"User","name":"jane"}'

        result = cli_runner.invoke(
            app,
            [
                "role-bindings",
                "create",
                "test-rb",
                "--role-ref",
                role_ref_json,
                "--subject",
                subject_json,
            ],
        )

        assert result.exit_code == 0
        mock_rbac_manager.create_role_binding.assert_called_once()
        call_args = mock_rbac_manager.create_role_binding.call_args
        assert call_args.args[0] == "test-rb"
        assert call_args.kwargs["role_ref"]["kind"] == "Role"
        assert len(call_args.kwargs["subjects"]) == 1

    def test_delete_role_binding_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["role-bindings", "delete", "test-rb", "--force"])

        assert result.exit_code == 0
        mock_rbac_manager.delete_role_binding.assert_called_once_with("test-rb", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_list_role_bindings_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """list should handle KubernetesError."""
        mock_rbac_manager.list_role_bindings.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["role-bindings", "list"])

        assert result.exit_code == 1

    def test_get_role_binding_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """get should handle KubernetesError."""
        mock_rbac_manager.get_role_binding.side_effect = KubernetesNotFoundError(
            resource_type="RoleBinding", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["role-bindings", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_create_role_binding_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """create should handle KubernetesError."""
        mock_rbac_manager.create_role_binding.side_effect = KubernetesError("connection failed")
        role_ref_json = (
            '{"kind":"Role","name":"pod-reader","api_group":"rbac.authorization.k8s.io"}'
        )

        result = cli_runner.invoke(
            app,
            ["role-bindings", "create", "test-rb", "--role-ref", role_ref_json],
        )

        assert result.exit_code == 1

    def test_delete_role_binding_aborts_without_confirmation(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete without --force should abort when user declines."""
        result = cli_runner.invoke(app, ["role-bindings", "delete", "test-rb"], input="n\n")

        assert result.exit_code != 0
        mock_rbac_manager.delete_role_binding.assert_not_called()

    def test_delete_role_binding_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete should handle KubernetesError."""
        mock_rbac_manager.delete_role_binding.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["role-bindings", "delete", "test-rb", "--force"])

        assert result.exit_code == 1
