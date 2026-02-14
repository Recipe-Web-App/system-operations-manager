"""Unit tests for Kubernetes persistent volume claim commands."""

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
class TestPersistentVolumeClaimCommands:
    """Tests for persistent volume claim commands."""

    @pytest.fixture
    def app(self, get_storage_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with PVC commands."""
        app = typer.Typer()
        register_storage_commands(app, get_storage_manager)
        return app

    def test_list_pvcs(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """list should list persistent volume claims."""
        mock_storage_manager.list_persistent_volume_claims.return_value = []

        result = cli_runner.invoke(app, ["pvcs", "list"])

        assert result.exit_code == 0
        mock_storage_manager.list_persistent_volume_claims.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_get_pvc(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """get should retrieve a persistent volume claim."""
        result = cli_runner.invoke(app, ["pvcs", "get", "test-pvc"])

        assert result.exit_code == 0
        mock_storage_manager.get_persistent_volume_claim.assert_called_once_with(
            "test-pvc", namespace=None
        )

    def test_create_pvc(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """create should create a persistent volume claim."""
        result = cli_runner.invoke(
            app,
            [
                "pvcs",
                "create",
                "test-pvc",
                "--storage",
                "10Gi",
                "--access-mode",
                "ReadWriteOnce",
            ],
        )

        assert result.exit_code == 0
        mock_storage_manager.create_persistent_volume_claim.assert_called_once()
        call_args = mock_storage_manager.create_persistent_volume_claim.call_args
        assert call_args.args[0] == "test-pvc"
        assert call_args.kwargs["storage"] == "10Gi"
        assert call_args.kwargs["access_modes"] == ["ReadWriteOnce"]

    def test_delete_pvc_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["pvcs", "delete", "test-pvc", "--force"])

        assert result.exit_code == 0
        mock_storage_manager.delete_persistent_volume_claim.assert_called_once_with(
            "test-pvc", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_storage_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_storage_manager.get_persistent_volume_claim.side_effect = KubernetesNotFoundError(
            resource_type="PersistentVolumeClaim", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["pvcs", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
