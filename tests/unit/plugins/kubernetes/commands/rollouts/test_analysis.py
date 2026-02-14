"""Unit tests for AnalysisTemplate and AnalysisRun commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.rollouts import (
    register_rollout_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestAnalysisCommands:
    """Tests for AnalysisTemplate and AnalysisRun commands."""

    @pytest.fixture
    def app(self, get_rollouts_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with rollout commands."""
        app = typer.Typer()
        register_rollout_commands(app, get_rollouts_manager)
        return app

    def test_list_templates(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list should list AnalysisTemplates."""
        result = cli_runner.invoke(app, ["analysis-templates", "list"])

        assert result.exit_code == 0
        mock_rollouts_manager.list_analysis_templates.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_get_template(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """get should retrieve an AnalysisTemplate."""
        result = cli_runner.invoke(app, ["analysis-templates", "get", "success-rate"])

        assert result.exit_code == 0
        mock_rollouts_manager.get_analysis_template.assert_called_once_with(
            "success-rate", namespace=None
        )

    def test_list_runs(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list should list AnalysisRuns."""
        result = cli_runner.invoke(app, ["analysis-runs", "list"])

        assert result.exit_code == 0
        mock_rollouts_manager.list_analysis_runs.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_get_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """get should retrieve an AnalysisRun."""
        result = cli_runner.invoke(app, ["analysis-runs", "get", "my-rollout-abc123"])

        assert result.exit_code == 0
        mock_rollouts_manager.get_analysis_run.assert_called_once_with(
            "my-rollout-abc123", namespace=None
        )

    def test_list_templates_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["analysis-templates", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_rollouts_manager.list_analysis_templates.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_rollouts_manager.get_analysis_template.side_effect = KubernetesNotFoundError(
            resource_type="AnalysisTemplate", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["analysis-templates", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
