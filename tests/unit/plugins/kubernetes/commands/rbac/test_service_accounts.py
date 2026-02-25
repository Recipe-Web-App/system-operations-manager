"""Unit tests for Kubernetes service account commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import click
import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.rbac import (
    _parse_json_list_option,
    _parse_json_option,
    _parse_labels,
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

    def test_list_service_accounts_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """list should handle KubernetesError."""
        mock_rbac_manager.list_service_accounts.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["service-accounts", "list"])

        assert result.exit_code == 1

    def test_create_service_account_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """create should handle KubernetesError."""
        mock_rbac_manager.create_service_account.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["service-accounts", "create", "test-sa"])

        assert result.exit_code == 1

    def test_delete_service_account_aborts_without_confirmation(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete without --force should abort when user declines."""
        result = cli_runner.invoke(app, ["service-accounts", "delete", "test-sa"], input="n\n")

        assert result.exit_code != 0
        mock_rbac_manager.delete_service_account.assert_not_called()

    def test_delete_service_account_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_rbac_manager: MagicMock
    ) -> None:
        """delete should handle KubernetesError."""
        mock_rbac_manager.delete_service_account.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["service-accounts", "delete", "test-sa", "--force"])

        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRBACParseHelpersHelper:
    """Tests for RBAC helper functions."""

    def test_parse_labels_none_returns_none(self) -> None:
        """_parse_labels with None should return None."""
        result = _parse_labels(None)
        assert result is None

    def test_parse_labels_empty_returns_none(self) -> None:
        """_parse_labels with empty list should return None."""
        result = _parse_labels([])
        assert result is None

    def test_parse_labels_valid(self) -> None:
        """_parse_labels should parse valid key=value entries."""
        result = _parse_labels(["env=prod", "team=ops"])
        assert result == {"env": "prod", "team": "ops"}

    def test_parse_labels_invalid_raises_exit(self) -> None:
        """_parse_labels with invalid format should raise click.Exit."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_labels(["badlabel"])
        assert exc_info.value.exit_code == 1

    def test_parse_json_option_valid(self) -> None:
        """_parse_json_option should parse valid JSON dict."""
        result = _parse_json_option('{"kind":"Role","name":"pod-reader"}', "role-ref")
        assert result == {"kind": "Role", "name": "pod-reader"}

    def test_parse_json_option_invalid_raises_exit(self) -> None:
        """_parse_json_option with invalid JSON should raise click.Exit."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_json_option("not-json{", "role-ref")
        assert exc_info.value.exit_code == 1

    def test_parse_json_list_option_none_returns_none(self) -> None:
        """_parse_json_list_option with None should return None."""
        result = _parse_json_list_option(None, "subject")
        assert result is None

    def test_parse_json_list_option_empty_returns_none(self) -> None:
        """_parse_json_list_option with empty list should return None."""
        result = _parse_json_list_option([], "subject")
        assert result is None

    def test_parse_json_list_option_valid(self) -> None:
        """_parse_json_list_option should parse valid JSON entries."""
        result = _parse_json_list_option(
            ['{"kind":"User","name":"jane"}', '{"kind":"Group","name":"ops"}'], "subject"
        )
        assert result is not None
        assert len(result) == 2
        assert result[0]["kind"] == "User"
        assert result[1]["kind"] == "Group"
