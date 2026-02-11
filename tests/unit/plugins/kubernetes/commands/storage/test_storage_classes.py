"""Unit tests for Kubernetes storage class commands."""

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
class TestStorageClassCommands:
    """Tests for storage class commands."""

    @pytest.fixture
    def app(self, get_storage_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with storage class commands."""
        app = typer.Typer()
        register_storage_commands(app, get_storage_manager)
        return app

    def test_list_storage_classes(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """list should list storage classes."""
        mock_storage_manager.list_storage_classes.return_value = []

        result = cli_runner.invoke(app, ["storage-classes", "list"])

        assert result.exit_code == 0
        mock_storage_manager.list_storage_classes.assert_called_once()

    def test_get_storage_class(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """get should retrieve a storage class."""
        result = cli_runner.invoke(app, ["storage-classes", "get", "standard"])

        assert result.exit_code == 0
        mock_storage_manager.get_storage_class.assert_called_once_with("standard")

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_storage_manager.get_storage_class.side_effect = KubernetesNotFoundError(
            resource_type="StorageClass", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["storage-classes", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
