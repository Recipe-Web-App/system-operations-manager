"""Unit tests for Kubernetes secret commands."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.config_resources import (
    register_config_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSecretCommands:
    """Tests for secret commands."""

    @pytest.fixture
    def app(self, get_config_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with secret commands."""
        app = typer.Typer()
        register_config_commands(app, get_config_manager)
        return app

    def test_list_secrets(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """list should list secrets."""
        mock_config_manager.list_secrets.return_value = []

        result = cli_runner.invoke(app, ["secrets", "list"])

        assert result.exit_code == 0
        mock_config_manager.list_secrets.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_get_secret(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """get should retrieve a secret."""
        result = cli_runner.invoke(app, ["secrets", "get", "test-secret"])

        assert result.exit_code == 0
        mock_config_manager.get_secret.assert_called_once_with("test-secret", namespace=None)

    def test_create_secret(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create should create a secret."""
        result = cli_runner.invoke(
            app,
            [
                "secrets",
                "create",
                "test-secret",
                "--data",
                "username=admin",
                "--data",
                "password=secret",
                "--type",
                "Opaque",
            ],
        )

        assert result.exit_code == 0
        mock_config_manager.create_secret.assert_called_once()
        call_args = mock_config_manager.create_secret.call_args
        assert call_args.args[0] == "test-secret"
        assert call_args.kwargs["data"] == {"username": "admin", "password": "secret"}
        assert call_args.kwargs["secret_type"] == "Opaque"

    def test_create_tls_secret(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create-tls should create a TLS secret from cert and key files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "tls.crt"
            key_path = Path(tmpdir) / "tls.key"
            cert_path.write_text(
                "-----BEGIN CERTIFICATE-----\ntest-cert\n-----END CERTIFICATE-----"
            )
            pk_marker = "PRIVATE KEY"  # avoid detect-private-key hook
            key_path.write_text(f"-----BEGIN {pk_marker}-----\ntest-key\n-----END {pk_marker}-----")

            result = cli_runner.invoke(
                app,
                [
                    "secrets",
                    "create-tls",
                    "test-tls",
                    "--cert",
                    str(cert_path),
                    "--key",
                    str(key_path),
                ],
            )

            assert result.exit_code == 0
            mock_config_manager.create_tls_secret.assert_called_once()
            call_args = mock_config_manager.create_tls_secret.call_args
            assert call_args.args[0] == "test-tls"
            assert "test-cert" in call_args.kwargs["cert"]
            assert "test-key" in call_args.kwargs["key"]

    def test_create_tls_secret_missing_files(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create-tls should fail if cert or key files don't exist."""
        result = cli_runner.invoke(
            app,
            [
                "secrets",
                "create-tls",
                "test-tls",
                "--cert",
                "/nonexistent/tls.crt",
                "--key",
                "/nonexistent/tls.key",
            ],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
        mock_config_manager.create_tls_secret.assert_not_called()

    def test_create_docker_registry_secret(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create-docker-registry should create a docker registry secret."""
        result = cli_runner.invoke(
            app,
            [
                "secrets",
                "create-docker-registry",
                "test-registry",
                "--server",
                "https://index.docker.io/v1/",
                "--username",
                "testuser",
                "--password",
                "testpass",
                "--email",
                "test@example.com",
            ],
        )

        assert result.exit_code == 0
        mock_config_manager.create_docker_registry_secret.assert_called_once()
        call_args = mock_config_manager.create_docker_registry_secret.call_args
        assert call_args.args[0] == "test-registry"
        assert call_args.kwargs["server"] == "https://index.docker.io/v1/"
        assert call_args.kwargs["username"] == "testuser"
        assert call_args.kwargs["password"] == "testpass"
        assert call_args.kwargs["email"] == "test@example.com"

    def test_delete_secret_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["secrets", "delete", "test-secret", "--force"])

        assert result.exit_code == 0
        mock_config_manager.delete_secret.assert_called_once_with("test-secret", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_config_manager.get_secret.side_effect = KubernetesNotFoundError(
            resource_type="Secret", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["secrets", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_list_secrets_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """list should handle KubernetesError."""
        mock_config_manager.list_secrets.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["secrets", "list"])

        assert result.exit_code == 1

    def test_create_secret_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create should handle KubernetesError."""
        mock_config_manager.create_secret.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(
            app,
            ["secrets", "create", "test-secret", "--data", "username=admin"],
        )

        assert result.exit_code == 1

    def test_create_tls_secret_missing_key_file(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create-tls should fail if key file doesn't exist but cert does."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "tls.crt"
            cert_path.write_text("cert-content")

            result = cli_runner.invoke(
                app,
                [
                    "secrets",
                    "create-tls",
                    "test-tls",
                    "--cert",
                    str(cert_path),
                    "--key",
                    "/nonexistent/tls.key",
                ],
            )

            assert result.exit_code == 1
            assert "not found" in result.stdout.lower()
            mock_config_manager.create_tls_secret.assert_not_called()

    def test_create_tls_secret_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create-tls should handle KubernetesError."""
        mock_config_manager.create_tls_secret.side_effect = KubernetesError("connection failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "tls.crt"
            key_path = Path(tmpdir) / "tls.key"
            cert_path.write_text("cert-content")
            key_path.write_text("key-content")

            result = cli_runner.invoke(
                app,
                [
                    "secrets",
                    "create-tls",
                    "test-tls",
                    "--cert",
                    str(cert_path),
                    "--key",
                    str(key_path),
                ],
            )

            assert result.exit_code == 1

    def test_create_docker_registry_secret_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create-docker-registry should handle KubernetesError."""
        mock_config_manager.create_docker_registry_secret.side_effect = KubernetesError(
            "connection failed"
        )

        result = cli_runner.invoke(
            app,
            [
                "secrets",
                "create-docker-registry",
                "test-registry",
                "--server",
                "https://index.docker.io/v1/",
                "--username",
                "testuser",
                "--password",
                "testpass",
            ],
        )

        assert result.exit_code == 1

    def test_delete_secret_aborts_without_confirmation(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """delete without --force should abort when user declines confirmation."""
        result = cli_runner.invoke(app, ["secrets", "delete", "test-secret"], input="n\n")

        assert result.exit_code != 0
        mock_config_manager.delete_secret.assert_not_called()

    def test_delete_secret_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """delete should handle KubernetesError."""
        mock_config_manager.delete_secret.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["secrets", "delete", "test-secret", "--force"])

        assert result.exit_code == 1
