"""Unit tests for OAuth2 security commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.security.oauth2 import (
    register_oauth2_commands,
)

from .conftest import _create_mock_entity


class TestOAuth2Commands:
    """Tests for OAuth2 CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
        mock_consumer_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with OAuth2 commands."""
        app = typer.Typer()
        register_oauth2_commands(
            app,
            lambda: mock_plugin_manager,
            lambda: mock_consumer_manager,
        )
        return app


class TestOAuth2Enable(TestOAuth2Commands):
    """Tests for OAuth2 enable command."""

    @pytest.mark.unit
    def test_enable_requires_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service."""
        result = cli_runner.invoke(app, ["oauth2", "enable"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower()

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
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["oauth2", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "oauth2"
        assert call_kwargs[1]["service"] == "my-api"

    @pytest.mark.unit
    def test_enable_with_scopes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass scopes to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "enable",
                "--service",
                "my-api",
                "--scope",
                "read",
                "--scope",
                "write",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        scopes = call_kwargs[1]["config"]["scopes"]
        assert "read" in scopes
        assert "write" in scopes

    @pytest.mark.unit
    def test_enable_with_mandatory_scope(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass mandatory_scope flag."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "enable",
                "--service",
                "my-api",
                "--scope",
                "read",
                "--mandatory-scope",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["mandatory_scope"] is True

    @pytest.mark.unit
    def test_enable_with_grant_types(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass grant type flags."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "enable",
                "--service",
                "my-api",
                "--enable-client-credentials",
                "--enable-password-grant",
                "--disable-authorization-code",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["enable_client_credentials"] is True
        assert config["enable_password_grant"] is True
        assert config["enable_authorization_code"] is False

    @pytest.mark.unit
    def test_enable_with_token_expiration(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass token_expiration to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["oauth2", "enable", "--service", "my-api", "--token-expiration", "3600"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["token_expiration"] == 3600

    @pytest.mark.unit
    def test_enable_with_provision_key(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass provision_key to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "enable",
                "--service",
                "my-api",
                "--provision-key",
                "my-secret-provision-key",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["provision_key"] == "my-secret-provision-key"

    @pytest.mark.unit
    def test_enable_with_anonymous(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass anonymous consumer ID."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["oauth2", "enable", "--service", "my-api", "--anonymous", "anon-consumer-id"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["anonymous"] == "anon-consumer-id"

    @pytest.mark.unit
    def test_enable_with_global_credentials(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass global_credentials flag."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["oauth2", "enable", "--service", "my-api", "--global-credentials"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["global_credentials"] is True

    @pytest.mark.unit
    def test_enable_with_accept_http(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass accept_http_if_already_terminated flag."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="oauth2",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["oauth2", "enable", "--service", "my-api", "--accept-http"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["accept_http_if_already_terminated"] is True

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
            ["oauth2", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestOAuth2CreateApp(TestOAuth2Commands):
    """Tests for OAuth2 create-app command."""

    @pytest.mark.unit
    def test_create_app_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-app should create an OAuth2 application."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "name": "My App",
                "client_id": "generated-client-id",
                "client_secret": "generated-secret",
                "redirect_uris": ["https://app.example.com/callback"],
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "create-app",
                "my-user",
                "--name",
                "My App",
                "--redirect-uri",
                "https://app.example.com/callback",
            ],
        )

        assert result.exit_code == 0
        mock_consumer_manager.add_credential.assert_called_once()
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][0] == "my-user"
        assert call_args[0][1] == "oauth2"
        assert call_args[0][2]["name"] == "My App"
        assert "https://app.example.com/callback" in call_args[0][2]["redirect_uris"]

    @pytest.mark.unit
    def test_create_app_with_multiple_redirect_uris(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-app should support multiple redirect URIs."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "name": "My App",
                "client_id": "generated-client-id",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "create-app",
                "my-user",
                "--name",
                "My App",
                "--redirect-uri",
                "https://app.example.com/callback",
                "--redirect-uri",
                "myapp://callback",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        redirect_uris = call_args[0][2]["redirect_uris"]
        assert "https://app.example.com/callback" in redirect_uris
        assert "myapp://callback" in redirect_uris

    @pytest.mark.unit
    def test_create_app_with_custom_client_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-app should pass custom client_id."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "name": "My App",
                "client_id": "custom-client-id",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "create-app",
                "my-user",
                "--name",
                "My App",
                "--redirect-uri",
                "https://app.example.com/callback",
                "--client-id",
                "custom-client-id",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][2]["client_id"] == "custom-client-id"

    @pytest.mark.unit
    def test_create_app_with_custom_client_secret(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-app should pass custom client_secret."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "name": "My App",
                "client_id": "client-id",
                "client_secret": "custom-secret",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "create-app",
                "my-user",
                "--name",
                "My App",
                "--redirect-uri",
                "https://app.example.com/callback",
                "--client-secret",
                "custom-secret",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][2]["client_secret"] == "custom-secret"

    @pytest.mark.unit
    def test_create_app_with_hash_secret(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-app should pass hash_secret flag."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "name": "My App",
                "client_id": "client-id",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "create-app",
                "my-user",
                "--name",
                "My App",
                "--redirect-uri",
                "https://app.example.com/callback",
                "--hash-secret",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][2]["hash_secret"] is True

    @pytest.mark.unit
    def test_create_app_with_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-app should pass tags."""
        mock_consumer_manager.add_credential.return_value = _create_mock_entity(
            {
                "id": "cred-1",
                "name": "My App",
                "client_id": "client-id",
            }
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "create-app",
                "my-user",
                "--name",
                "My App",
                "--redirect-uri",
                "https://app.example.com/callback",
                "--tag",
                "production",
                "--tag",
                "mobile",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        tags = call_args[0][2]["tags"]
        assert "production" in tags
        assert "mobile" in tags

    @pytest.mark.unit
    def test_create_app_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-app should handle KongAPIError gracefully."""
        mock_consumer_manager.add_credential.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            [
                "oauth2",
                "create-app",
                "nonexistent",
                "--name",
                "My App",
                "--redirect-uri",
                "https://app.example.com/callback",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestOAuth2ListApps(TestOAuth2Commands):
    """Tests for OAuth2 list-apps command."""

    @pytest.mark.unit
    def test_list_apps_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-apps should list OAuth2 applications."""
        mock_consumer_manager.list_credentials.return_value = [
            _create_mock_entity({"id": "cred-1", "name": "App 1", "client_id": "client-1"}),
            _create_mock_entity({"id": "cred-2", "name": "App 2", "client_id": "client-2"}),
        ]

        result = cli_runner.invoke(
            app,
            ["oauth2", "list-apps", "my-user"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.list_credentials.assert_called_once_with("my-user", "oauth2")

    @pytest.mark.unit
    def test_list_apps_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-apps should support JSON output."""
        result = cli_runner.invoke(
            app,
            ["oauth2", "list-apps", "my-user", "--output", "json"],
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_list_apps_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-apps should handle KongAPIError gracefully."""
        mock_consumer_manager.list_credentials.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["oauth2", "list-apps", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
