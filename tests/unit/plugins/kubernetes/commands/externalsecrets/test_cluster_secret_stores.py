"""Unit tests for ClusterSecretStore commands."""

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
class TestClusterSecretStoreCommands:
    """Tests for ClusterSecretStore commands."""

    @pytest.fixture
    def app(self, get_external_secrets_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with external secrets commands."""
        app = typer.Typer()
        register_external_secrets_commands(app, get_external_secrets_manager)
        return app

    def test_list_cluster_secret_stores(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list should list ClusterSecretStores."""
        result = cli_runner.invoke(app, ["cluster-secret-stores", "list"])

        assert result.exit_code == 0
        mock_external_secrets_manager.list_cluster_secret_stores.assert_called_once_with(
            label_selector=None,
        )

    def test_list_with_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """list with --selector should pass label selector."""
        result = cli_runner.invoke(app, ["cluster-secret-stores", "list", "-l", "provider=aws"])

        assert result.exit_code == 0
        mock_external_secrets_manager.list_cluster_secret_stores.assert_called_once_with(
            label_selector="provider=aws",
        )

    def test_get_cluster_secret_store(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """get should retrieve a ClusterSecretStore."""
        result = cli_runner.invoke(app, ["cluster-secret-stores", "get", "aws-store"])

        assert result.exit_code == 0
        mock_external_secrets_manager.get_cluster_secret_store.assert_called_once_with("aws-store")

    def test_create_cluster_secret_store(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """create should create a ClusterSecretStore."""
        config = '{"aws":{"service":"SecretsManager","region":"us-east-1"}}'
        result = cli_runner.invoke(
            app,
            ["cluster-secret-stores", "create", "aws-store", "--provider-config", config],
        )

        assert result.exit_code == 0
        mock_external_secrets_manager.create_cluster_secret_store.assert_called_once()
        call_kwargs = mock_external_secrets_manager.create_cluster_secret_store.call_args
        assert call_kwargs.args[0] == "aws-store"
        assert call_kwargs.kwargs["provider_config"] == {
            "aws": {"service": "SecretsManager", "region": "us-east-1"}
        }

    def test_delete_cluster_secret_store_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["cluster-secret-stores", "delete", "aws-store", "--force"])

        assert result.exit_code == 0
        mock_external_secrets_manager.delete_cluster_secret_store.assert_called_once_with(
            "aws-store"
        )
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_external_secrets_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_external_secrets_manager.get_cluster_secret_store.side_effect = (
            KubernetesNotFoundError(resource_type="ClusterSecretStore", resource_name="nonexistent")
        )

        result = cli_runner.invoke(app, ["cluster-secret-stores", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
