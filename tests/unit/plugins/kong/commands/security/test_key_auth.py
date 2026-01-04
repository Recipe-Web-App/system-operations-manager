"""Unit tests for key authentication security commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.security.key_auth import (
    register_key_auth_commands,
)


class TestKeyAuthCommands:
    """Tests for key-auth CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
        mock_consumer_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with key-auth commands."""
        app = typer.Typer()
        register_key_auth_commands(
            app,
            lambda: mock_plugin_manager,
            lambda: mock_consumer_manager,
        )
        return app


class TestKeyAuthEnable(TestKeyAuthCommands):
    """Tests for key-auth enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["key-auth", "enable"])

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
            name="key-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["key-auth", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "key-auth"
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
            name="key-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["key-auth", "enable", "--route", "my-route"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["route"] == "my-route"

    @pytest.mark.unit
    def test_enable_with_key_names(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass key_names to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="key-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "key-auth",
                "enable",
                "--service",
                "my-api",
                "--key-name",
                "apikey",
                "--key-name",
                "x-api-key",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert "apikey" in call_kwargs[1]["config"]["key_names"]
        assert "x-api-key" in call_kwargs[1]["config"]["key_names"]

    @pytest.mark.unit
    def test_enable_with_hide_credentials(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass hide_credentials flag."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="key-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["key-auth", "enable", "--service", "my-api", "--hide-credentials"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["hide_credentials"] is True

    @pytest.mark.unit
    def test_enable_with_key_locations(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass key location flags."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="key-auth",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "key-auth",
                "enable",
                "--service",
                "my-api",
                "--no-key-in-query",
                "--key-in-body",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["key_in_query"] is False
        assert config["key_in_body"] is True

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
            ["key-auth", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestKeyAuthCreateKey(TestKeyAuthCommands):
    """Tests for key-auth create-key command."""

    @pytest.mark.unit
    def test_create_key_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-key should create a credential."""
        result = cli_runner.invoke(
            app,
            ["key-auth", "create-key", "my-user"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.add_credential.assert_called_once()
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][0] == "my-user"
        assert call_args[0][1] == "key-auth"

    @pytest.mark.unit
    def test_create_key_with_custom_key(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-key should pass custom key value."""
        result = cli_runner.invoke(
            app,
            ["key-auth", "create-key", "my-user", "--key", "my-secret-api-key"],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][2]["key"] == "my-secret-api-key"

    @pytest.mark.unit
    def test_create_key_with_ttl(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-key should pass TTL value."""
        result = cli_runner.invoke(
            app,
            ["key-auth", "create-key", "my-user", "--ttl", "86400"],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        assert call_args[0][2]["ttl"] == 86400

    @pytest.mark.unit
    def test_create_key_with_tags(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-key should pass tags."""
        result = cli_runner.invoke(
            app,
            [
                "key-auth",
                "create-key",
                "my-user",
                "--tag",
                "production",
                "--tag",
                "api-v2",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_consumer_manager.add_credential.call_args
        tags = call_args[0][2]["tags"]
        assert "production" in tags
        assert "api-v2" in tags

    @pytest.mark.unit
    def test_create_key_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """create-key should handle KongAPIError gracefully."""
        mock_consumer_manager.add_credential.side_effect = KongAPIError(
            "Consumer not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["key-auth", "create-key", "nonexistent-user"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestKeyAuthListKeys(TestKeyAuthCommands):
    """Tests for key-auth list-keys command."""

    @pytest.mark.unit
    def test_list_keys_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-keys should list credentials."""
        result = cli_runner.invoke(
            app,
            ["key-auth", "list-keys", "my-user"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.list_credentials.assert_called_once_with("my-user", "key-auth")

    @pytest.mark.unit
    def test_list_keys_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """list-keys should support JSON output."""
        result = cli_runner.invoke(
            app,
            ["key-auth", "list-keys", "my-user", "--output", "json"],
        )

        assert result.exit_code == 0


class TestKeyAuthRevokeKey(TestKeyAuthCommands):
    """Tests for key-auth revoke-key command."""

    @pytest.mark.unit
    def test_revoke_key_with_confirmation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """revoke-key should prompt for confirmation."""
        result = cli_runner.invoke(
            app,
            ["key-auth", "revoke-key", "my-user", "key-123"],
            input="y\n",
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete_credential.assert_called_once_with(
            "my-user", "key-auth", "key-123"
        )

    @pytest.mark.unit
    def test_revoke_key_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """revoke-key should not delete when cancelled."""
        result = cli_runner.invoke(
            app,
            ["key-auth", "revoke-key", "my-user", "key-123"],
            input="n\n",
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete_credential.assert_not_called()

    @pytest.mark.unit
    def test_revoke_key_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """revoke-key --force should skip confirmation."""
        result = cli_runner.invoke(
            app,
            ["key-auth", "revoke-key", "my-user", "key-123", "--force"],
        )

        assert result.exit_code == 0
        mock_consumer_manager.delete_credential.assert_called_once_with(
            "my-user", "key-auth", "key-123"
        )

    @pytest.mark.unit
    def test_revoke_key_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """revoke-key should handle KongAPIError gracefully."""
        mock_consumer_manager.delete_credential.side_effect = KongAPIError(
            "Credential not found",
            status_code=404,
        )

        result = cli_runner.invoke(
            app,
            ["key-auth", "revoke-key", "my-user", "key-123", "--force"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
