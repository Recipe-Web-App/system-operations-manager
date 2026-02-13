"""Unit tests for CronWorkflow commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.workflows import (
    register_workflow_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCronWorkflowCommands:
    """Tests for CronWorkflow commands."""

    @pytest.fixture
    def app(self, get_workflows_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workflow commands."""
        app = typer.Typer()
        register_workflow_commands(app, get_workflows_manager)
        return app

    def test_list(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list should list CronWorkflows."""
        result = cli_runner.invoke(app, ["workflows", "cron", "list"])

        assert result.exit_code == 0
        mock_workflows_manager.list_cron_workflows.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_get(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """get should retrieve a CronWorkflow."""
        result = cli_runner.invoke(app, ["workflows", "cron", "get", "my-cron"])

        assert result.exit_code == 0
        mock_workflows_manager.get_cron_workflow.assert_called_once_with("my-cron", namespace=None)

    def test_create(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create should create a CronWorkflow."""
        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "cron",
                "create",
                "my-cron",
                "--schedule",
                "0 0 * * *",
                "--template-ref",
                "my-template",
            ],
        )

        assert result.exit_code == 0
        mock_workflows_manager.create_cron_workflow.assert_called_once()
        call_kwargs = mock_workflows_manager.create_cron_workflow.call_args
        assert call_kwargs.args[0] == "my-cron"
        assert call_kwargs.kwargs["schedule"] == "0 0 * * *"
        assert call_kwargs.kwargs["template_ref"] == "my-template"
        assert call_kwargs.kwargs["timezone"] == ""
        assert call_kwargs.kwargs["concurrency_policy"] == "Allow"

    def test_delete_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["workflows", "cron", "delete", "my-cron", "--force"])

        assert result.exit_code == 0
        mock_workflows_manager.delete_cron_workflow.assert_called_once_with(
            "my-cron", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_suspend(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """suspend should suspend a CronWorkflow."""
        result = cli_runner.invoke(app, ["workflows", "cron", "suspend", "my-cron"])

        assert result.exit_code == 0
        mock_workflows_manager.suspend_cron_workflow.assert_called_once_with(
            "my-cron", namespace=None
        )

    def test_resume(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """resume should resume a CronWorkflow."""
        result = cli_runner.invoke(app, ["workflows", "cron", "resume", "my-cron"])

        assert result.exit_code == 0
        mock_workflows_manager.resume_cron_workflow.assert_called_once_with(
            "my-cron", namespace=None
        )

    def test_list_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["workflows", "cron", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_workflows_manager.list_cron_workflows.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_workflows_manager.get_cron_workflow.side_effect = KubernetesNotFoundError(
            resource_type="CronWorkflow", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["workflows", "cron", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
