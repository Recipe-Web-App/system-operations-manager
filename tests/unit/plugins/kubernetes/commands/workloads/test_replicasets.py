"""Unit tests for Kubernetes ReplicaSet commands."""

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
class TestReplicaSetCommands:
    """Tests for ReplicaSet CLI commands."""

    @pytest.fixture
    def app(self, get_workload_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workload commands."""
        app = typer.Typer()
        register_workload_commands(app, get_workload_manager)
        return app

    def test_list_replicasets(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_replicaset: MagicMock,
    ) -> None:
        """replicasets list should display replicasets."""
        mock_workload_manager.list_replica_sets.return_value = [sample_replicaset]

        result = cli_runner.invoke(app, ["replicasets", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_replica_sets.assert_called_once()

    def test_list_replicasets_all_namespaces(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """replicasets list -A should list from all namespaces."""
        mock_workload_manager.list_replica_sets.return_value = []

        result = cli_runner.invoke(app, ["replicasets", "list", "--all-namespaces"])

        assert result.exit_code == 0

    def test_get_replicaset(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_replicaset: MagicMock,
    ) -> None:
        """replicasets get should display replicaset details."""
        mock_workload_manager.get_replica_set.return_value = sample_replicaset

        result = cli_runner.invoke(app, ["replicasets", "get", "test-rs"])

        assert result.exit_code == 0
        mock_workload_manager.get_replica_set.assert_called_once_with("test-rs", None)

    def test_delete_replicaset_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """replicasets delete --force should skip confirmation."""
        result = cli_runner.invoke(app, ["replicasets", "delete", "test-rs", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_replica_set.assert_called_once_with("test-rs", None)

    def test_delete_replicaset_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """replicasets delete should cancel when not confirmed."""
        result = cli_runner.invoke(app, ["replicasets", "delete", "test-rs"], input="n\n")

        assert result.exit_code == 0
        mock_workload_manager.delete_replica_set.assert_not_called()
