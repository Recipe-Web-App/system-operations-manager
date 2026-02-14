"""Tests for cert-manager Issuer and ClusterIssuer commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.certs import register_certs_commands


@pytest.mark.unit
@pytest.mark.kubernetes
class TestIssuerCommands:
    """Tests for Issuer commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_issuers(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list should list Issuers."""
        result = cli_runner.invoke(app, ["certs", "issuer", "list"])

        assert result.exit_code == 0
        mock_certmanager_manager.list_issuers.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_get_issuer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get should retrieve an Issuer."""
        result = cli_runner.invoke(app, ["certs", "issuer", "get", "letsencrypt-staging"])

        assert result.exit_code == 0
        mock_certmanager_manager.get_issuer.assert_called_once_with(
            "letsencrypt-staging", namespace=None
        )

    def test_create_issuer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create should create an Issuer."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "issuer",
                "create",
                "self-signed",
                "--type",
                "selfSigned",
                "--config",
                "{}",
            ],
        )

        assert result.exit_code == 0
        mock_certmanager_manager.create_issuer.assert_called_once()
        call_kwargs = mock_certmanager_manager.create_issuer.call_args
        assert call_kwargs.args[0] == "self-signed"
        assert call_kwargs.kwargs["issuer_type"] == "selfSigned"

    def test_delete_issuer_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(
            app, ["certs", "issuer", "delete", "letsencrypt-staging", "--force"]
        )

        assert result.exit_code == 0
        mock_certmanager_manager.delete_issuer.assert_called_once_with(
            "letsencrypt-staging", namespace=None
        )

    def test_issuer_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """status should show issuer status."""
        result = cli_runner.invoke(app, ["certs", "issuer", "status", "letsencrypt-staging"])

        assert result.exit_code == 0
        mock_certmanager_manager.get_issuer_status.assert_called_once_with(
            "letsencrypt-staging", namespace=None
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterIssuerCommands:
    """Tests for ClusterIssuer commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_cluster_issuers(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list should list ClusterIssuers."""
        result = cli_runner.invoke(app, ["certs", "clusterissuer", "list"])

        assert result.exit_code == 0
        mock_certmanager_manager.list_cluster_issuers.assert_called_once_with(
            label_selector=None,
        )

    def test_get_cluster_issuer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get should retrieve a ClusterIssuer."""
        result = cli_runner.invoke(app, ["certs", "clusterissuer", "get", "letsencrypt-prod"])

        assert result.exit_code == 0
        mock_certmanager_manager.get_cluster_issuer.assert_called_once_with("letsencrypt-prod")

    def test_create_cluster_issuer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create should create a ClusterIssuer."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "clusterissuer",
                "create",
                "self-signed",
                "--type",
                "selfSigned",
                "--config",
                "{}",
            ],
        )

        assert result.exit_code == 0
        mock_certmanager_manager.create_cluster_issuer.assert_called_once()

    def test_delete_cluster_issuer_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(
            app, ["certs", "clusterissuer", "delete", "letsencrypt-prod", "--force"]
        )

        assert result.exit_code == 0
        mock_certmanager_manager.delete_cluster_issuer.assert_called_once_with("letsencrypt-prod")

    def test_cluster_issuer_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """status should show ClusterIssuer status."""
        result = cli_runner.invoke(app, ["certs", "clusterissuer", "status", "letsencrypt-prod"])

        assert result.exit_code == 0
        mock_certmanager_manager.get_cluster_issuer_status.assert_called_once_with(
            "letsencrypt-prod"
        )
