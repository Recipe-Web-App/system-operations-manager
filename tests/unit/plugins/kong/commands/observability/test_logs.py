"""Unit tests for logging commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.observability.logs import (
    _find_log_plugin,
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


# =============================================================================
# _find_log_plugin helper tests
# =============================================================================


class TestFindLogPlugin(TestLogsCommands):
    """Tests for the _find_log_plugin helper function."""

    @pytest.mark.unit
    def test_find_log_plugin_not_list(
        self,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """_find_log_plugin returns None when manager.list returns a non-list."""
        mock_plugin_manager.list.return_value = {"error": "unexpected"}

        result = _find_log_plugin(mock_plugin_manager, "http-log", None, None)

        assert result is None

    @pytest.mark.unit
    def test_find_log_plugin_service_match(
        self,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """_find_log_plugin returns plugin data when service id matches."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-svc-1",
            "name": "http-log",
            "service": {"id": "svc-abc", "name": "my-service"},
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = _find_log_plugin(mock_plugin_manager, "http-log", "svc-abc", None)

        assert result is not None
        assert result["id"] == "plugin-svc-1"

    @pytest.mark.unit
    def test_find_log_plugin_service_match_by_name(
        self,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """_find_log_plugin returns plugin data when service name matches."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-svc-2",
            "name": "http-log",
            "service": {"id": "svc-xyz", "name": "my-service"},
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = _find_log_plugin(mock_plugin_manager, "http-log", "my-service", None)

        assert result is not None
        assert result["id"] == "plugin-svc-2"

    @pytest.mark.unit
    def test_find_log_plugin_route_match(
        self,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """_find_log_plugin returns plugin data when route id matches."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-route-1",
            "name": "http-log",
            "service": None,
            "route": {"id": "route-abc", "name": "my-route"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = _find_log_plugin(mock_plugin_manager, "http-log", None, "route-abc")

        assert result is not None
        assert result["id"] == "plugin-route-1"

    @pytest.mark.unit
    def test_find_log_plugin_global_match(
        self,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """_find_log_plugin returns plugin data for global scope (no service, no route)."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-global-1",
            "name": "http-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = _find_log_plugin(mock_plugin_manager, "http-log", None, None)

        assert result is not None
        assert result["id"] == "plugin-global-1"

    @pytest.mark.unit
    def test_find_log_plugin_no_match(
        self,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """_find_log_plugin returns None when no plugin matches the scope."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-svc-99",
            "name": "http-log",
            "service": {"id": "other-svc", "name": "other-service"},
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        # Searching for "svc-abc" but only "other-svc" exists
        result = _find_log_plugin(mock_plugin_manager, "http-log", "svc-abc", None)

        assert result is None


# =============================================================================
# HTTP log get/disable extended tests
# =============================================================================


class TestHttpLogGetExtended(TestLogsCommands):
    """Extended tests for http log get command."""

    @pytest.mark.unit
    def test_get_found_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http get should display plugin config when plugin is found globally."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-123",
            "name": "http-log",
            "config": {"http_endpoint": "http://example.com"},
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "http", "get"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once_with(name="http-log")

    @pytest.mark.unit
    def test_get_for_service_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http get should show not-found message for service scope."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "http", "get", "--service", "my-svc"])

        assert result.exit_code == 0
        assert "no http log" in result.stdout.lower()
        assert "my-svc" in result.stdout

    @pytest.mark.unit
    def test_get_for_route_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http get should show not-found message for route scope."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "http", "get", "--route", "my-route"])

        assert result.exit_code == 0
        assert "no http log" in result.stdout.lower()
        assert "my-route" in result.stdout


class TestHttpLogDisableExtended(TestLogsCommands):
    """Extended tests for http log disable command."""

    @pytest.mark.unit
    def test_disable_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http disable should show not-found message when plugin absent."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "http", "disable"])

        assert result.exit_code == 0
        assert "no http log" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_no_plugin_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http disable should error when plugin has no id field."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "name": "http-log",
            "service": None,
            "route": None,
            # no "id" key
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "http", "disable", "--force"])

        assert result.exit_code == 1
        assert "plugin id not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_confirmation_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http disable should cancel when user declines confirmation."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-123",
            "name": "http-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "http", "disable"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_plugin_manager.disable.assert_not_called()

    @pytest.mark.unit
    def test_disable_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """http disable should handle KongAPIError from disable call."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-123",
            "name": "http-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]
        mock_plugin_manager.disable.side_effect = KongAPIError(
            "Disable failed",
            status_code=500,
        )

        result = cli_runner.invoke(app, ["logs", "http", "disable", "--force"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


# =============================================================================
# File log get/disable tests
# =============================================================================


class TestFileLogGet(TestLogsCommands):
    """Tests for file log get command."""

    @pytest.mark.unit
    def test_get_found_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file get should display plugin config when plugin is found."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "file-plugin-1",
            "name": "file-log",
            "config": {"path": "/var/log/kong/access.log"},
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "file", "get"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once_with(name="file-log")

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file get should show not-found message when plugin is absent."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "file", "get", "--service", "my-svc"])

        assert result.exit_code == 0
        assert "no file log" in result.stdout.lower()


class TestFileLogDisable(TestLogsCommands):
    """Tests for file log disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "file-plugin-1",
            "name": "file-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "file", "disable", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("file-plugin-1")

    @pytest.mark.unit
    def test_disable_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file disable should show not-found message when plugin absent."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "file", "disable"])

        assert result.exit_code == 0
        assert "no file log" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_no_plugin_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file disable should error when plugin has no id field."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "name": "file-log",
            "service": None,
            "route": None,
            # no "id" key
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "file", "disable", "--force"])

        assert result.exit_code == 1
        assert "plugin id not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file disable should cancel when user declines confirmation."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "file-plugin-1",
            "name": "file-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "file", "disable"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_plugin_manager.disable.assert_not_called()

    @pytest.mark.unit
    def test_disable_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """file disable should handle KongAPIError from disable call."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "file-plugin-1",
            "name": "file-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]
        mock_plugin_manager.disable.side_effect = KongAPIError(
            "File disable failed",
            status_code=500,
        )

        result = cli_runner.invoke(app, ["logs", "file", "disable", "--force"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


# =============================================================================
# Syslog enable/get/disable extended tests
# =============================================================================


class TestSyslogEnableExtended(TestLogsCommands):
    """Extended tests for syslog enable command covering optional severity params."""

    @pytest.mark.unit
    def test_enable_with_severity_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog enable should include optional severity config when provided."""
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
                "--successful-severity",
                "info",
                "--client-errors-severity",
                "warning",
                "--server-errors-severity",
                "err",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["successful_severity"] == "info"
        assert config["client_errors_severity"] == "warning"
        assert config["server_errors_severity"] == "err"

    @pytest.mark.unit
    def test_enable_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog enable should handle KongAPIError gracefully."""
        mock_plugin_manager.enable.side_effect = KongAPIError(
            "Syslog enable failed",
            status_code=400,
        )

        result = cli_runner.invoke(app, ["logs", "syslog", "enable", "--global"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestSyslogGet(TestLogsCommands):
    """Tests for syslog get command."""

    @pytest.mark.unit
    def test_get_found_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog get should display plugin config when plugin is found."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "syslog-plugin-1",
            "name": "syslog",
            "config": {"host": "127.0.0.1", "port": 514},
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "syslog", "get"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once_with(name="syslog")

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog get should show not-found message when plugin is absent."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "syslog", "get", "--service", "my-svc"])

        assert result.exit_code == 0
        assert "no syslog" in result.stdout.lower()


class TestSyslogDisable(TestLogsCommands):
    """Tests for syslog disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "syslog-plugin-1",
            "name": "syslog",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "syslog", "disable", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("syslog-plugin-1")

    @pytest.mark.unit
    def test_disable_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog disable should show not-found message when plugin absent."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "syslog", "disable"])

        assert result.exit_code == 0
        assert "no syslog" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_no_plugin_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog disable should error when plugin has no id field."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "name": "syslog",
            "service": None,
            "route": None,
            # no "id" key
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "syslog", "disable", "--force"])

        assert result.exit_code == 1
        assert "plugin id not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """syslog disable should cancel when user declines confirmation."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "syslog-plugin-1",
            "name": "syslog",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "syslog", "disable"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_plugin_manager.disable.assert_not_called()


