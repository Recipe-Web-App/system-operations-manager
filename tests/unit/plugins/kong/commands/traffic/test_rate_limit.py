"""Unit tests for rate limiting commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.traffic.rate_limit import (
    register_rate_limit_commands,
)


class TestRateLimitCommands:
    """Tests for rate limiting CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with rate limit commands."""
        app = typer.Typer()
        register_rate_limit_commands(app, lambda: mock_plugin_manager)
        return app


class TestRateLimitEnable(TestRateLimitCommands):
    """Tests for rate-limit enable command."""

    @pytest.mark.unit
    def test_enable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["rate-limit", "enable", "--minute", "100"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "route" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_requires_at_least_one_limit(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should fail without any rate limit specified."""
        result = cli_runner.invoke(app, ["rate-limit", "enable", "--service", "my-api"])

        assert result.exit_code == 1
        assert "limit" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_service_and_minute(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should call plugin manager with correct args."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="rate-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["rate-limit", "enable", "--service", "my-api", "--minute", "100"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["service"] == "my-api"
        assert call_kwargs[1]["config"]["minute"] == 100

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
            name="rate-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            ["rate-limit", "enable", "--route", "my-route", "--second", "10"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["route"] == "my-route"

    @pytest.mark.unit
    def test_enable_with_multiple_limits(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass all limit options to config."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="rate-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "rate-limit",
                "enable",
                "--service",
                "my-api",
                "--second",
                "10",
                "--minute",
                "100",
                "--hour",
                "5000",
                "--day",
                "50000",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["second"] == 10
        assert config["minute"] == 100
        assert config["hour"] == 5000
        assert config["day"] == 50000

    @pytest.mark.unit
    def test_enable_with_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass policy option."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="rate-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "rate-limit",
                "enable",
                "--service",
                "my-api",
                "--minute",
                "100",
                "--policy",
                "cluster",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["policy"] == "cluster"

    @pytest.mark.unit
    def test_enable_with_invalid_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should reject invalid policy."""
        result = cli_runner.invoke(
            app,
            [
                "rate-limit",
                "enable",
                "--service",
                "my-api",
                "--minute",
                "100",
                "--policy",
                "invalid",
            ],
        )

        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_limit_by(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass limit-by option."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="rate-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "rate-limit",
                "enable",
                "--service",
                "my-api",
                "--minute",
                "100",
                "--limit-by",
                "consumer",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["limit_by"] == "consumer"

    @pytest.mark.unit
    def test_enable_with_header_limit_by_requires_header_name(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """enable should require header-name when limit-by is header."""
        result = cli_runner.invoke(
            app,
            [
                "rate-limit",
                "enable",
                "--service",
                "my-api",
                "--minute",
                "100",
                "--limit-by",
                "header",
            ],
        )

        assert result.exit_code == 1
        assert "header-name" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_header_name(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """enable should pass header-name when limit-by is header."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="rate-limiting",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "rate-limit",
                "enable",
                "--service",
                "my-api",
                "--minute",
                "100",
                "--limit-by",
                "header",
                "--header-name",
                "X-Custom-Header",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["header_name"] == "X-Custom-Header"

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
            ["rate-limit", "enable", "--service", "my-api", "--minute", "100"],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestRateLimitGet(TestRateLimitCommands):
    """Tests for rate-limit get command."""

    @pytest.mark.unit
    def test_get_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """get should fail without --service or --route."""
        result = cli_runner.invoke(app, ["rate-limit", "get"])

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
            "name": "rate-limiting",
            "service": {"id": "service-123"},
            "config": {"minute": 100},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["rate-limit", "get", "--service", "service-123"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once_with(name="rate-limiting")

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["rate-limit", "get", "--service", "my-api"])

        assert result.exit_code == 0
        assert "no rate limiting" in result.stdout.lower()


class TestRateLimitDisable(TestRateLimitCommands):
    """Tests for rate-limit disable command."""

    @pytest.mark.unit
    def test_disable_requires_service_or_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """disable should fail without --service or --route."""
        result = cli_runner.invoke(app, ["rate-limit", "disable"])

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

        result = cli_runner.invoke(app, ["rate-limit", "disable", "--service", "my-api"])

        assert result.exit_code == 0
        assert "no rate limiting" in result.stdout.lower()

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
            "name": "rate-limiting",
            "service": {"id": "service-123"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app, ["rate-limit", "disable", "--service", "service-123", "--force"]
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
            "name": "rate-limiting",
            "service": {"id": "service-123"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app, ["rate-limit", "disable", "--service", "service-123"], input="n\n"
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_not_called()
        assert "cancelled" in result.stdout.lower()
