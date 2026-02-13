"""Unit tests for Rollout promote/abort/retry commands."""

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
class TestPromoteCommands:
    """Tests for Rollout promote/abort/retry commands."""

    @pytest.fixture
    def app(self, get_rollouts_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with rollout commands."""
        app = typer.Typer()
        register_rollout_commands(app, get_rollouts_manager)
        return app

    def test_promote(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """promote should promote a Rollout."""
        result = cli_runner.invoke(app, ["rollouts", "promote", "my-rollout"])

        assert result.exit_code == 0
        mock_rollouts_manager.promote_rollout.assert_called_once_with(
            "my-rollout", namespace=None, full=False
        )

    def test_promote_full(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """promote with --full should fully promote."""
        result = cli_runner.invoke(app, ["rollouts", "promote", "my-rollout", "--full"])

        assert result.exit_code == 0
        mock_rollouts_manager.promote_rollout.assert_called_once_with(
            "my-rollout", namespace=None, full=True
        )

    def test_abort(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """abort should abort a Rollout."""
        result = cli_runner.invoke(app, ["rollouts", "abort", "my-rollout"])

        assert result.exit_code == 0
        mock_rollouts_manager.abort_rollout.assert_called_once_with("my-rollout", namespace=None)

    def test_retry(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """retry should retry a Rollout."""
        result = cli_runner.invoke(app, ["rollouts", "retry", "my-rollout"])

        assert result.exit_code == 0
        mock_rollouts_manager.retry_rollout.assert_called_once_with("my-rollout", namespace=None)

    def test_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """status should get Rollout status."""
        result = cli_runner.invoke(app, ["rollouts", "status", "my-rollout"])

        assert result.exit_code == 0
        mock_rollouts_manager.get_rollout_status.assert_called_once_with(
            "my-rollout", namespace=None
        )

    def test_status_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """status with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["rollouts", "status", "my-rollout", "-n", "production"])

        assert result.exit_code == 0
        mock_rollouts_manager.get_rollout_status.assert_called_once_with(
            "my-rollout", namespace="production"
        )

    def test_promote_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """promote should handle KubernetesError appropriately."""
        mock_rollouts_manager.promote_rollout.side_effect = KubernetesNotFoundError(
            resource_type="Rollout", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["rollouts", "promote", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_abort_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """abort should handle KubernetesError appropriately."""
        mock_rollouts_manager.abort_rollout.side_effect = KubernetesNotFoundError(
            resource_type="Rollout", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["rollouts", "abort", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
