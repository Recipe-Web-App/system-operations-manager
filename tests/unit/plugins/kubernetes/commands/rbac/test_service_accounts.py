"""Unit tests for Kubernetes service account commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.rbac import (
    register_rbac_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestServiceAccountCommands:
    """Tests for service account commands."""

    @pytest.fixture
    def app(self, get_rbac_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with service account commands."""
        app = typer.Typer()
        register_rbac_commands(app, get_rbac_manager)
        return app

    def test_list_service_accounts(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """list should list service accounts."""
        mock_rbac_manager.list_service_accounts.return_value = []

        result = cli_runner.invoke(app, ["service-accounts", "list"])

        assert result.exit_code == 0
        mock_rbac_manager.list_service_accounts.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_get_service_account(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """get should retrieve a service account."""
        result = cli_runner.invoke(app, ["service-accounts", "get", "test-sa"])

        assert result.exit_code == 0
        mock_rbac_manager.get_service_account.assert_called_once_with("test-sa", namespace=None)

    def test_create_service_account(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """create should create a service account."""
        result = cli_runner.invoke(app, ["service-accounts", "create", "test-sa"])

        assert result.exit_code == 0
        mock_rbac_manager.create_service_account.assert_called_once()
        call_args = mock_rbac_manager.create_service_account.call_args
        assert call_args.args[0] == "test-sa"

    def test_delete_service_account_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["service-accounts", "delete", "test-sa", "--force"])

        assert result.exit_code == 0
        mock_rbac_manager.delete_service_account.assert_called_once_with("test-sa", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_rbac_manager.get_service_account.side_effect = KubernetesNotFoundError(
            resource_type="ServiceAccount", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["service-accounts", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
