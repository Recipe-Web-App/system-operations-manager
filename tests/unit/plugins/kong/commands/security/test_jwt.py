"""Unit tests for JWT security commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.security.jwt import (
    JWT_ALGORITHMS,
    register_jwt_commands,
)

from .conftest import _create_mock_entity


class TestJWTCommands:
    """Tests for JWT CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
        mock_consumer_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with JWT commands."""
        app = typer.Typer()
        register_jwt_commands(
            app,
            lambda: mock_plugin_manager,
            lambda: mock_consumer_manager,
        )
        return app


class TestJWTAlgorithms:
    """Tests for JWT algorithm constants."""

    @pytest.mark.unit
    def test_supported_algorithms(self) -> None:
        """JWT_ALGORITHMS should contain expected algorithms."""
        # Symmetric algorithms
        assert "HS256" in JWT_ALGORITHMS
        assert "HS384" in JWT_ALGORITHMS
        assert "HS512" in JWT_ALGORITHMS

        # RSA algorithms
        assert "RS256" in JWT_ALGORITHMS
        assert "RS384" in JWT_ALGORITHMS
        assert "RS512" in JWT_ALGORITHMS

        # ECDSA algorithms
        assert "ES256" in JWT_ALGORITHMS
        assert "ES384" in JWT_ALGORITHMS
        assert "ES512" in JWT_ALGORITHMS


class TestJWTEnable(TestJWTCommands):
    """Tests for JWT enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["jwt", "enable"])

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
            name="jwt",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["jwt", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "jwt"
        assert call_kwargs[1]["service"] == "my-api"

    @pytest.mark.unit
    def test_enable_with_claims_to_verify(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass claims_to_verify to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="jwt",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "jwt",
                "enable",
                "--service",
                "my-api",
                "--claim",
                "exp",
                "--claim",
                "nbf",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        claims = call_kwargs[1]["config"]["claims_to_verify"]
        assert "exp" in claims
        assert "nbf" in claims

    @pytest.mark.unit
    def test_enable_with_key_claim_name(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass key_claim_name to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="jwt",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["jwt", "enable", "--service", "my-api", "--key-claim", "sub"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["key_claim_name"] == "sub"

    @pytest.mark.unit
    def test_enable_with_secret_is_base64(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass secret_is_base64 flag."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="jwt",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["jwt", "enable", "--service", "my-api", "--secret-is-base64"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["secret_is_base64"] is True

    @pytest.mark.unit
    def test_enable_with_header_names(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass header_names to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="jwt",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "jwt",
                "enable",
                "--service",
                "my-api",
                "--header-name",
                "Authorization",
                "--header-name",
                "X-JWT-Token",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        headers = call_kwargs[1]["config"]["header_names"]
        assert "Authorization" in headers
        assert "X-JWT-Token" in headers

    @pytest.mark.unit
    def test_enable_with_max_expiration(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass maximum_expiration to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="jwt",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["jwt", "enable", "--service", "my-api", "--max-expiration", "86400"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["maximum_expiration"] == 86400

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
            ["jwt", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestJWTAddCredential(TestJWTCommands):
    """Tests for JWT add-credential command."""

    @pytest.mark.unit
    def test_add_credential_hs256_requires_secret(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """add-credential with HS256 should require --secret."""
        result = cli_runner.invoke(
            app,
            ["jwt", "add-credential", "my-user", "--algorithm", "HS256"],
        )

        assert result.exit_code == 1
        assert "secret" in result.stdout.lower()

    @pytest.mark.unit
    def test_add_credential_hs384_requires_secret(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """add-credential with HS384 should require --secret."""
        result = cli_runner.invoke(
            app,
            ["jwt", "add-credential", "my-user", "--algorithm", "HS384"],
        )

        assert result.exit_code == 1
        assert "secret" in result.stdout.lower()

    @pytest.mark.unit
    def test_add_credential_rs256_requires_rsa_key(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """add-credential with RS256 should require --rsa-public-key."""
        result = cli_runner.invoke(
            app,
            ["jwt", "add-credential", "my-user", "--algorithm", "RS256"],
        )

        assert result.exit_code == 1
        assert "rsa" in result.stdout.lower()

    @pytest.mark.unit
    def test_add_credential_es256_requires_rsa_key(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """add-credential with ES256 should require --rsa-public-key."""
        result = cli_runner.invoke(
            app,
            ["jwt", "add-credential", "my-user", "--algorithm", "ES256"],
        )

        assert result.exit_code == 1
        assert "rsa" in result.stdout.lower()

    @pytest.mark.unit
    def test_add_credential_invalid_algorithm(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """add-credential should reject invalid algorithm."""
        result = cli_runner.invoke(
            app,
            ["jwt", "add-credential", "my-user", "--algorithm", "INVALID"],
        )

        assert result.exit_code == 1
        assert "algorithm" in result.stdout.lower() or "invalid" in result.stdout.lower()

    @pytest.mark.unit
    def test_add_credential_hs256_with_secret(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-credential should create HS256 credential with secret."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "key": "jwt-issuer",
                "algorithm": "HS256",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "jwt",
                "add-credential",
                "my-user",
                "--algorithm",
                "HS256",
                "--secret",
                "my-secret-key",
            ],
        )

        assert result.exit_code == 0
        mock_consumer_manager.add_credential.assert_called_once()
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][0] == "my-user"
        assert call_args[0][1] == "jwt"
        assert call_args[0][2]["algorithm"] == "HS256"
        assert call_args[0][2]["secret"] == "my-secret-key"

    @pytest.mark.unit
    def test_add_credential_with_custom_key(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-credential should pass custom key (iss claim)."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "key": "my-issuer",
                "algorithm": "HS256",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "jwt",
                "add-credential",
                "my-user",
                "--algorithm",
                "HS256",
                "--secret",
                "my-secret",
                "--key",
                "my-issuer",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][2]["key"] == "my-issuer"

    @pytest.mark.unit
    def test_add_credential_rs256_with_rsa_key(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-credential should create RS256 credential with RSA key."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "key": "jwt-issuer",
                "algorithm": "RS256",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "jwt",
                "add-credential",
                "my-user",
                "--algorithm",
                "RS256",
                "--rsa-public-key",
                "-----BEGIN PUBLIC KEY-----\nTEST\n-----END PUBLIC KEY-----",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][2]["algorithm"] == "RS256"
        assert "-----BEGIN PUBLIC KEY-----" in call_args[0][2]["rsa_public_key"]

    @pytest.mark.unit
    def test_add_credential_reads_rsa_key_from_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
        temp_key_file: Path,
    ) -> None:
        """add-credential should read RSA key from file with @ prefix."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "key": "jwt-issuer",
                "algorithm": "RS256",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "jwt",
                "add-credential",
                "my-user",
                "--algorithm",
                "RS256",
                "--rsa-public-key",
                f"@{temp_key_file}",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert "TEST_KEY_DATA" in call_args[0][2]["rsa_public_key"]

    @pytest.mark.unit
    def test_add_credential_with_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-credential should pass tags."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "key": "jwt-issuer",
                "algorithm": "HS256",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "jwt",
                "add-credential",
                "my-user",
                "--algorithm",
                "HS256",
                "--secret",
                "my-secret",
                "--tag",
                "production",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert "production" in call_args[0][2]["tags"]

    @pytest.mark.unit
    def test_add_credential_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """add-credential should handle KongAPIError gracefully."""
        mock_consumer_manager.add_credential.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            [
                "jwt",
                "add-credential",
                "nonexistent",
                "--algorithm",
                "HS256",
                "--secret",
                "secret",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestJWTListCredentials(TestJWTCommands):
    """Tests for JWT list-credentials command."""

    @pytest.mark.unit
    def test_list_credentials_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-credentials should list JWT credentials."""
        mock_consumer_manager.list_credentials.return_value = [
            _create_mock_entity({"id": "cred-1", "key": "issuer-1", "algorithm": "HS256"}),
            _create_mock_entity({"id": "cred-2", "key": "issuer-2", "algorithm": "RS256"}),
        ]

        result = cli_runner.invoke(
            app,
            ["jwt", "list-credentials", "my-user"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.list_credentials.assert_called_once_with("my-user", "jwt")

    @pytest.mark.unit
    def test_list_credentials_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-credentials should support JSON output."""
        result = cli_runner.invoke(
            app,
            ["jwt", "list-credentials", "my-user", "--output", "json"],
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_list_credentials_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-credentials should handle KongAPIError gracefully."""
        mock_consumer_manager.list_credentials.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["jwt", "list-credentials", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
