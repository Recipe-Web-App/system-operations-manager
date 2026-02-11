"""Unit tests for Kubernetes StatefulSet commands."""

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
class TestStatefulSetCommands:
    """Tests for StatefulSet CLI commands."""

    @pytest.fixture
    def app(self, get_workload_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workload commands."""
        app = typer.Typer()
        register_workload_commands(app, get_workload_manager)
        return app

    def test_list_statefulsets(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_statefulset: MagicMock,
    ) -> None:
        """statefulsets list should display statefulsets."""
        mock_workload_manager.list_stateful_sets.return_value = [sample_statefulset]

        result = cli_runner.invoke(app, ["statefulsets", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_stateful_sets.assert_called_once()

    def test_get_statefulset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_statefulset: MagicMock,
    ) -> None:
        """statefulsets get should display statefulset details."""
        mock_workload_manager.get_stateful_set.return_value = sample_statefulset

        result = cli_runner.invoke(app, ["statefulsets", "get", "test-sts"])

        assert result.exit_code == 0
        mock_workload_manager.get_stateful_set.assert_called_once_with("test-sts", None)

    def test_create_statefulset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_statefulset: MagicMock,
    ) -> None:
        """statefulsets create should create statefulset."""
        mock_workload_manager.create_stateful_set.return_value = sample_statefulset

        result = cli_runner.invoke(
            app,
            [
                "statefulsets",
                "create",
                "my-db",
                "--image",
                "postgres:15",
                "--service-name",
                "my-db-svc",
            ],
        )

        assert result.exit_code == 0
        mock_workload_manager.create_stateful_set.assert_called_once()

    def test_create_statefulset_with_replicas(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_statefulset: MagicMock,
    ) -> None:
        """statefulsets create should support replicas option."""
        mock_workload_manager.create_stateful_set.return_value = sample_statefulset

        result = cli_runner.invoke(
            app,
            [
                "statefulsets",
                "create",
                "my-db",
                "--image",
                "postgres:15",
                "--service-name",
                "my-db-svc",
                "--replicas",
                "3",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_workload_manager.create_stateful_set.call_args[1]
        assert call_kwargs["replicas"] == 3

    def test_update_statefulset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_statefulset: MagicMock,
    ) -> None:
        """statefulsets update should update statefulset."""
        mock_workload_manager.update_stateful_set.return_value = sample_statefulset

        result = cli_runner.invoke(
            app, ["statefulsets", "update", "my-db", "--image", "postgres:16"]
        )

        assert result.exit_code == 0
        mock_workload_manager.update_stateful_set.assert_called_once()

    def test_delete_statefulset_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """statefulsets delete --force should skip confirmation."""
        result = cli_runner.invoke(app, ["statefulsets", "delete", "my-db", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_stateful_set.assert_called_once_with("my-db", None)

    def test_scale_statefulset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_statefulset: MagicMock,
    ) -> None:
        """statefulsets scale should scale statefulset."""
        mock_workload_manager.scale_stateful_set.return_value = sample_statefulset

        result = cli_runner.invoke(app, ["statefulsets", "scale", "my-db", "--replicas", "5"])

        assert result.exit_code == 0
        mock_workload_manager.scale_stateful_set.assert_called_once()

    def test_restart_statefulset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_statefulset: MagicMock,
    ) -> None:
        """statefulsets restart should restart statefulset."""
        mock_workload_manager.restart_stateful_set.return_value = sample_statefulset

        result = cli_runner.invoke(app, ["statefulsets", "restart", "my-db"])

        assert result.exit_code == 0
        mock_workload_manager.restart_stateful_set.assert_called_once_with("my-db", None)
