"""Unit tests for Kubernetes deployment commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.workloads import (
    register_workload_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDeploymentCommands:
    """Tests for deployment CLI commands."""

    @pytest.fixture
    def app(self, get_workload_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workload commands."""
        app = typer.Typer()
        register_workload_commands(app, get_workload_manager)
        return app

    def test_list_deployments(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments list should display deployments."""
        mock_workload_manager.list_deployments.return_value = [sample_deployment]

        result = cli_runner.invoke(app, ["deployments", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_deployments.assert_called_once()

    def test_list_deployments_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """deployments list -n should filter by namespace."""
        mock_workload_manager.list_deployments.return_value = []

        result = cli_runner.invoke(app, ["deployments", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_workload_manager.list_deployments.assert_called_once()

    def test_get_deployment(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments get should display deployment details."""
        mock_workload_manager.get_deployment.return_value = sample_deployment

        result = cli_runner.invoke(app, ["deployments", "get", "test-deployment"])

        assert result.exit_code == 0
        mock_workload_manager.get_deployment.assert_called_once_with("test-deployment", None)

    def test_create_deployment(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments create should create deployment."""
        mock_workload_manager.create_deployment.return_value = sample_deployment

        result = cli_runner.invoke(
            app, ["deployments", "create", "my-app", "--image", "nginx:1.21"]
        )

        assert result.exit_code == 0
        mock_workload_manager.create_deployment.assert_called_once()

    def test_create_deployment_with_replicas(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments create should support replicas option."""
        mock_workload_manager.create_deployment.return_value = sample_deployment

        result = cli_runner.invoke(
            app,
            ["deployments", "create", "my-app", "--image", "nginx:1.21", "--replicas", "3"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_workload_manager.create_deployment.call_args[1]
        assert call_kwargs["replicas"] == 3

    def test_create_deployment_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments create should support label option."""
        mock_workload_manager.create_deployment.return_value = sample_deployment

        result = cli_runner.invoke(
            app,
            [
                "deployments",
                "create",
                "my-app",
                "--image",
                "nginx:1.21",
                "-l",
                "app=nginx",
                "-l",
                "env=prod",
            ],
        )

        assert result.exit_code == 0

    def test_update_deployment_image(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments update should update deployment image."""
        mock_workload_manager.update_deployment.return_value = sample_deployment

        result = cli_runner.invoke(
            app, ["deployments", "update", "my-app", "--image", "nginx:1.22"]
        )

        assert result.exit_code == 0
        mock_workload_manager.update_deployment.assert_called_once()

    def test_update_deployment_replicas(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments update should update deployment replicas."""
        mock_workload_manager.update_deployment.return_value = sample_deployment

        result = cli_runner.invoke(app, ["deployments", "update", "my-app", "--replicas", "5"])

        assert result.exit_code == 0
        call_kwargs = mock_workload_manager.update_deployment.call_args[1]
        assert call_kwargs["replicas"] == 5

    def test_delete_deployment_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """deployments delete --force should skip confirmation."""
        result = cli_runner.invoke(app, ["deployments", "delete", "my-app", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_deployment.assert_called_once_with("my-app", None)

    def test_scale_deployment(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments scale should scale deployment."""
        mock_workload_manager.scale_deployment.return_value = sample_deployment

        result = cli_runner.invoke(app, ["deployments", "scale", "my-app", "--replicas", "10"])

        assert result.exit_code == 0
        mock_workload_manager.scale_deployment.assert_called_once()

    def test_restart_deployment(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_deployment: MagicMock,
    ) -> None:
        """deployments restart should restart deployment."""
        mock_workload_manager.restart_deployment.return_value = sample_deployment

        result = cli_runner.invoke(app, ["deployments", "restart", "my-app"])

        assert result.exit_code == 0
        mock_workload_manager.restart_deployment.assert_called_once_with("my-app", None)

    def test_rollout_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """deployments rollout-status should show rollout status."""
        mock_workload_manager.get_rollout_status.return_value = {
            "status": "complete",
            "updated_replicas": 3,
        }

        result = cli_runner.invoke(app, ["deployments", "rollout-status", "my-app"])

        assert result.exit_code == 0
        mock_workload_manager.get_rollout_status.assert_called_once_with("my-app", None)

    def test_rollback_deployment(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """deployments rollback should rollback deployment."""
        result = cli_runner.invoke(app, ["deployments", "rollback", "my-app"])

        assert result.exit_code == 0
        mock_workload_manager.rollback_deployment.assert_called_once()

    def test_rollback_deployment_with_revision(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """deployments rollback should support revision option."""
        result = cli_runner.invoke(app, ["deployments", "rollback", "my-app", "--revision", "3"])

        assert result.exit_code == 0
        call_kwargs = mock_workload_manager.rollback_deployment.call_args[1]
        assert call_kwargs["revision"] == 3

    def test_deployment_not_found_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """deployment commands should handle not found error."""
        mock_workload_manager.get_deployment.side_effect = KubernetesNotFoundError(
            resource_type="Deployment", resource_name="missing"
        )

        result = cli_runner.invoke(app, ["deployments", "get", "missing"])

        assert result.exit_code == 1
