"""Tests for Argo Rollouts command error paths and helper functions.

Covers:
- _parse_labels valid and invalid input
- _parse_canary_steps valid, invalid JSON, and non-list JSON
- KubernetesError handling in every command
- delete abort path (confirm_delete returns False)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import click
import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.rollouts import (
    _parse_canary_steps,
    _parse_labels,
    register_rollout_commands,
)

# =============================================================================
# Helper function tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for the _parse_labels helper function in rollouts."""

    def test_returns_none_for_none_input(self) -> None:
        """_parse_labels should return None when given None."""
        result = _parse_labels(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """_parse_labels should return None when given an empty list."""
        result = _parse_labels([])
        assert result is None

    def test_parses_single_label(self) -> None:
        """_parse_labels should parse a single key=value label."""
        result = _parse_labels(["app=myapp"])
        assert result == {"app": "myapp"}

    def test_parses_multiple_labels(self) -> None:
        """_parse_labels should parse multiple key=value labels."""
        result = _parse_labels(["app=myapp", "version=v1"])
        assert result == {"app": "myapp", "version": "v1"}

    def test_invalid_label_raises_exit(self) -> None:
        """_parse_labels should raise click.exceptions.Exit for labels without '='."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_labels(["noequalssign"])
        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseCanarySteps:
    """Tests for the _parse_canary_steps helper function."""

    def test_returns_none_for_none_input(self) -> None:
        """_parse_canary_steps should return None when given None."""
        result = _parse_canary_steps(None)
        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """_parse_canary_steps should return None when given an empty string."""
        result = _parse_canary_steps("")
        assert result is None

    def test_parses_valid_steps(self) -> None:
        """_parse_canary_steps should parse a valid JSON array of steps."""
        result = _parse_canary_steps('[{"setWeight": 20}, {"pause": {}}]')
        assert result == [{"setWeight": 20}, {"pause": {}}]

    def test_invalid_json_raises_exit(self) -> None:
        """_parse_canary_steps should raise click.exceptions.Exit for invalid JSON."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_canary_steps("not-valid-json")
        assert exc_info.value.exit_code == 1

    def test_non_list_json_raises_exit(self) -> None:
        """_parse_canary_steps should raise click.exceptions.Exit when JSON is not a list."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_canary_steps('{"setWeight": 20}')
        assert exc_info.value.exit_code == 1


# =============================================================================
# KubernetesError handling for Rollout commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRolloutCommandErrors:
    """Tests for KubernetesError handling in Rollout commands."""

    @pytest.fixture
    def app(self, get_rollouts_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with rollout commands."""
        app = typer.Typer()
        register_rollout_commands(app, get_rollouts_manager)
        return app

    def test_list_rollouts_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list rollouts should handle KubernetesError."""
        mock_rollouts_manager.list_rollouts.side_effect = KubernetesError("list failed")
        result = cli_runner.invoke(app, ["rollouts", "list"])
        assert result.exit_code == 1

    def test_create_rollout_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """create rollout should handle KubernetesError."""
        mock_rollouts_manager.create_rollout.side_effect = KubernetesError("create failed")
        result = cli_runner.invoke(
            app,
            ["rollouts", "create", "my-rollout", "--image", "nginx:1.21"],
        )
        assert result.exit_code == 1

    def test_delete_rollout_abort_when_not_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """delete rollout should abort when user does not confirm."""
        cli_runner.invoke(app, ["rollouts", "delete", "my-rollout"], input="n\n")
        mock_rollouts_manager.delete_rollout.assert_not_called()

    def test_delete_rollout_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """delete rollout should handle KubernetesError."""
        mock_rollouts_manager.delete_rollout.side_effect = KubernetesError("delete failed")
        result = cli_runner.invoke(app, ["rollouts", "delete", "my-rollout", "--force"])
        assert result.exit_code == 1

    def test_rollout_status_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """rollout status should handle KubernetesError."""
        mock_rollouts_manager.get_rollout_status.side_effect = KubernetesError("status failed")
        result = cli_runner.invoke(app, ["rollouts", "status", "my-rollout"])
        assert result.exit_code == 1

    def test_retry_rollout_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """retry rollout should handle KubernetesError."""
        mock_rollouts_manager.retry_rollout.side_effect = KubernetesNotFoundError(
            resource_type="Rollout", resource_name="nonexistent"
        )
        result = cli_runner.invoke(app, ["rollouts", "retry", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


# =============================================================================
# KubernetesError handling for AnalysisTemplate commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestAnalysisTemplateCommandErrors:
    """Tests for KubernetesError handling in AnalysisTemplate commands."""

    @pytest.fixture
    def app(self, get_rollouts_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with rollout commands."""
        app = typer.Typer()
        register_rollout_commands(app, get_rollouts_manager)
        return app

    def test_list_analysis_templates_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list analysis templates should handle KubernetesError."""
        mock_rollouts_manager.list_analysis_templates.side_effect = KubernetesError("list failed")
        result = cli_runner.invoke(app, ["analysis-templates", "list"])
        assert result.exit_code == 1

    def test_get_analysis_template_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """get analysis template should handle KubernetesError."""
        mock_rollouts_manager.get_analysis_template.side_effect = KubernetesNotFoundError(
            resource_type="AnalysisTemplate", resource_name="missing"
        )
        result = cli_runner.invoke(app, ["analysis-templates", "get", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


# =============================================================================
# KubernetesError handling for AnalysisRun commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestAnalysisRunCommandErrors:
    """Tests for KubernetesError handling in AnalysisRun commands."""

    @pytest.fixture
    def app(self, get_rollouts_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with rollout commands."""
        app = typer.Typer()
        register_rollout_commands(app, get_rollouts_manager)
        return app

    def test_list_analysis_runs_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list analysis runs should handle KubernetesError."""
        mock_rollouts_manager.list_analysis_runs.side_effect = KubernetesError("list failed")
        result = cli_runner.invoke(app, ["analysis-runs", "list"])
        assert result.exit_code == 1

    def test_get_analysis_run_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """get analysis run should handle KubernetesError."""
        mock_rollouts_manager.get_analysis_run.side_effect = KubernetesNotFoundError(
            resource_type="AnalysisRun", resource_name="missing"
        )
        result = cli_runner.invoke(app, ["analysis-runs", "get", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


# =============================================================================
# Label and canary steps parsing via CLI (exercises helper success paths)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRolloutLabelAndStepsParsing:
    """Tests for label and canary-steps parsing through CLI commands."""

    @pytest.fixture
    def app(self, get_rollouts_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with rollout commands."""
        app = typer.Typer()
        register_rollout_commands(app, get_rollouts_manager)
        return app

    def test_create_rollout_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """create rollout with --label should pass parsed labels."""
        result = cli_runner.invoke(
            app,
            [
                "rollouts",
                "create",
                "my-rollout",
                "--image",
                "nginx:1.21",
                "--label",
                "app=myapp",
                "--label",
                "env=production",
            ],
        )
        assert result.exit_code == 0
        call_kwargs: Any = mock_rollouts_manager.create_rollout.call_args
        assert call_kwargs.kwargs["labels"] == {"app": "myapp", "env": "production"}

    def test_create_rollout_with_canary_steps(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """create rollout with --canary-steps should pass parsed steps."""
        result = cli_runner.invoke(
            app,
            [
                "rollouts",
                "create",
                "my-rollout",
                "--image",
                "nginx:1.21",
                "--canary-steps",
                '[{"setWeight": 20}, {"pause": {}}]',
            ],
        )
        assert result.exit_code == 0
        call_kwargs: Any = mock_rollouts_manager.create_rollout.call_args
        assert call_kwargs.kwargs["canary_steps"] == [
            {"setWeight": 20},
            {"pause": {}},
        ]

    def test_create_rollout_invalid_canary_steps_exits(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """create rollout with invalid canary steps JSON should exit."""
        result = cli_runner.invoke(
            app,
            [
                "rollouts",
                "create",
                "my-rollout",
                "--image",
                "nginx:1.21",
                "--canary-steps",
                "not-valid-json",
            ],
        )
        assert result.exit_code != 0

    def test_create_rollout_non_list_canary_steps_exits(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """create rollout with non-list canary steps JSON should exit."""
        result = cli_runner.invoke(
            app,
            [
                "rollouts",
                "create",
                "my-rollout",
                "--image",
                "nginx:1.21",
                "--canary-steps",
                '{"setWeight": 20}',
            ],
        )
        assert result.exit_code != 0
