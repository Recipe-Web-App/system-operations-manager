"""Unit tests for Workflow commands."""

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
class TestWorkflowCommands:
    """Tests for Workflow commands."""

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
        """list should list Workflows."""
        result = cli_runner.invoke(app, ["workflows", "list"])

        assert result.exit_code == 0
        mock_workflows_manager.list_workflows.assert_called_once_with(
            namespace=None,
            label_selector=None,
            phase=None,
        )

    def test_list_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["workflows", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_workflows_manager.list_workflows.assert_called_once_with(
            namespace="production",
            label_selector=None,
            phase=None,
        )

    def test_list_with_phase(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list with --phase should filter by phase."""
        result = cli_runner.invoke(app, ["workflows", "list", "--phase", "Running"])

        assert result.exit_code == 0
        mock_workflows_manager.list_workflows.assert_called_once_with(
            namespace=None,
            label_selector=None,
            phase="Running",
        )

    def test_get(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """get should retrieve a Workflow."""
        result = cli_runner.invoke(app, ["workflows", "get", "my-workflow"])

        assert result.exit_code == 0
        mock_workflows_manager.get_workflow.assert_called_once_with("my-workflow", namespace=None)

    def test_get_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """get with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["workflows", "get", "my-workflow", "-n", "production"])

        assert result.exit_code == 0
        mock_workflows_manager.get_workflow.assert_called_once_with(
            "my-workflow", namespace="production"
        )

    def test_create(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create should create a Workflow."""
        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "create",
                "my-workflow",
                "--template-ref",
                "my-template",
            ],
        )

        assert result.exit_code == 0
        mock_workflows_manager.create_workflow.assert_called_once()
        call_kwargs = mock_workflows_manager.create_workflow.call_args
        assert call_kwargs.args[0] == "my-workflow"
        assert call_kwargs.kwargs["template_ref"] == "my-template"
        assert call_kwargs.kwargs["arguments"] is None
        assert call_kwargs.kwargs["labels"] is None

    def test_create_with_arguments(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create with --argument should pass arguments."""
        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "create",
                "my-workflow",
                "--template-ref",
                "my-template",
                "--argument",
                "message=hello",
                "--argument",
                "count=5",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_workflows_manager.create_workflow.call_args
        assert call_kwargs.kwargs["arguments"] == {"message": "hello", "count": "5"}

    def test_delete_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["workflows", "delete", "my-workflow", "--force"])

        assert result.exit_code == 0
        mock_workflows_manager.delete_workflow.assert_called_once_with(
            "my-workflow", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_delete_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete with --namespace should pass namespace."""
        result = cli_runner.invoke(
            app,
            ["workflows", "delete", "my-workflow", "-n", "production", "--force"],
        )

        assert result.exit_code == 0
        mock_workflows_manager.delete_workflow.assert_called_once_with(
            "my-workflow", namespace="production"
        )

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_workflows_manager.get_workflow.side_effect = KubernetesNotFoundError(
            resource_type="Workflow", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["workflows", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
