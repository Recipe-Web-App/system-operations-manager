"""Unit tests for CORS security commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.security.cors import (
    register_cors_commands,
)


class TestCORSCommands:
    """Tests for CORS CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with CORS commands."""
        app = typer.Typer()
        register_cors_commands(app, lambda: mock_plugin_manager)
        return app

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["cors", "enable", "--origin", "https://example.com"])

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
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["cors", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
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
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["cors", "enable", "--route", "my-route"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["route"] == "my-route"

    @pytest.mark.unit
    def test_enable_with_origins(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass origins to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "cors",
                "enable",
                "--service",
                "my-api",
                "--origin",
                "https://example.com",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["origins"] == ["https://example.com"]

    @pytest.mark.unit
    def test_enable_with_wildcard_origin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support wildcard origin."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["cors", "enable", "--service", "my-api", "--origin", "*"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["origins"] == ["*"]

    @pytest.mark.unit
    def test_enable_with_multiple_origins(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support multiple --origin flags."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "cors",
                "enable",
                "--service",
                "my-api",
                "--origin",
                "https://example.com",
                "--origin",
                "https://app.example.com",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        origins = call_kwargs[1]["config"]["origins"]
        assert "https://example.com" in origins
        assert "https://app.example.com" in origins

    @pytest.mark.unit
    def test_enable_with_methods(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass methods to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "cors",
                "enable",
                "--service",
                "my-api",
                "--method",
                "GET",
                "--method",
                "POST",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        methods = call_kwargs[1]["config"]["methods"]
        assert "GET" in methods
        assert "POST" in methods

    @pytest.mark.unit
    def test_enable_with_headers(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass headers to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "cors",
                "enable",
                "--service",
                "my-api",
                "--header",
                "Accept",
                "--header",
                "Authorization",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        headers = call_kwargs[1]["config"]["headers"]
        assert "Accept" in headers
        assert "Authorization" in headers

    @pytest.mark.unit
    def test_enable_with_credentials(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass credentials flag to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["cors", "enable", "--service", "my-api", "--credentials"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["credentials"] is True

    @pytest.mark.unit
    def test_enable_with_max_age(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass max_age to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["cors", "enable", "--service", "my-api", "--max-age", "3600"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["max_age"] == 3600

    @pytest.mark.unit
    def test_enable_with_all_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass all options to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="cors",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "cors",
                "enable",
                "--service",
                "my-api",
                "--origin",
                "https://example.com",
                "--method",
                "GET",
                "--header",
                "Accept",
                "--exposed-header",
                "X-Request-Id",
                "--credentials",
                "--max-age",
                "3600",
                "--preflight-continue",
                "--private-network",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["origins"] == ["https://example.com"]
        assert config["methods"] == ["GET"]
        assert config["headers"] == ["Accept"]
        assert config["exposed_headers"] == ["X-Request-Id"]
        assert config["credentials"] is True
        assert config["max_age"] == 3600
        assert config["preflight_continue"] is True
        assert config["private_network"] is True

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
            ["cors", "enable", "--service", "my-api"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
