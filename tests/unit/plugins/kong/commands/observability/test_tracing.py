"""Unit tests for tracing commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.observability.tracing import (
    register_tracing_commands,
)


class TestTracingCommands:
    """Tests for tracing CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with tracing commands."""
        app = typer.Typer()
        register_tracing_commands(app, lambda: mock_plugin_manager)
        return app


class TestOpenTelemetryEnable(TestTracingCommands):
    """Tests for opentelemetry enable command."""

    @pytest.mark.unit
    def test_enable_requires_scope(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """opentelemetry enable should fail without scope."""
        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "opentelemetry",
                "enable",
                "--endpoint",
                "http://otel:4317",
            ],
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
        """opentelemetry enable should work with --global."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="opentelemetry",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "opentelemetry",
                "enable",
                "--endpoint",
                "http://otel-collector:4317",
                "--global",
            ],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "opentelemetry"
        assert call_kwargs[1]["config"]["endpoint"] == "http://otel-collector:4317"

    @pytest.mark.unit
    def test_enable_with_headers(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """opentelemetry enable should parse headers."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="opentelemetry",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "opentelemetry",
                "enable",
                "--endpoint",
                "http://otel:4317",
                "--header",
                "Authorization=Bearer token",
                "--header",
                "X-Custom=value",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["headers"]["Authorization"] == "Bearer token"
        assert config["headers"]["X-Custom"] == "value"

    @pytest.mark.unit
    def test_enable_with_resource_attributes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """opentelemetry enable should parse resource attributes."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="opentelemetry",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "opentelemetry",
                "enable",
                "--endpoint",
                "http://otel:4317",
                "--resource-attribute",
                "service.name=my-api",
                "--resource-attribute",
                "environment=production",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["resource_attributes"]["service.name"] == "my-api"
        assert config["resource_attributes"]["environment"] == "production"

    @pytest.mark.unit
    def test_enable_with_batch_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """opentelemetry enable should pass batch options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="opentelemetry",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "opentelemetry",
                "enable",
                "--endpoint",
                "http://otel:4317",
                "--batch-span-count",
                "100",
                "--batch-flush-delay",
                "5",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["batch_span_count"] == 100
        assert config["batch_flush_delay"] == 5


class TestOpenTelemetryGet(TestTracingCommands):
    """Tests for opentelemetry get command."""

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """opentelemetry get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["tracing", "opentelemetry", "get"])

        assert result.exit_code == 0
        assert "no opentelemetry" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_global_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """opentelemetry get should show config when found."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "opentelemetry",
            "service": None,
            "route": None,
            "config": {"endpoint": "http://otel:4317"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["tracing", "opentelemetry", "get"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once_with(name="opentelemetry")


class TestOpenTelemetryDisable(TestTracingCommands):
    """Tests for opentelemetry disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """opentelemetry disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "opentelemetry",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["tracing", "opentelemetry", "disable", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")


class TestZipkinEnable(TestTracingCommands):
    """Tests for zipkin enable command."""

    @pytest.mark.unit
    def test_enable_requires_scope(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """zipkin enable should fail without scope."""
        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "zipkin",
                "enable",
                "--http-endpoint",
                "http://zipkin:9411/api/v2/spans",
            ],
        )

        assert result.exit_code == 1

    @pytest.mark.unit
    def test_enable_with_global(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """zipkin enable should work with --global."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="zipkin",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "zipkin",
                "enable",
                "--http-endpoint",
                "http://zipkin:9411/api/v2/spans",
                "--global",
            ],
        )

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "zipkin"
        config = call_kwargs[1]["config"]
        assert config["http_endpoint"] == "http://zipkin:9411/api/v2/spans"

    @pytest.mark.unit
    def test_enable_with_sample_ratio(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """zipkin enable should pass sample ratio."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="zipkin",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "zipkin",
                "enable",
                "--http-endpoint",
                "http://zipkin:9411/api/v2/spans",
                "--sample-ratio",
                "0.1",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["config"]["sample_ratio"] == 0.1

    @pytest.mark.unit
    def test_enable_with_header_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """zipkin enable should pass header type options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="zipkin",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "zipkin",
                "enable",
                "--http-endpoint",
                "http://zipkin:9411/api/v2/spans",
                "--header-type",
                "w3c",
                "--default-header-type",
                "w3c",
                "--global",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["header_type"] == "w3c"
        assert config["default_header_type"] == "w3c"


class TestZipkinGet(TestTracingCommands):
    """Tests for zipkin get command."""

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """zipkin get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["tracing", "zipkin", "get"])

        assert result.exit_code == 0
        assert "no zipkin" in result.stdout.lower()


class TestZipkinDisable(TestTracingCommands):
    """Tests for zipkin disable command."""

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """zipkin disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "zipkin",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["tracing", "zipkin", "disable", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")


class TestTracingErrorHandling(TestTracingCommands):
    """Tests for error handling in tracing commands."""

    @pytest.mark.unit
    def test_opentelemetry_enable_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """opentelemetry enable should handle KongAPIError gracefully."""
        mock_plugin_manager.enable.side_effect = KongAPIError(
            "Plugin error",
            status_code=400,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "opentelemetry",
                "enable",
                "--endpoint",
                "http://otel:4317",
                "--global",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_zipkin_enable_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """zipkin enable should handle KongAPIError gracefully."""
        mock_plugin_manager.enable.side_effect = KongAPIError(
            "Plugin error",
            status_code=400,
        )

        result = cli_runner.invoke(
            app,
            [
                "tracing",
                "zipkin",
                "enable",
                "--http-endpoint",
                "http://zipkin:9411/api/v2/spans",
                "--global",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
