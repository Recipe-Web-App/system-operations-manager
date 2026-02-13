"""Unit tests for Workflow artifacts commands."""

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
class TestArtifactCommands:
    """Tests for Workflow artifacts commands."""

    @pytest.fixture
    def app(self, get_workflows_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workflow commands."""
        app = typer.Typer()
        register_workflow_commands(app, get_workflows_manager)
        return app

    def test_list_artifacts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """artifacts should list workflow artifacts."""
        result = cli_runner.invoke(app, ["workflows", "artifacts", "my-workflow"])

        assert result.exit_code == 0
        mock_workflows_manager.list_workflow_artifacts.assert_called_once_with(
            "my-workflow", namespace=None
        )

    def test_list_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """artifacts with --namespace should pass namespace."""
        result = cli_runner.invoke(
            app, ["workflows", "artifacts", "my-workflow", "-n", "production"]
        )

        assert result.exit_code == 0
        mock_workflows_manager.list_workflow_artifacts.assert_called_once_with(
            "my-workflow", namespace="production"
        )

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_workflows_manager.list_workflow_artifacts.side_effect = KubernetesNotFoundError(
            resource_type="Workflow", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["workflows", "artifacts", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
