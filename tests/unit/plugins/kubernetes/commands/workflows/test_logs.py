"""Unit tests for Workflow logs commands."""

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
class TestLogCommands:
    """Tests for Workflow logs commands."""

    @pytest.fixture
    def app(self, get_workflows_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workflow commands."""
        app = typer.Typer()
        register_workflow_commands(app, get_workflows_manager)
        return app

    def test_logs_static(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """logs should retrieve static logs."""
        mock_workflows_manager.get_workflow_logs.return_value = "workflow logs here"
        result = cli_runner.invoke(app, ["workflows", "logs", "my-workflow"])

        assert result.exit_code == 0
        mock_workflows_manager.get_workflow_logs.assert_called_once_with(
            "my-workflow", namespace=None, container="main", follow=False
        )
        assert "workflow logs here" in result.stdout

    def test_logs_with_container(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """logs with --container should pass container name."""
        result = cli_runner.invoke(app, ["workflows", "logs", "my-workflow", "--container", "wait"])

        assert result.exit_code == 0
        call_kwargs = mock_workflows_manager.get_workflow_logs.call_args
        assert call_kwargs.kwargs["container"] == "wait"

    def test_logs_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """logs with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["workflows", "logs", "my-workflow", "-n", "production"])

        assert result.exit_code == 0
        call_kwargs = mock_workflows_manager.get_workflow_logs.call_args
        assert call_kwargs.args[0] == "my-workflow"
        assert call_kwargs.kwargs["namespace"] == "production"

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_workflows_manager.get_workflow_logs.side_effect = KubernetesNotFoundError(
            resource_type="Workflow", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["workflows", "logs", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
