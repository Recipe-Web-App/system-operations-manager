"""Unit tests for Kubernetes job commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.jobs import (
    register_job_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestJobCommands:
    """Tests for job commands."""

    @pytest.fixture
    def app(self, get_job_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with job commands."""
        app = typer.Typer()
        register_job_commands(app, get_job_manager)
        return app

    def test_list_jobs(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """list should list jobs."""
        mock_job_manager.list_jobs.return_value = []

        result = cli_runner.invoke(app, ["jobs", "list"])

        assert result.exit_code == 0
        mock_job_manager.list_jobs.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_list_jobs_with_namespace(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """list should accept namespace parameter."""
        mock_job_manager.list_jobs.return_value = []

        result = cli_runner.invoke(app, ["jobs", "list", "-n", "kube-system"])

        assert result.exit_code == 0
        mock_job_manager.list_jobs.assert_called_once_with(
            namespace="kube-system", all_namespaces=False, label_selector=None
        )

    def test_get_job(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """get should retrieve a job."""
        result = cli_runner.invoke(app, ["jobs", "get", "test-job"])

        assert result.exit_code == 0
        mock_job_manager.get_job.assert_called_once_with("test-job", namespace=None)

    def test_create_job(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """create should create a job."""
        result = cli_runner.invoke(
            app,
            [
                "jobs",
                "create",
                "test-job",
                "--image",
                "busybox",
                "--command",
                "echo",
                "--command",
                "hello",
            ],
        )

        assert result.exit_code == 0
        mock_job_manager.create_job.assert_called_once()
        call_args = mock_job_manager.create_job.call_args
        assert call_args.args[0] == "test-job"
        assert call_args.kwargs["image"] == "busybox"
        assert call_args.kwargs["command"] == ["echo", "hello"]

    def test_delete_job_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["jobs", "delete", "test-job", "--force"])

        assert result.exit_code == 0
        mock_job_manager.delete_job.assert_called_once()
        call_args = mock_job_manager.delete_job.call_args
        assert call_args.args[0] == "test-job"
        assert call_args.kwargs["propagation_policy"] == "Background"
        assert "deleted" in result.stdout.lower()

    def test_delete_job_with_propagation_policy(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """delete should accept propagation-policy parameter."""
        result = cli_runner.invoke(
            app,
            [
                "jobs",
                "delete",
                "test-job",
                "--propagation-policy",
                "Foreground",
                "--force",
            ],
        )

        assert result.exit_code == 0
        mock_job_manager.delete_job.assert_called_once()
        call_args = mock_job_manager.delete_job.call_args
        assert call_args.kwargs["propagation_policy"] == "Foreground"

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_job_manager.get_job.side_effect = KubernetesNotFoundError(
            resource_type="Job", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["jobs", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
