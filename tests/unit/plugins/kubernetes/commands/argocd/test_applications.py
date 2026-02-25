"""Unit tests for ArgoCD Application commands."""

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
class TestApplicationCommands:
    """Tests for ArgoCD Application commands."""

    @pytest.fixture
    def app(self, get_argocd_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with argocd commands."""
        app = typer.Typer()
        register_argocd_commands(app, get_argocd_manager)
        return app

    def test_list_applications(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """list should list Applications."""
        result = cli_runner.invoke(app, ["argocd", "app", "list"])

        assert result.exit_code == 0
        mock_argocd_manager.list_applications.assert_called_once_with(
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
        result = cli_runner.invoke(app, ["argocd", "app", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_argocd_manager.list_applications.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_list_with_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """list with --label-selector should pass selector."""
        result = cli_runner.invoke(app, ["argocd", "app", "list", "-l", "env=prod"])

        assert result.exit_code == 0
        mock_argocd_manager.list_applications.assert_called_once_with(
            namespace=None,
            label_selector="env=prod",
        )

    def test_get_application(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """get should retrieve an Application."""
        result = cli_runner.invoke(app, ["argocd", "app", "get", "my-app"])

        assert result.exit_code == 0
        mock_argocd_manager.get_application.assert_called_once_with("my-app", namespace=None)

    def test_get_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """get with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["argocd", "app", "get", "my-app", "-n", "production"])

        assert result.exit_code == 0
        mock_argocd_manager.get_application.assert_called_once_with(
            "my-app", namespace="production"
        )

    def test_create_application(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """create should create an Application."""
        result = cli_runner.invoke(
            app,
            [
                "argocd",
                "app",
                "create",
                "my-app",
                "--repo-url",
                "https://github.com/org/repo",
                "--path",
                "k8s",
            ],
        )

        assert result.exit_code == 0
        mock_argocd_manager.create_application.assert_called_once()
        call_kwargs = mock_argocd_manager.create_application.call_args
        assert call_kwargs.args[0] == "my-app"
        assert call_kwargs.kwargs["repo_url"] == "https://github.com/org/repo"
        assert call_kwargs.kwargs["path"] == "k8s"
        assert call_kwargs.kwargs["project"] == "default"
        assert call_kwargs.kwargs["target_revision"] == "HEAD"

    def test_create_with_auto_sync(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """create with --auto-sync should enable auto-sync."""
        result = cli_runner.invoke(
            app,
            [
                "argocd",
                "app",
                "create",
                "my-app",
                "--repo-url",
                "https://github.com/org/repo",
                "--path",
                "k8s",
                "--auto-sync",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_argocd_manager.create_application.call_args
        assert call_kwargs.kwargs["auto_sync"] is True

    def test_delete_application_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["argocd", "app", "delete", "my-app", "--force"])

        assert result.exit_code == 0
        mock_argocd_manager.delete_application.assert_called_once_with("my-app", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_delete_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """delete with --namespace should pass namespace."""
        result = cli_runner.invoke(
            app,
            ["argocd", "app", "delete", "my-app", "-n", "production", "--force"],
        )

        assert result.exit_code == 0
        mock_argocd_manager.delete_application.assert_called_once_with(
            "my-app", namespace="production"
        )

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_argocd_manager.get_application.side_effect = KubernetesNotFoundError(
            resource_type="Application", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["argocd", "app", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_create_with_project(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """create with --project should use custom project."""
        result = cli_runner.invoke(
            app,
            [
                "argocd",
                "app",
                "create",
                "my-app",
                "--repo-url",
                "https://github.com/org/repo",
                "--path",
                "k8s",
                "--project",
                "my-project",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_argocd_manager.create_application.call_args
        assert call_kwargs.kwargs["project"] == "my-project"

    def test_create_with_target_revision(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """create with --target-revision should use custom revision."""
        result = cli_runner.invoke(
            app,
            [
                "argocd",
                "app",
                "create",
                "my-app",
                "--repo-url",
                "https://github.com/org/repo",
                "--path",
                "k8s",
                "--target-revision",
                "v1.2.3",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_argocd_manager.create_application.call_args
        assert call_kwargs.kwargs["target_revision"] == "v1.2.3"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestApplicationCommandErrorPaths:
    """Tests for ArgoCD Application command error handling paths."""

    @pytest.fixture
    def app(self, get_argocd_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with argocd commands."""
        app = typer.Typer()
        register_argocd_commands(app, get_argocd_manager)
        return app

    def test_list_applications_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """list should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.list_applications.side_effect = KubernetesError(
            "Failed to list applications"
        )

        result = cli_runner.invoke(app, ["argocd", "app", "list"])

        assert result.exit_code == 1

    def test_create_application_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """create should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.create_application.side_effect = KubernetesError(
            "Failed to create application"
        )

        result = cli_runner.invoke(
            app,
            [
                "argocd",
                "app",
                "create",
                "my-app",
                "--repo-url",
                "https://github.com/org/repo",
                "--path",
                "k8s",
            ],
        )

        assert result.exit_code == 1

    def test_delete_application_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """delete without --force should exit when confirmation is declined."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.argocd.confirm_delete",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["argocd", "app", "delete", "my-app"])

        assert result.exit_code == 0
        mock_argocd_manager.delete_application.assert_not_called()

    def test_delete_application_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """delete should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.delete_application.side_effect = KubernetesError(
            "Failed to delete application"
        )

        result = cli_runner.invoke(app, ["argocd", "app", "delete", "my-app", "--force"])

        assert result.exit_code == 1

    def test_sync_application_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """sync should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.sync_application.side_effect = KubernetesError(
            "Failed to sync application"
        )

        result = cli_runner.invoke(app, ["argocd", "app", "sync", "my-app"])

        assert result.exit_code == 1

    def test_rollback_application_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """rollback should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.rollback_application.side_effect = KubernetesError(
            "Failed to rollback application"
        )

        result = cli_runner.invoke(app, ["argocd", "app", "rollback", "my-app"])

        assert result.exit_code == 1

    def test_application_health_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """health should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.get_application_health.side_effect = KubernetesError(
            "Failed to get application health"
        )

        result = cli_runner.invoke(app, ["argocd", "app", "health", "my-app"])

        assert result.exit_code == 1

    def test_application_diff_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """diff should handle KubernetesError and exit with code 1."""
        mock_argocd_manager.diff_application.side_effect = KubernetesError(
            "Failed to diff application"
        )

        result = cli_runner.invoke(app, ["argocd", "app", "diff", "my-app"])

        assert result.exit_code == 1
