"""Unit tests for Kubernetes DaemonSet commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.workloads import (
    register_workload_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDaemonSetCommands:
    """Tests for DaemonSet CLI commands."""

    @pytest.fixture
    def app(self, get_workload_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workload commands."""
        app = typer.Typer()
        register_workload_commands(app, get_workload_manager)
        return app

    def test_list_daemonsets(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_daemonset: MagicMock,
    ) -> None:
        """daemonsets list should display daemonsets."""
        mock_workload_manager.list_daemon_sets.return_value = [sample_daemonset]

        result = cli_runner.invoke(app, ["daemonsets", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_daemon_sets.assert_called_once()

    def test_get_daemonset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_daemonset: MagicMock,
    ) -> None:
        """daemonsets get should display daemonset details."""
        mock_workload_manager.get_daemon_set.return_value = sample_daemonset

        result = cli_runner.invoke(app, ["daemonsets", "get", "test-ds"])

        assert result.exit_code == 0
        mock_workload_manager.get_daemon_set.assert_called_once_with("test-ds", None)

    def test_create_daemonset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_daemonset: MagicMock,
    ) -> None:
        """daemonsets create should create daemonset."""
        mock_workload_manager.create_daemon_set.return_value = sample_daemonset

        result = cli_runner.invoke(
            app, ["daemonsets", "create", "my-logger", "--image", "fluentd:latest"]
        )

        assert result.exit_code == 0
        mock_workload_manager.create_daemon_set.assert_called_once()

    def test_create_daemonset_with_port(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_daemonset: MagicMock,
    ) -> None:
        """daemonsets create should support port option."""
        mock_workload_manager.create_daemon_set.return_value = sample_daemonset

        result = cli_runner.invoke(
            app,
            ["daemonsets", "create", "my-logger", "--image", "fluentd:latest", "--port", "24224"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_workload_manager.create_daemon_set.call_args[1]
        assert call_kwargs["port"] == 24224

    def test_update_daemonset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_daemonset: MagicMock,
    ) -> None:
        """daemonsets update should update daemonset."""
        mock_workload_manager.update_daemon_set.return_value = sample_daemonset

        result = cli_runner.invoke(
            app, ["daemonsets", "update", "my-logger", "--image", "fluentd:v2"]
        )

        assert result.exit_code == 0
        mock_workload_manager.update_daemon_set.assert_called_once()

    def test_delete_daemonset_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """daemonsets delete --force should skip confirmation."""
        result = cli_runner.invoke(app, ["daemonsets", "delete", "my-logger", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_daemon_set.assert_called_once_with("my-logger", None)

    def test_restart_daemonset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_daemonset: MagicMock,
    ) -> None:
        """daemonsets restart should restart daemonset."""
        mock_workload_manager.restart_daemon_set.return_value = sample_daemonset

        result = cli_runner.invoke(app, ["daemonsets", "restart", "my-logger"])

        assert result.exit_code == 0
        mock_workload_manager.restart_daemon_set.assert_called_once_with("my-logger", None)
