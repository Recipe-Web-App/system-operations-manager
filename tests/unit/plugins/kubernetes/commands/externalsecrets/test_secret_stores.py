"""Unit tests for SecretStore commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.externalsecrets import (
    register_external_secrets_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSecretStoreCommands:
    """Tests for SecretStore commands."""

    @pytest.fixture
    def app(self, get_external_secrets_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with external secrets commands."""
        app = typer.Typer()
        register_external_secrets_commands(app, get_external_secrets_manager)
        return app

    def test_list_secret_stores(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list should list SecretStores."""
        result = cli_runner.invoke(app, ["secret-stores", "list"])

        assert result.exit_code == 0
        mock_external_secrets_manager.list_secret_stores.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_secret_stores_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["secret-stores", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_external_secrets_manager.list_secret_stores.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_list_secret_stores_with_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list with --selector should pass label selector."""
        result = cli_runner.invoke(app, ["secret-stores", "list", "-l", "provider=vault"])

        assert result.exit_code == 0
        mock_external_secrets_manager.list_secret_stores.assert_called_once_with(
            namespace=None,
            label_selector="provider=vault",
        )

    def test_get_secret_store(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """get should retrieve a SecretStore."""
        result = cli_runner.invoke(app, ["secret-stores", "get", "vault-store"])

        assert result.exit_code == 0
        mock_external_secrets_manager.get_secret_store.assert_called_once_with(
            "vault-store", namespace=None
        )

    def test_get_secret_store_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """get with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["secret-stores", "get", "vault-store", "-n", "production"])

        assert result.exit_code == 0
        mock_external_secrets_manager.get_secret_store.assert_called_once_with(
            "vault-store", namespace="production"
        )

    def test_create_secret_store(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """create should create a SecretStore."""
        config = '{"vault":{"server":"https://vault.example.com"}}'
        result = cli_runner.invoke(
            app,
            ["secret-stores", "create", "vault-store", "--provider-config", config],
        )

        assert result.exit_code == 0
        mock_external_secrets_manager.create_secret_store.assert_called_once()
        call_kwargs = mock_external_secrets_manager.create_secret_store.call_args
        assert call_kwargs.args[0] == "vault-store"
        assert call_kwargs.kwargs["provider_config"] == {
            "vault": {"server": "https://vault.example.com"}
        }

    def test_delete_secret_store_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["secret-stores", "delete", "vault-store", "--force"])

        assert result.exit_code == 0
        mock_external_secrets_manager.delete_secret_store.assert_called_once_with(
            "vault-store", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_external_secrets_manager.get_secret_store.side_effect = KubernetesNotFoundError(
            resource_type="SecretStore", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["secret-stores", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
