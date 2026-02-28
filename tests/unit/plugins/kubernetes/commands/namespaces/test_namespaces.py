"""Unit tests for Kubernetes namespace commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.namespaces import (
    _parse_labels,
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


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for _parse_labels helper."""

    def test_parse_labels_none_returns_none(self) -> None:
        """_parse_labels with None should return None."""
        result = _parse_labels(None)
        assert result is None

    def test_parse_labels_empty_list_returns_none(self) -> None:
        """_parse_labels with empty list should return None."""
        result = _parse_labels([])
        assert result is None

    def test_parse_labels_invalid_format_exits(self) -> None:
        """_parse_labels with invalid label format should raise Exit with code 1."""
        import click

        with pytest.raises(click.exceptions.Exit):
            _parse_labels(["invalid-label-without-equals"])

    def test_parse_labels_valid(self) -> None:
        """_parse_labels with valid labels should return a dict."""
        result = _parse_labels(["env=prod", "team=platform"])
        assert result == {"env": "prod", "team": "platform"}


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNamespaceCommandErrorPaths:
    """Tests for namespace CLI command error handling paths."""

    @pytest.fixture
    def app(self, get_namespace_cluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with namespace commands."""
        app = typer.Typer()
        register_namespace_commands(app, get_namespace_cluster_manager)
        return app

    def test_list_namespaces_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """list should handle KubernetesError and exit with code 1."""
        mock_namespace_cluster_manager.list_namespaces.side_effect = KubernetesError(
            "Failed to list namespaces"
        )

        result = cli_runner.invoke(app, ["namespaces", "list"])

        assert result.exit_code == 1

    def test_create_namespace_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """create should handle KubernetesError and exit with code 1."""
        mock_namespace_cluster_manager.create_namespace.side_effect = KubernetesError(
            "Failed to create namespace"
        )

        result = cli_runner.invoke(app, ["namespaces", "create", "my-namespace"])

        assert result.exit_code == 1

    def test_delete_namespace_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """delete without --force should abort when confirmation is declined."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.namespaces.confirm_delete",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["namespaces", "delete", "my-namespace"])

        assert result.exit_code != 0
        mock_namespace_cluster_manager.delete_namespace.assert_not_called()

    def test_delete_namespace_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """delete should handle KubernetesError and exit with code 1."""
        mock_namespace_cluster_manager.delete_namespace.side_effect = KubernetesError(
            "Failed to delete namespace"
        )

        result = cli_runner.invoke(app, ["namespaces", "delete", "my-namespace", "--force"])

        assert result.exit_code == 1
