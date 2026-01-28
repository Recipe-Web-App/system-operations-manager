"""Unit tests for request size limiting commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.traffic.request_size import (
    register_request_size_commands,
)


class TestRequestSizeCommands:
    """Tests for request size limiting CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with request size commands."""
        app = typer.Typer()
        register_request_size_commands(app, lambda: mock_plugin_manager)
        return app


class TestRequestSizeEnable(TestRequestSizeCommands):
    """Tests for request-size enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["request-size", "enable"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_service_default_size(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should use default size when not specified."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-size-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(app, ["request-size", "enable", "--service", "my-api"])

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["allowed_payload_size"] == 128
        assert call_kwargs[1]["config"]["size_unit"] == "megabytes"

    @pytest.mark.unit
    def test_enable_with_custom_size(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass custom size to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-size-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-size",
                "enable",
                "--service",
                "my-api",
                "--allowed-payload-size",
                "10",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["allowed_payload_size"] == 10

    @pytest.mark.unit
    def test_enable_with_size_unit(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass size unit to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-size-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-size",
                "enable",
                "--service",
                "my-api",
                "--allowed-payload-size",
                "512",
                "--size-unit",
                "kilobytes",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["size_unit"] == "kilobytes"

    @pytest.mark.unit
    def test_enable_with_invalid_size_unit(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should reject invalid size unit."""
        result = cli_runner.invoke(
            app,
            [
                "request-size",
                "enable",
                "--service",
                "my-api",
                "--size-unit",
                "gigabytes",
            ],
        )

        assert result.exit_code == 1
        assert "gigabytes" in result.stdout.lower() or "invalid" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_require_content_length(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass require_content_length to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="request-size-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "request-size",
                "enable",
                "--service",
                "my-api",
                "--require-content-length",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["require_content_length"] is True

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
            name="request-size-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(app, ["request-size", "enable", "--route", "my-route"])

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

        result = cli_runner.invoke(app, ["request-size", "enable", "--service", "my-api"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestRequestSizeGet(TestRequestSizeCommands):
    """Tests for request-size get command."""

    @pytest.mark.unit
    def test_get_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """get should fail without --service or --route."""
        result = cli_runner.invoke(app, ["request-size", "get"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_with_service_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should show plugin config when found."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "request-size-limiting",
            "service": {"id": "service-123"},
            "config": {"allowed_payload_size": 128},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["request-size", "get", "--service", "service-123"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once_with(name="request-size-limiting")

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["request-size", "get", "--service", "my-api"])

        assert result.exit_code == 0
        assert "no request size limiting" in result.stdout.lower()


class TestRequestSizeDisable(TestRequestSizeCommands):
    """Tests for request-size disable command."""

    @pytest.mark.unit
    def test_disable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """disable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["request-size", "disable"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["request-size", "disable", "--service", "my-api"])

        assert result.exit_code == 0
        assert "no request size limiting" in result.stdout.lower()

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
            "name": "request-size-limiting",
            "service": {"id": "service-123"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app, ["request-size", "disable", "--service", "service-123", "--force"]
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")
        assert "disabled" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """disable should cancel when user declines confirmation."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "request-size-limiting",
            "service": {"id": "service-123"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app, ["request-size", "disable", "--service", "service-123"], input="n\n"
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_not_called()
        assert "cancelled" in result.stdout.lower()
