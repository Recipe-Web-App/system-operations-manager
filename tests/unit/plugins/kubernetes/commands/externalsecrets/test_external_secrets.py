"""Unit tests for ExternalSecret commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.externalsecrets import (
    register_external_secrets_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestExternalSecretCommands:
    """Tests for ExternalSecret commands."""

    @pytest.fixture
    def app(self, get_external_secrets_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with external secrets commands."""
        app = typer.Typer()
        register_external_secrets_commands(app, get_external_secrets_manager)
        return app

    def test_list_external_secrets(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list should list ExternalSecrets."""
        result = cli_runner.invoke(app, ["external-secrets", "list"])

        assert result.exit_code == 0
        mock_external_secrets_manager.list_external_secrets.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["external-secrets", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_external_secrets_manager.list_external_secrets.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_get_external_secret(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """get should retrieve an ExternalSecret."""
        result = cli_runner.invoke(app, ["external-secrets", "get", "my-secret"])

        assert result.exit_code == 0
        mock_external_secrets_manager.get_external_secret.assert_called_once_with(
            "my-secret", namespace=None
        )

    def test_get_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """get with --namespace should pass namespace."""
        result = cli_runner.invoke(
            app, ["external-secrets", "get", "my-secret", "-n", "production"]
        )

        assert result.exit_code == 0
        mock_external_secrets_manager.get_external_secret.assert_called_once_with(
            "my-secret", namespace="production"
        )

    def test_create_external_secret(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """create should create an ExternalSecret."""
        data_json = (
            '{"secretKey":"password","remoteRef":{"key":"secret/myapp","property":"password"}}'
        )
        result = cli_runner.invoke(
            app,
            [
                "external-secrets",
                "create",
                "my-secret",
                "--store",
                "vault-store",
                "--data",
                data_json,
            ],
        )

        assert result.exit_code == 0
        mock_external_secrets_manager.create_external_secret.assert_called_once()
        call_kwargs = mock_external_secrets_manager.create_external_secret.call_args
        assert call_kwargs.args[0] == "my-secret"
        assert call_kwargs.kwargs["store_name"] == "vault-store"
        assert call_kwargs.kwargs["store_kind"] == "SecretStore"
        assert call_kwargs.kwargs["refresh_interval"] == "1h"

    def test_create_with_store_kind(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """create with --store-kind should pass store kind."""
        result = cli_runner.invoke(
            app,
            [
                "external-secrets",
                "create",
                "my-secret",
                "--store",
                "aws-store",
                "--store-kind",
                "ClusterSecretStore",
                "--refresh-interval",
                "30m",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_external_secrets_manager.create_external_secret.call_args
        assert call_kwargs.kwargs["store_kind"] == "ClusterSecretStore"
        assert call_kwargs.kwargs["refresh_interval"] == "30m"

    def test_delete_external_secret_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["external-secrets", "delete", "my-secret", "--force"])

        assert result.exit_code == 0
        mock_external_secrets_manager.delete_external_secret.assert_called_once_with(
            "my-secret", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_delete_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """delete with --namespace should pass namespace."""
        result = cli_runner.invoke(
            app,
            ["external-secrets", "delete", "my-secret", "-n", "production", "--force"],
        )

        assert result.exit_code == 0
        mock_external_secrets_manager.delete_external_secret.assert_called_once_with(
            "my-secret", namespace="production"
        )

    def test_sync_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """sync-status should show sync status."""
        result = cli_runner.invoke(app, ["external-secrets", "sync-status", "my-secret"])

        assert result.exit_code == 0
        mock_external_secrets_manager.get_sync_status.assert_called_once_with(
            "my-secret", namespace=None
        )

    def test_sync_status_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """sync-status with --namespace should pass namespace."""
        result = cli_runner.invoke(
            app,
            ["external-secrets", "sync-status", "my-secret", "-n", "production"],
        )

        assert result.exit_code == 0
        mock_external_secrets_manager.get_sync_status.assert_called_once_with(
            "my-secret", namespace="production"
        )

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_external_secrets_manager.get_external_secret.side_effect = KubernetesNotFoundError(
            resource_type="ExternalSecret", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["external-secrets", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_list_external_secrets_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list should handle KubernetesError."""
        mock_external_secrets_manager.list_external_secrets.side_effect = KubernetesError(
            "connection failed"
        )

        result = cli_runner.invoke(app, ["external-secrets", "list"])

        assert result.exit_code == 1

    def test_create_external_secret_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """create should handle KubernetesError."""
        mock_external_secrets_manager.create_external_secret.side_effect = KubernetesError(
            "connection failed"
        )

        result = cli_runner.invoke(
            app,
            [
                "external-secrets",
                "create",
                "my-secret",
                "--store",
                "vault-store",
            ],
        )

        assert result.exit_code == 1

    def test_delete_external_secret_aborts_without_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """delete without --force should abort when user declines."""
        result = cli_runner.invoke(app, ["external-secrets", "delete", "my-secret"], input="n\n")

        assert result.exit_code != 0
        mock_external_secrets_manager.delete_external_secret.assert_not_called()

    def test_delete_external_secret_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """delete should handle KubernetesError."""
        mock_external_secrets_manager.delete_external_secret.side_effect = KubernetesError(
            "connection failed"
        )

        result = cli_runner.invoke(app, ["external-secrets", "delete", "my-secret", "--force"])

        assert result.exit_code == 1

    def test_sync_status_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """sync-status should handle KubernetesError."""
        mock_external_secrets_manager.get_sync_status.side_effect = KubernetesError(
            "connection failed"
        )

        result = cli_runner.invoke(app, ["external-secrets", "sync-status", "my-secret"])

        assert result.exit_code == 1
