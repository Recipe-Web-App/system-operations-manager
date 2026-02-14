"""Unit tests for Kubernetes cluster role binding commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.rbac import (
    register_rbac_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterRoleBindingCommands:
    """Tests for cluster role binding commands."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with cluster role binding commands."""
        app = typer.Typer()
        register_rbac_commands(app, get_rbac_manager)
        return app

    def test_list_cluster_role_bindings(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """list should list cluster role bindings."""
        mock_rbac_manager.list_cluster_role_bindings.return_value = []

        result = cli_runner.invoke(app, ["cluster-role-bindings", "list"])

        assert result.exit_code == 0
        mock_rbac_manager.list_cluster_role_bindings.assert_called_once_with(label_selector=None)

    def test_get_cluster_role_binding(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """get should retrieve a cluster role binding."""
        result = cli_runner.invoke(app, ["cluster-role-bindings", "get", "test-crb"])

        assert result.exit_code == 0
        mock_rbac_manager.get_cluster_role_binding.assert_called_once_with("test-crb")

    def test_create_cluster_role_binding(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """create should create a cluster role binding."""
        role_ref_json = (
            '{"kind":"ClusterRole","name":"cluster-admin","api_group":"rbac.authorization.k8s.io"}'
        )
        subject_json = '{"kind":"User","name":"admin"}'

        result = cli_runner.invoke(
            app,
            [
                "cluster-role-bindings",
                "create",
                "test-crb",
                "--role-ref",
                role_ref_json,
                "--subject",
                subject_json,
            ],
        )

        assert result.exit_code == 0
        mock_rbac_manager.create_cluster_role_binding.assert_called_once()
        call_args = mock_rbac_manager.create_cluster_role_binding.call_args
        assert call_args.args[0] == "test-crb"
        assert call_args.kwargs["role_ref"]["kind"] == "ClusterRole"
        assert len(call_args.kwargs["subjects"]) == 1

    def test_delete_cluster_role_binding_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["cluster-role-bindings", "delete", "test-crb", "--force"])

        assert result.exit_code == 0
        mock_rbac_manager.delete_cluster_role_binding.assert_called_once_with("test-crb")
        assert "deleted" in result.stdout.lower()
