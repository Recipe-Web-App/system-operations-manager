"""Unit tests for SecretStore commands."""

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
from system_operations_manager.plugins.kubernetes.commands.externalsecrets import (
    _parse_data_refs,
    _parse_labels,
    _parse_provider_config,
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

    def test_list_secret_stores_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list should handle KubernetesError."""
        mock_external_secrets_manager.list_secret_stores.side_effect = KubernetesError(
            "connection failed"
        )

        result = cli_runner.invoke(app, ["secret-stores", "list"])

        assert result.exit_code == 1

    def test_create_secret_store_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """create should handle KubernetesError."""
        mock_external_secrets_manager.create_secret_store.side_effect = KubernetesError(
            "connection failed"
        )

        config = '{"vault":{"server":"https://vault.example.com"}}'
        result = cli_runner.invoke(
            app,
            ["secret-stores", "create", "vault-store", "--provider-config", config],
        )

        assert result.exit_code == 1

    def test_delete_secret_store_aborts_without_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """delete without --force should abort when user declines."""
        result = cli_runner.invoke(app, ["secret-stores", "delete", "vault-store"], input="n\n")

        assert result.exit_code != 0
        mock_external_secrets_manager.delete_secret_store.assert_not_called()

    def test_delete_secret_store_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """delete should handle KubernetesError."""
        mock_external_secrets_manager.delete_secret_store.side_effect = KubernetesError(
            "connection failed"
        )

        result = cli_runner.invoke(app, ["secret-stores", "delete", "vault-store", "--force"])

        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabelsESHelper:
    """Tests for _parse_labels helper in externalsecrets module."""

    def test_parse_labels_none_returns_none(self) -> None:
        """_parse_labels with None should return None."""
        result = _parse_labels(None)
        assert result is None

    def test_parse_labels_empty_list_returns_none(self) -> None:
        """_parse_labels with empty list should return None."""
        result = _parse_labels([])
        assert result is None

    def test_parse_labels_valid(self) -> None:
        """_parse_labels should parse valid key=value entries."""
        result = _parse_labels(["provider=vault", "env=prod"])
        assert result == {"provider": "vault", "env": "prod"}

    def test_parse_labels_invalid_format_raises_exit(self) -> None:
        """_parse_labels with invalid format should raise click.Exit."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_labels(["invalidlabel"])
        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseProviderConfigHelper:
    """Tests for _parse_provider_config helper function."""

    def test_parse_valid_json(self) -> None:
        """_parse_provider_config should parse valid JSON object."""
        config = '{"vault":{"server":"https://vault.example.com"}}'
        result = _parse_provider_config(config)
        assert result == {"vault": {"server": "https://vault.example.com"}}

    def test_parse_non_dict_json_raises_exit(self) -> None:
        """_parse_provider_config with non-dict JSON should raise click.Exit."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_provider_config("[1,2,3]")
        assert exc_info.value.exit_code == 1

    def test_parse_invalid_json_raises_exit(self) -> None:
        """_parse_provider_config with invalid JSON should raise click.Exit."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_provider_config("not-json{")
        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseDataRefsHelper:
    """Tests for _parse_data_refs helper function."""

    def test_parse_data_refs_none_returns_none(self) -> None:
        """_parse_data_refs with None should return None."""
        result = _parse_data_refs(None)
        assert result is None

    def test_parse_data_refs_empty_returns_none(self) -> None:
        """_parse_data_refs with empty list should return None."""
        result = _parse_data_refs([])
        assert result is None

    def test_parse_data_refs_valid(self) -> None:
        """_parse_data_refs should parse valid JSON entries."""
        refs = ['{"secretKey":"password","remoteRef":{"key":"secret"}}']
        result = _parse_data_refs(refs)
        assert result is not None
        assert len(result) == 1
        assert result[0]["secretKey"] == "password"

    def test_parse_data_refs_invalid_json_raises_exit(self) -> None:
        """_parse_data_refs with invalid JSON should raise click.Exit."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_data_refs(["not-json{"])
        assert exc_info.value.exit_code == 1
