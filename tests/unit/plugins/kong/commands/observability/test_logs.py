"""Unit tests for logging commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.observability.logs import (
    register_logs_commands,
)


class TestLogsCommands:
    """Tests for logging CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with logs commands."""
        app = typer.Typer()
        register_logs_commands(app, lambda: mock_plugin_manager)
        return app


class TestHttpLogEnable(TestLogsCommands):
    """Tests for http log enable command."""

    @pytest.mark.unit
    def test_enable_requires_scope(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """http enable should fail without scope."""
        result = cli_runner.invoke(
            app,
            ["logs", "http", "enable", "--http-endpoint", "http://example.com"],
        )

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "global" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_global(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http enable should work with --global."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="http-log",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "http",
                "enable",
                "--http-endpoint",
                "http://logs.example.com",
                "--global",
            ],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "http-log"
        assert call_kwargs[1]["config"]["http_endpoint"] == "http://logs.example.com"

    @pytest.mark.unit
    def test_enable_with_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http enable should pass all options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="http-log",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "http",
                "enable",
                "--http-endpoint",
                "http://logs.example.com",
                "--method",
                "PUT",
                "--timeout",
                "5000",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["method"] == "PUT"
        assert config["timeout"] == 5000


class TestHttpLogGet(TestLogsCommands):
    """Tests for http log get command."""

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "http", "get"])

        assert result.exit_code == 0
        assert "no http log" in result.stdout.lower()


class TestHttpLogDisable(TestLogsCommands):
    """Tests for http log disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "http-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "http", "disable", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")


class TestFileLogEnable(TestLogsCommands):
    """Tests for file log enable command."""

    @pytest.mark.unit
    def test_enable_with_path(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file enable should work with --path."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="file-log",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "file",
                "enable",
                "--path",
                "/var/log/kong/access.log",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "file-log"
        assert call_kwargs[1]["config"]["path"] == "/var/log/kong/access.log"

    @pytest.mark.unit
    def test_enable_with_reopen(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file enable should pass reopen option."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="file-log",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "file",
                "enable",
                "--path",
                "/var/log/kong/access.log",
                "--reopen",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["reopen"] is True


class TestSyslogEnable(TestLogsCommands):
    """Tests for syslog enable command."""

    @pytest.mark.unit
    def test_enable_with_defaults(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog enable should work with default options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="syslog",
            enabled=True,
        )

        result = cli_runner.invoke(app, ["logs", "syslog", "enable", "--global"])

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "syslog"
        config = call_kwargs[1]["config"]
        assert config["host"] == "127.0.0.1"
        assert config["port"] == 514

    @pytest.mark.unit
    def test_enable_with_custom_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog enable should pass custom options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="syslog",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "syslog",
                "enable",
                "--host",
                "syslog.example.com",
                "--port",
                "1514",
                "--facility",
                "local0",
                "--severity",
                "warning",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["host"] == "syslog.example.com"
        assert config["port"] == 1514
        assert config["facility"] == "local0"
        assert config["severity"] == "warning"


class TestTcpLogEnable(TestLogsCommands):
    """Tests for tcp log enable command."""

    @pytest.mark.unit
    def test_enable_with_host_port(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """tcp enable should work with --host and --port."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="tcp-log",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "tcp",
                "enable",
                "--host",
                "logs.example.com",
                "--port",
                "5000",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "tcp-log"
        config = call_kwargs[1]["config"]
        assert config["host"] == "logs.example.com"
        assert config["port"] == 5000

    @pytest.mark.unit
    def test_enable_with_tls(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """tcp enable should pass TLS options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="tcp-log",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "tcp",
                "enable",
                "--host",
                "logs.example.com",
                "--port",
                "5000",
                "--tls",
                "--tls-sni",
                "logs.example.com",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["tls"] is True
        assert config["tls_sni"] == "logs.example.com"


class TestLogsErrorHandling(TestLogsCommands):
    """Tests for error handling in logs commands."""

    @pytest.mark.unit
    def test_http_enable_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http enable should handle KongAPIError gracefully."""
        mock_plugin_manager.enable.side_effect = KongAPIError(
            "Plugin error",
            status_code=400,
        )

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "http",
                "enable",
                "--http-endpoint",
                "http://logs.example.com",
                "--global",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
