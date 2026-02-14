"""Tests for cert-manager Certificate commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.certs import register_certs_commands


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCertificateCommands:
    """Tests for Certificate commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_certificates(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list should list Certificates."""
        result = cli_runner.invoke(app, ["certs", "cert", "list"])

        assert result.exit_code == 0
        mock_certmanager_manager.list_certificates.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_certificates_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["certs", "cert", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_certmanager_manager.list_certificates.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_get_certificate(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get should retrieve a Certificate."""
        result = cli_runner.invoke(app, ["certs", "cert", "get", "my-tls"])

        assert result.exit_code == 0
        mock_certmanager_manager.get_certificate.assert_called_once_with("my-tls", namespace=None)

    def test_create_certificate(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create should create a Certificate with required options."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "cert",
                "create",
                "my-tls",
                "--secret-name",
                "my-tls-secret",
                "--issuer-name",
                "letsencrypt-prod",
                "--dns-name",
                "example.com",
                "--dns-name",
                "www.example.com",
            ],
        )

        assert result.exit_code == 0
        mock_certmanager_manager.create_certificate.assert_called_once()
        call_kwargs = mock_certmanager_manager.create_certificate.call_args
        assert call_kwargs.args[0] == "my-tls"
        assert call_kwargs.kwargs["secret_name"] == "my-tls-secret"
        assert call_kwargs.kwargs["issuer_name"] == "letsencrypt-prod"
        assert call_kwargs.kwargs["dns_names"] == ["example.com", "www.example.com"]

    def test_create_certificate_with_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create with optional args should pass them through."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "cert",
                "create",
                "my-tls",
                "--secret-name",
                "my-tls-secret",
                "--issuer-name",
                "ca-issuer",
                "--issuer-kind",
                "ClusterIssuer",
                "--dns-name",
                "example.com",
                "--duration",
                "8760h",
                "--renew-before",
                "720h",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_certmanager_manager.create_certificate.call_args
        assert call_kwargs.kwargs["issuer_kind"] == "ClusterIssuer"
        assert call_kwargs.kwargs["duration"] == "8760h"
        assert call_kwargs.kwargs["renew_before"] == "720h"

    def test_delete_certificate_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["certs", "cert", "delete", "my-tls", "--force"])

        assert result.exit_code == 0
        mock_certmanager_manager.delete_certificate.assert_called_once_with(
            "my-tls", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_certificate_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """status should show certificate status."""
        result = cli_runner.invoke(app, ["certs", "cert", "status", "my-tls"])

        assert result.exit_code == 0
        mock_certmanager_manager.get_certificate_status.assert_called_once_with(
            "my-tls", namespace=None
        )

    def test_renew_certificate(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """renew should trigger certificate renewal."""
        result = cli_runner.invoke(app, ["certs", "cert", "renew", "my-tls"])

        assert result.exit_code == 0
        mock_certmanager_manager.renew_certificate.assert_called_once_with("my-tls", namespace=None)
        assert "renewal triggered" in result.stdout.lower()
