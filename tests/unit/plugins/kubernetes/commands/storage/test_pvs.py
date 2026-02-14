"""Unit tests for Kubernetes persistent volume commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.storage import (
    register_storage_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPersistentVolumeCommands:
    """Tests for persistent volume commands."""

    @pytest.fixture
    def app(self, get_storage_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with PV commands."""
        app = typer.Typer()
        register_storage_commands(app, get_storage_manager)
        return app

    def test_list_pvs(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """list should list persistent volumes."""
        mock_storage_manager.list_persistent_volumes.return_value = []

        result = cli_runner.invoke(app, ["pvs", "list"])

        assert result.exit_code == 0
        mock_storage_manager.list_persistent_volumes.assert_called_once_with(label_selector=None)

    def test_get_pv(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """get should retrieve a persistent volume."""
        result = cli_runner.invoke(app, ["pvs", "get", "test-pv"])

        assert result.exit_code == 0
        mock_storage_manager.get_persistent_volume.assert_called_once_with("test-pv")

    def test_delete_pv_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["pvs", "delete", "test-pv", "--force"])

        assert result.exit_code == 0
        mock_storage_manager.delete_persistent_volume.assert_called_once_with("test-pv")
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_storage_manager.get_persistent_volume.side_effect = KubernetesNotFoundError(
            resource_type="PersistentVolume", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["pvs", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
