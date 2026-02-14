"""Unit tests for WorkflowTemplate commands."""

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
class TestTemplateCommands:
    """Tests for WorkflowTemplate commands."""

    @pytest.fixture
    def app(self, get_workflows_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workflow commands."""
        app = typer.Typer()
        register_workflow_commands(app, get_workflows_manager)
        return app

    def test_list_templates(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list should list WorkflowTemplates."""
        result = cli_runner.invoke(app, ["workflows", "templates", "list"])

        assert result.exit_code == 0
        mock_workflows_manager.list_workflow_templates.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_get_template(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """get should retrieve a WorkflowTemplate."""
        result = cli_runner.invoke(app, ["workflows", "templates", "get", "my-template"])

        assert result.exit_code == 0
        mock_workflows_manager.get_workflow_template.assert_called_once_with(
            "my-template", namespace=None
        )

    def test_delete_template_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(
            app, ["workflows", "templates", "delete", "my-template", "--force"]
        )

        assert result.exit_code == 0
        mock_workflows_manager.delete_workflow_template.assert_called_once_with(
            "my-template", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_list_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["workflows", "templates", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_workflows_manager.list_workflow_templates.assert_called_once_with(
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
        mock_workflows_manager.get_workflow_template.side_effect = KubernetesNotFoundError(
            resource_type="WorkflowTemplate", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["workflows", "templates", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
