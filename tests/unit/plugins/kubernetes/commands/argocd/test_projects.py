"""Unit tests for ArgoCD Project commands."""

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
from system_operations_manager.plugins.kubernetes.commands.argocd import (
    register_argocd_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestProjectCommands:
    """Tests for ArgoCD Project commands."""

    @pytest.fixture
    def app(self, get_argocd_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with argocd commands."""
        app = typer.Typer()
        register_argocd_commands(app, get_argocd_manager)
        return app

    def test_list_projects(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """list should list Projects."""
        result = cli_runner.invoke(app, ["argocd", "project", "list"])

        assert result.exit_code == 0
        mock_argocd_manager.list_projects.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["argocd", "project", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_argocd_manager.list_projects.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_get_project(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """get should retrieve a Project."""
        result = cli_runner.invoke(app, ["argocd", "project", "get", "my-project"])

        assert result.exit_code == 0
        mock_argocd_manager.get_project.assert_called_once_with("my-project", namespace=None)

    def test_create_project(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """create should create a Project."""
        result = cli_runner.invoke(
            app,
            [
                "argocd",
                "project",
                "create",
                "my-project",
                "--description",
                "Test project",
            ],
        )

        assert result.exit_code == 0
        mock_argocd_manager.create_project.assert_called_once()
        call_kwargs = mock_argocd_manager.create_project.call_args
        assert call_kwargs.args[0] == "my-project"
        assert call_kwargs.kwargs["description"] == "Test project"

    def test_delete_project_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["argocd", "project", "delete", "my-project", "--force"])

        assert result.exit_code == 0
        mock_argocd_manager.delete_project.assert_called_once_with("my-project", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_argocd_manager.get_project.side_effect = KubernetesNotFoundError(
            resource_type="AppProject", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["argocd", "project", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestProjectCommandErrorPaths:
    """Tests for ArgoCD Project command error handling paths."""

    @pytest.fixture
    def app(self, get_argocd_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with argocd commands."""
        app = typer.Typer()
        register_argocd_commands(app, get_argocd_manager)
        return app

    def test_list_projects_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """list projects should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.list_projects.side_effect = KubernetesError("Failed to list projects")

        result = cli_runner.invoke(app, ["argocd", "project", "list"])

        assert result.exit_code == 1

    def test_create_project_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """create project should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.create_project.side_effect = KubernetesError("Failed to create project")

        result = cli_runner.invoke(
            app,
            ["argocd", "project", "create", "my-project", "--description", "Test"],
        )

        assert result.exit_code == 1

    def test_delete_project_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """delete project without --force should exit when confirmation is declined."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.argocd.confirm_delete",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["argocd", "project", "delete", "my-project"])

        assert result.exit_code == 0
        mock_argocd_manager.delete_project.assert_not_called()

    def test_delete_project_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """delete project should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.delete_project.side_effect = KubernetesError("Failed to delete project")

        result = cli_runner.invoke(app, ["argocd", "project", "delete", "my-project", "--force"])

        assert result.exit_code == 1
