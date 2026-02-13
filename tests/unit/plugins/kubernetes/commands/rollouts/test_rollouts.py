"""Unit tests for Rollout commands."""

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
class TestRolloutCommands:
    """Tests for Rollout commands."""

    @pytest.fixture
    def app(self, get_rollouts_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with rollout commands."""
        app = typer.Typer()
        register_rollout_commands(app, get_rollouts_manager)
        return app

    def test_list(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list should list Rollouts."""
        result = cli_runner.invoke(app, ["rollouts", "list"])

        assert result.exit_code == 0
        mock_rollouts_manager.list_rollouts.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["rollouts", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_rollouts_manager.list_rollouts.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_list_with_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """list with --selector should pass label selector."""
        result = cli_runner.invoke(app, ["rollouts", "list", "-l", "app=myapp"])

        assert result.exit_code == 0
        mock_rollouts_manager.list_rollouts.assert_called_once_with(
            namespace=None,
            label_selector="app=myapp",
        )

    def test_get(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """get should retrieve a Rollout."""
        result = cli_runner.invoke(app, ["rollouts", "get", "my-rollout"])

        assert result.exit_code == 0
        mock_rollouts_manager.get_rollout.assert_called_once_with("my-rollout", namespace=None)

    def test_get_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """get with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["rollouts", "get", "my-rollout", "-n", "production"])

        assert result.exit_code == 0
        mock_rollouts_manager.get_rollout.assert_called_once_with(
            "my-rollout", namespace="production"
        )

    def test_create(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """create should create a Rollout."""
        result = cli_runner.invoke(
            app,
            ["rollouts", "create", "my-rollout", "--image", "nginx:1.21"],
        )

        assert result.exit_code == 0
        mock_rollouts_manager.create_rollout.assert_called_once()
        call_kwargs = mock_rollouts_manager.create_rollout.call_args
        assert call_kwargs.args[0] == "my-rollout"
        assert call_kwargs.kwargs["image"] == "nginx:1.21"
        assert call_kwargs.kwargs["strategy"] == "canary"
        assert call_kwargs.kwargs["replicas"] == 1

    def test_create_bluegreen(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """create with blueGreen strategy should pass strategy."""
        result = cli_runner.invoke(
            app,
            [
                "rollouts",
                "create",
                "my-rollout",
                "--image",
                "nginx:1.21",
                "--strategy",
                "blueGreen",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_rollouts_manager.create_rollout.call_args
        assert call_kwargs.kwargs["strategy"] == "blueGreen"

    def test_delete_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["rollouts", "delete", "my-rollout", "--force"])

        assert result.exit_code == 0
        mock_rollouts_manager.delete_rollout.assert_called_once_with("my-rollout", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_delete_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """delete with --namespace should pass namespace."""
        result = cli_runner.invoke(
            app, ["rollouts", "delete", "my-rollout", "-n", "production", "--force"]
        )

        assert result.exit_code == 0
        mock_rollouts_manager.delete_rollout.assert_called_once_with(
            "my-rollout", namespace="production"
        )

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_rollouts_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_rollouts_manager.get_rollout.side_effect = KubernetesNotFoundError(
            resource_type="Rollout", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["rollouts", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
