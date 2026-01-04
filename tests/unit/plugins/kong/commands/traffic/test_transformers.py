"""Unit tests for request and response transformer commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.traffic.transformers import (
    register_transformer_commands,
)


class TestTransformerCommands:
    """Tests for request and response transformer CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with transformer commands."""
        app = typer.Typer()
        register_transformer_commands(app, lambda: mock_plugin_manager)
        return app


class TestRequestTransformerEnable(TestTransformerCommands):
    """Tests for request-transformer enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(
            app, ["request-transformer", "enable", "--add-header", "X-Custom:value"]
        )

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_requires_at_least_one_transformation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without any transformation option."""
        result = cli_runner.invoke(app, ["request-transformer", "enable", "--service", "my-api"])

        assert result.exit_code == 1
        assert "transformation" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_add_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass add header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Custom:value",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["headers"] == ["X-Custom:value"]

    @pytest.mark.unit
    def test_enable_with_multiple_add_headers(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support multiple --add-header options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Header1:value1",
                "--add-header",
                "X-Header2:value2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        headers = call_kwargs[1]["config"]["add"]["headers"]
        assert "X-Header1:value1" in headers
        assert "X-Header2:value2" in headers

    @pytest.mark.unit
    def test_enable_with_remove_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass remove header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--remove-header",
                "X-Internal",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["remove"]["headers"] == ["X-Internal"]

    @pytest.mark.unit
    def test_enable_with_rename_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass rename header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--rename-header",
                "Authorization:X-Auth",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["rename"]["headers"] == ["Authorization:X-Auth"]

    @pytest.mark.unit
    def test_enable_with_invalid_header_format(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should reject invalid header format."""
        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "InvalidFormat",
            ],
        )

        assert result.exit_code == 1
        assert "format" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_querystring(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass querystring options to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-querystring",
                "api_version:v2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["querystring"] == ["api_version:v2"]

    @pytest.mark.unit
    def test_enable_with_body(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass body options to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-body",
                "source:internal",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["body"] == ["source:internal"]

    @pytest.mark.unit
    def test_enable_with_mixed_operations(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support mixed add/remove/rename operations."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Custom:value",
                "--remove-header",
                "X-Internal",
                "--rename-header",
                "Auth:X-Auth",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["add"]["headers"] == ["X-Custom:value"]
        assert config["remove"]["headers"] == ["X-Internal"]
        assert config["rename"]["headers"] == ["Auth:X-Auth"]

    @pytest.mark.unit
    def test_enable_with_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should work with route scope."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-transformer",
                "enable",
                "--route",
                "my-route",
                "--add-header",
                "X-Custom:value",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["route"] == "my-route"

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
            [
                "request-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Custom:value",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestRequestTransformerGet(TestTransformerCommands):
    """Tests for request-transformer get command."""

    @pytest.mark.unit
    def test_get_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """get should fail without --service or --route."""
        result = cli_runner.invoke(app, ["request-transformer", "get"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["request-transformer", "get", "--service", "my-api"])

        assert result.exit_code == 0
        assert "no request transformer" in result.stdout.lower()


class TestRequestTransformerDisable(TestTransformerCommands):
    """Tests for request-transformer disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "request-transformer",
            "service": {"id": "service-123"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["request-transformer", "disable", "--service", "service-123", "--force"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")


class TestResponseTransformerEnable(TestTransformerCommands):
    """Tests for response-transformer enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(
            app, ["response-transformer", "enable", "--add-header", "X-Custom:value"]
        )

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_requires_at_least_one_transformation(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without any transformation option."""
        result = cli_runner.invoke(app, ["response-transformer", "enable", "--service", "my-api"])

        assert result.exit_code == 1
        assert "transformation" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_add_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass add header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "X-Response-Time:100ms",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["headers"] == ["X-Response-Time:100ms"]

    @pytest.mark.unit
    def test_enable_with_remove_header(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass remove header to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--remove-header",
                "Server",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["remove"]["headers"] == ["Server"]

    @pytest.mark.unit
    def test_enable_with_add_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass add json to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-json",
                "api_version:v2",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["add"]["json"] == ["api_version:v2"]

    @pytest.mark.unit
    def test_enable_with_mixed_operations(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should support mixed header and json operations."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="response-transformer",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "response-transformer",
                "enable",
                "--service",
                "my-api",
                "--add-header",
                "Cache-Control:no-cache",
                "--remove-header",
                "X-Powered-By",
                "--add-json",
                "status:success",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["add"]["headers"] == ["Cache-Control:no-cache"]
        assert config["add"]["json"] == ["status:success"]
        assert config["remove"]["headers"] == ["X-Powered-By"]


class TestResponseTransformerGet(TestTransformerCommands):
    """Tests for response-transformer get command."""

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["response-transformer", "get", "--service", "my-api"])

        assert result.exit_code == 0
        assert "no response transformer" in result.stdout.lower()


class TestResponseTransformerDisable(TestTransformerCommands):
    """Tests for response-transformer disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "response-transformer",
            "service": {"id": "service-123"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["response-transformer", "disable", "--service", "service-123", "--force"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")