# =============================================================================
# TCP log get/disable extended tests
# =============================================================================


class TestTcpLogGet(TestLogsCommands):
    """Tests for tcp log get command."""

    @pytest.mark.unit
    def test_get_found_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """tcp get should display plugin config when plugin is found."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "tcp-plugin-1",
            "name": "tcp-log",
            "config": {"host": "logs.example.com", "port": 5000},
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "tcp", "get"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once_with(name="tcp-log")

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """tcp get should show not-found message when plugin is absent."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "tcp", "get", "--service", "my-svc"])

        assert result.exit_code == 0
        assert "no tcp log" in result.stdout.lower()


class TestTcpLogDisable(TestLogsCommands):
    """Tests for tcp log disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """tcp disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "tcp-plugin-1",
            "name": "tcp-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "tcp", "disable", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("tcp-plugin-1")

    @pytest.mark.unit
    def test_disable_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """tcp disable should show not-found message when plugin absent."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["logs", "tcp", "disable"])

        assert result.exit_code == 0
        assert "no tcp log" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """tcp disable should cancel when user declines confirmation."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "tcp-plugin-1",
            "name": "tcp-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["logs", "tcp", "disable"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_plugin_manager.disable.assert_not_called()

    @pytest.mark.unit
    def test_disable_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """tcp disable should handle KongAPIError from disable call."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "tcp-plugin-1",
            "name": "tcp-log",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]
        mock_plugin_manager.disable.side_effect = KongAPIError(
            "TCP disable failed",
            status_code=500,
        )

        result = cli_runner.invoke(app, ["logs", "tcp", "disable", "--force"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
