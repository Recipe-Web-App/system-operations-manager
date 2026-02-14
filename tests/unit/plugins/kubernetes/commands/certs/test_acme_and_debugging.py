"""Tests for cert-manager ACME, CertificateRequest, and Challenge commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.certs import register_certs_commands


@pytest.mark.unit
@pytest.mark.kubernetes
class TestACMECommands:
    """Tests for ACME helper commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_create_acme_issuer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create-issuer should create an ACME Issuer."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "acme",
                "create-issuer",
                "letsencrypt-staging",
                "--email",
                "admin@example.com",
            ],
        )

        assert result.exit_code == 0
        mock_certmanager_manager.create_acme_issuer.assert_called_once()
        call_kwargs = mock_certmanager_manager.create_acme_issuer.call_args
        assert call_kwargs.args[0] == "letsencrypt-staging"
        assert call_kwargs.kwargs["email"] == "admin@example.com"

    def test_create_acme_issuer_production(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create-issuer with --production should use LE production server."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "acme",
                "create-issuer",
                "letsencrypt-prod",
                "--email",
                "admin@example.com",
                "--production",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_certmanager_manager.create_acme_issuer.call_args
        assert "letsencrypt.org/directory" in call_kwargs.kwargs["server"]
        assert "staging" not in call_kwargs.kwargs["server"]

    def test_create_acme_cluster_issuer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create-clusterissuer should create an ACME ClusterIssuer."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "acme",
                "create-clusterissuer",
                "letsencrypt-prod",
                "--email",
                "admin@example.com",
                "--production",
                "--ingress-class",
                "nginx",
            ],
        )

        assert result.exit_code == 0
        mock_certmanager_manager.create_acme_cluster_issuer.assert_called_once()
        call_kwargs = mock_certmanager_manager.create_acme_cluster_issuer.call_args
        assert call_kwargs.kwargs["ingress_class"] == "nginx"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCertificateRequestCommands:
    """Tests for CertificateRequest commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_certificate_requests(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list should list CertificateRequests."""
        result = cli_runner.invoke(app, ["certs", "request", "list"])

        assert result.exit_code == 0
        mock_certmanager_manager.list_certificate_requests.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_get_certificate_request(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get should retrieve a CertificateRequest."""
        result = cli_runner.invoke(app, ["certs", "request", "get", "my-tls-1"])

        assert result.exit_code == 0
        mock_certmanager_manager.get_certificate_request.assert_called_once_with(
            "my-tls-1", namespace=None
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestChallengeCommands:
    """Tests for Challenge commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_challenges(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list should list Challenges."""
        result = cli_runner.invoke(app, ["certs", "challenge", "list"])

        assert result.exit_code == 0
        mock_certmanager_manager.list_challenges.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_get_challenge(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get should retrieve a Challenge."""
        result = cli_runner.invoke(app, ["certs", "challenge", "get", "my-challenge"])

        assert result.exit_code == 0
        mock_certmanager_manager.get_challenge.assert_called_once_with(
            "my-challenge", namespace=None
        )

    def test_troubleshoot_challenge(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """troubleshoot should show comprehensive challenge info."""
        result = cli_runner.invoke(app, ["certs", "challenge", "troubleshoot", "my-challenge"])

        assert result.exit_code == 0
        mock_certmanager_manager.troubleshoot_challenge.assert_called_once_with(
            "my-challenge", namespace=None
        )
