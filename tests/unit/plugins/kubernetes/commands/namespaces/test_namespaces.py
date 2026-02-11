"""Unit tests for Kubernetes namespace commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.namespaces import (
    register_namespace_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNamespaceCommands:
    """Tests for namespace CLI commands."""

    @pytest.fixture
    def app(self, get_namespace_cluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with namespace commands."""
        app = typer.Typer()
        register_namespace_commands(app, get_namespace_cluster_manager)
        return app

    def test_list_namespaces(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
        sample_namespace: MagicMock,
    ) -> None:
        """namespaces list should display namespaces."""
        mock_namespace_cluster_manager.list_namespaces.return_value = [sample_namespace]

        result = cli_runner.invoke(app, ["namespaces", "list"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.list_namespaces.assert_called_once()

    def test_list_namespaces_with_label_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """namespaces list -l should filter by label selector."""
        mock_namespace_cluster_manager.list_namespaces.return_value = []

        result = cli_runner.invoke(app, ["namespaces", "list", "-l", "env=production"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.list_namespaces.assert_called_once()

    def test_get_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
        sample_namespace: MagicMock,
    ) -> None:
        """namespaces get should display namespace details."""
        mock_namespace_cluster_manager.get_namespace.return_value = sample_namespace

        result = cli_runner.invoke(app, ["namespaces", "get", "test-namespace"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.get_namespace.assert_called_once_with("test-namespace")

    def test_create_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
        sample_namespace: MagicMock,
    ) -> None:
        """namespaces create should create namespace."""
        mock_namespace_cluster_manager.create_namespace.return_value = sample_namespace

        result = cli_runner.invoke(app, ["namespaces", "create", "my-namespace"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.create_namespace.assert_called_once()

    def test_create_namespace_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
        sample_namespace: MagicMock,
    ) -> None:
        """namespaces create should support label option."""
        mock_namespace_cluster_manager.create_namespace.return_value = sample_namespace

        result = cli_runner.invoke(
            app,
            ["namespaces", "create", "my-namespace", "-l", "env=dev", "-l", "team=platform"],
        )

        assert result.exit_code == 0
        mock_namespace_cluster_manager.create_namespace.assert_called_once()

    def test_delete_namespace_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """namespaces delete should delete namespace when confirmed."""
        result = cli_runner.invoke(app, ["namespaces", "delete", "my-namespace"], input="y\n")

        assert result.exit_code == 0
        mock_namespace_cluster_manager.delete_namespace.assert_called_once_with("my-namespace")

    def test_delete_namespace_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """namespaces delete --force should skip confirmation."""
        result = cli_runner.invoke(app, ["namespaces", "delete", "my-namespace", "--force"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.delete_namespace.assert_called_once_with("my-namespace")

    def test_namespace_not_found_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """namespace commands should handle not found error."""
        mock_namespace_cluster_manager.get_namespace.side_effect = KubernetesNotFoundError(
            resource_type="Namespace", resource_name="missing"
        )

        result = cli_runner.invoke(app, ["namespaces", "get", "missing"])

        assert result.exit_code == 1
