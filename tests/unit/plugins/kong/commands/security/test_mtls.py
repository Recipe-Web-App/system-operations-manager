"""Unit tests for mTLS security commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.security.mtls import (
    REVOCATION_CHECK_MODES,
    register_mtls_commands,
)

from .conftest import _create_mock_entity


class TestMTLSCommands:
    """Tests for mTLS CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
        mock_consumer_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with mTLS commands."""
        app = typer.Typer()
        register_mtls_commands(
            app,
            lambda: mock_plugin_manager,
            lambda: mock_consumer_manager,
        )
        return app


class TestRevocationModes:
    """Tests for revocation check mode constants."""

    @pytest.mark.unit
    def test_supported_revocation_modes(self) -> None:
        """REVOCATION_CHECK_MODES should contain expected modes."""
        assert "SKIP" in REVOCATION_CHECK_MODES
        assert "IGNORE_CA_ERROR" in REVOCATION_CHECK_MODES
        assert "STRICT" in REVOCATION_CHECK_MODES


class TestMTLSEnable(TestMTLSCommands):
    """Tests for mTLS enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["mtls", "enable"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should call plugin manager with service."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "mtls-auth"
        assert call_kwargs[1]["service"] == "my-api"

    @pytest.mark.unit
    def test_enable_with_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should call plugin manager with route."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "enable", "--route", "my-route"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["route"] == "my-route"

    @pytest.mark.unit
    def test_enable_with_ca_certificates(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass ca_certificates to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "mtls",
                "enable",
                "--service",
                "my-api",
                "--ca-certificate",
                "ca-cert-uuid-1",
                "--ca-certificate",
                "ca-cert-uuid-2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        certs = call_kwargs[1]["config"]["ca_certificates"]
        assert "ca-cert-uuid-1" in certs
        assert "ca-cert-uuid-2" in certs

    @pytest.mark.unit
    def test_enable_with_skip_consumer_lookup(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass skip_consumer_lookup flag."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "enable", "--service", "my-api", "--skip-consumer-lookup"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["skip_consumer_lookup"] is True

    @pytest.mark.unit
    def test_enable_with_revocation_check_mode_skip(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass revocation_check_mode SKIP."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "mtls",
                "enable",
                "--service",
                "my-api",
                "--revocation-check-mode",
                "SKIP",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["revocation_check_mode"] == "SKIP"

    @pytest.mark.unit
    def test_enable_with_revocation_check_mode_strict(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass revocation_check_mode STRICT."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "mtls",
                "enable",
                "--service",
                "my-api",
                "--revocation-check-mode",
                "STRICT",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["revocation_check_mode"] == "STRICT"

    @pytest.mark.unit
    def test_enable_invalid_revocation_mode(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should reject invalid revocation check mode."""
        result = cli_runner.invoke(
            app,
            [
                "mtls",
                "enable",
                "--service",
                "my-api",
                "--revocation-check-mode",
                "INVALID",
            ],
        )

        assert result.exit_code == 1
        assert "revocation" in result.stdout.lower() or "invalid" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_authenticated_group_by(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass authenticated_group_by."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "mtls",
                "enable",
                "--service",
                "my-api",
                "--authenticated-group-by",
                "CN",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["authenticated_group_by"] == "CN"

    @pytest.mark.unit
    def test_enable_with_http_timeout(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass http_timeout."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "enable", "--service", "my-api", "--http-timeout", "5000"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["http_timeout"] == 5000

    @pytest.mark.unit
    def test_enable_with_cert_cache_ttl(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass cert_cache_ttl."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "enable", "--service", "my-api", "--cert-cache-ttl", "300"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["cert_cache_ttl"] == 300

    @pytest.mark.unit
    def test_enable_with_allow_partial_chain(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass allow_partial_chain flag."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="mtls-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "enable", "--service", "my-api", "--allow-partial-chain"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["allow_partial_chain"] is True

    @pytest.mark.unit
    def test_enable_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should handle KongAPIError gracefully."""
        mock_plugin_manager.enable.side_effect = KongAPIError(
            "Plugin configuration error",
            status_code=400,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestMTLSAddCert(TestMTLSCommands):
    """Tests for mTLS add-cert command."""

    @pytest.mark.unit
    def test_add_cert_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-cert should create mTLS credential."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "subject_name": "CN=client,O=MyOrg",
                "created_at": 1234567890,
            }
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "add-cert", "my-user", "--subject-name", "CN=client,O=MyOrg"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.add_credential.assert_called_once()
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][0] == "my-user"
        assert call_args[0][1] == "mtls-auth"
        assert call_args[0][2]["subject_name"] == "CN=client,O=MyOrg"

    @pytest.mark.unit
    def test_add_cert_with_ca_certificate(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-cert should pass ca_certificate reference."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "subject_name": "CN=app-client",
                "ca_certificate": {"id": "ca-cert-uuid"},
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "mtls",
                "add-cert",
                "my-user",
                "--subject-name",
                "CN=app-client",
                "--ca-certificate",
                "ca-cert-uuid",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][2]["ca_certificate"] == {"id": "ca-cert-uuid"}

    @pytest.mark.unit
    def test_add_cert_with_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-cert should pass tags."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "subject_name": "CN=client",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "mtls",
                "add-cert",
                "my-user",
                "--subject-name",
                "CN=client",
                "--tag",
                "production",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert "production" in call_args[0][2]["tags"]

    @pytest.mark.unit
    def test_add_cert_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-cert should handle KongAPIError gracefully."""
        mock_consumer_manager.add_credential.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "add-cert", "nonexistent", "--subject-name", "CN=client"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestMTLSListCerts(TestMTLSCommands):
    """Tests for mTLS list-certs command."""

    @pytest.mark.unit
    def test_list_certs_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-certs should list mTLS credentials."""
        mock_consumer_manager.list_credentials.return_value = [
            _create_mock_entity({"id": "cred-1", "subject_name": "CN=client1"}),
            _create_mock_entity({"id": "cred-2", "subject_name": "CN=client2"}),
        ]

        result = cli_runner.invoke(
            app,
            ["mtls", "list-certs", "my-user"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.list_credentials.assert_called_once_with("my-user", "mtls-auth")

    @pytest.mark.unit
    def test_list_certs_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-certs should support JSON output."""
        result = cli_runner.invoke(
            app,
            ["mtls", "list-certs", "my-user", "--output", "json"],
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_list_certs_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-certs should handle KongAPIError gracefully."""
        mock_consumer_manager.list_credentials.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "list-certs", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestMTLSRevokeCert(TestMTLSCommands):
    """Tests for mTLS revoke-cert command."""

    @pytest.mark.unit
    def test_revoke_cert_with_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """revoke-cert should prompt for confirmation."""
        result = cli_runner.invoke(
            app,
            ["mtls", "revoke-cert", "my-user", "cert-123"],
            input="y\n",
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete_credential.assert_called_once_with(
            "my-user", "mtls-auth", "cert-123"
        )

    @pytest.mark.unit
    def test_revoke_cert_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """revoke-cert should not delete when cancelled."""
        result = cli_runner.invoke(
            app,
            ["mtls", "revoke-cert", "my-user", "cert-123"],
            input="n\n",
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete_credential.assert_not_called()

    @pytest.mark.unit
    def test_revoke_cert_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """revoke-cert --force should skip confirmation."""
        result = cli_runner.invoke(
            app,
            ["mtls", "revoke-cert", "my-user", "cert-123", "--force"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete_credential.assert_called_once_with(
            "my-user", "mtls-auth", "cert-123"
        )

    @pytest.mark.unit
    def test_revoke_cert_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """revoke-cert should handle KongAPIError gracefully."""
        mock_consumer_manager.delete_credential.side_effect = KongAPIError(
            "Credential not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["mtls", "revoke-cert", "my-user", "cert-123", "--force"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
