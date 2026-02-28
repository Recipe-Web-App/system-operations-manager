"""Unit tests for metrics commands."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.config import PercentileMetrics
from system_operations_manager.integrations.kong.models.observability import (
    MetricsSummary,
)
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.plugins.kong.commands.observability.metrics import (
    register_metrics_commands,
)


class TestMetricsCommands:
    """Tests for metrics CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_plugin_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with metrics commands."""
        app = typer.Typer()
        register_metrics_commands(
            app,
            lambda: mock_plugin_manager,
            lambda: mock_observability_manager,
        )
        return app


class TestPrometheusEnable(TestMetricsCommands):
    """Tests for prometheus enable command."""

    @pytest.mark.unit
    def test_enable_requires_scope(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """prometheus enable should fail without --service, --route, or --global."""
        result = cli_runner.invoke(app, ["metrics", "prometheus", "enable"])

        assert result.exit_code == 1
        assert "service" in result.stdout.lower() or "global" in result.stdout.lower()

    @pytest.mark.unit
    def test_enable_with_global(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus enable should work with --global."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="prometheus",
            enabled=True,
        )

        result = cli_runner.invoke(app, ["metrics", "prometheus", "enable", "--global"])

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[0][0] == "prometheus"
        assert call_kwargs[1]["service"] is None
        assert call_kwargs[1]["route"] is None

    @pytest.mark.unit
    def test_enable_with_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus enable should work with --service."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="prometheus",
            enabled=True,
        )

        result = cli_runner.invoke(app, ["metrics", "prometheus", "enable", "--service", "my-api"])

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        assert call_kwargs[1]["service"] == "my-api"

    @pytest.mark.unit
    def test_enable_with_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus enable should pass config options."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="plugin-1",
            name="prometheus",
            enabled=True,
        )

        result = cli_runner.invoke(
            app,
            [
                "metrics",
                "prometheus",
                "enable",
                "--global",
                "--per-consumer",
                "--status-code-metrics",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_plugin_manager.enable.call_args
        config = call_kwargs[1]["config"]
        assert config["per_consumer"] is True
        assert config["status_code_metrics"] is True

    @pytest.mark.unit
    def test_enable_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus enable should handle KongAPIError gracefully."""
        mock_plugin_manager.enable.side_effect = KongAPIError(
            "Plugin error",
            status_code=400,
        )

        result = cli_runner.invoke(app, ["metrics", "prometheus", "enable", "--global"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestPrometheusGet(TestMetricsCommands):
    """Tests for prometheus get command."""

    @pytest.mark.unit
    def test_get_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus get should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["metrics", "prometheus", "get"])

        assert result.exit_code == 0
        assert "no prometheus" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_global_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus get should show config when global plugin found."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "prometheus",
            "service": None,
            "route": None,
            "config": {"per_consumer": False},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["metrics", "prometheus", "get"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once_with(name="prometheus")


class TestPrometheusDisable(TestMetricsCommands):
    """Tests for prometheus disable command."""

    @pytest.mark.unit
    def test_disable_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus disable should show message when plugin not found."""
        mock_plugin_manager.list.return_value = []

        result = cli_runner.invoke(app, ["metrics", "prometheus", "disable"])

        assert result.exit_code == 0
        assert "no prometheus" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus disable should skip confirmation with --force."""
        mock_plugin = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "prometheus",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["metrics", "prometheus", "disable", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")


class TestMetricsShow(TestMetricsCommands):
    """Tests for metrics show command."""

    @pytest.mark.unit
    def test_show_displays_summary(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics show should display aggregated metrics."""
        result = cli_runner.invoke(app, ["metrics", "show"])

        assert result.exit_code == 0
        mock_observability_manager.get_metrics_summary.assert_called_once()
        assert "10,000" in result.stdout or "10000" in result.stdout

    @pytest.mark.unit
    def test_show_with_service_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics show should pass service filter."""
        result = cli_runner.invoke(app, ["metrics", "show", "--service", "my-api"])

        assert result.exit_code == 0
        call_kwargs = mock_observability_manager.get_metrics_summary.call_args
        assert call_kwargs[1]["service_filter"] == "my-api"

    @pytest.mark.unit
    def test_show_no_data(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics show should show message when no data available."""
        mock_observability_manager.get_metrics_summary.return_value = MetricsSummary(
            total_requests=0
        )

        result = cli_runner.invoke(app, ["metrics", "show"])

        assert result.exit_code == 0
        assert "no metrics" in result.stdout.lower()


class TestMetricsList(TestMetricsCommands):
    """Tests for metrics list command."""

    @pytest.mark.unit
    def test_list_displays_metrics(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics list should display available metrics."""
        result = cli_runner.invoke(app, ["metrics", "list"])

        assert result.exit_code == 0
        mock_observability_manager.list_metrics.assert_called_once()

    @pytest.mark.unit
    def test_list_with_name_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics list should pass name filter."""
        result = cli_runner.invoke(app, ["metrics", "list", "--name", "kong_http"])

        assert result.exit_code == 0
        call_kwargs = mock_observability_manager.list_metrics.call_args
        assert call_kwargs[1]["name_filter"] == "kong_http"

    @pytest.mark.unit
    def test_list_with_type_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics list should pass type filter."""
        result = cli_runner.invoke(app, ["metrics", "list", "--type", "counter"])

        assert result.exit_code == 0
        call_kwargs = mock_observability_manager.list_metrics.call_args
        assert call_kwargs[1]["type_filter"] == "counter"

    @pytest.mark.unit
    def test_list_no_metrics(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics list should show message when no metrics found."""
        mock_observability_manager.list_metrics.return_value = []

        result = cli_runner.invoke(app, ["metrics", "list"])

        assert result.exit_code == 0
        assert "no metrics" in result.stdout.lower()


class TestMetricsStatus(TestMetricsCommands):
    """Tests for metrics status command."""

    @pytest.mark.unit
    def test_status_displays_node_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics status should display node status."""
        result = cli_runner.invoke(app, ["metrics", "status"])

        assert result.exit_code == 0
        mock_observability_manager.get_node_status.assert_called_once()
        assert "connected" in result.stdout.lower()

    @pytest.mark.unit
    def test_status_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics status should support JSON output."""
        result = cli_runner.invoke(app, ["metrics", "status", "--output", "json"])

        assert result.exit_code == 0
        mock_observability_manager.get_node_status.assert_called_once()


class TestMetricsPercentiles(TestMetricsCommands):
    """Tests for metrics percentiles command."""

    @pytest.mark.unit
    def test_percentiles_displays_values(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics percentiles should display P50/P95/P99 values."""
        result = cli_runner.invoke(app, ["metrics", "percentiles"])

        assert result.exit_code == 0
        mock_observability_manager.get_percentile_metrics.assert_called_once()
        # Should show percentile values
        assert "p50" in result.stdout.lower() or "25.5" in result.stdout

    @pytest.mark.unit
    def test_percentiles_with_service_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics percentiles should pass service filter."""
        result = cli_runner.invoke(app, ["metrics", "percentiles", "--service", "my-api"])

        assert result.exit_code == 0
        call_kwargs = mock_observability_manager.get_percentile_metrics.call_args
        assert call_kwargs[1]["service_filter"] == "my-api"

    @pytest.mark.unit
    def test_percentiles_with_route_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics percentiles should pass route filter."""
        result = cli_runner.invoke(app, ["metrics", "percentiles", "--route", "my-route"])

        assert result.exit_code == 0
        call_kwargs = mock_observability_manager.get_percentile_metrics.call_args
        assert call_kwargs[1]["route_filter"] == "my-route"

    @pytest.mark.unit
    def test_percentiles_no_data(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics percentiles should show message when no data."""
        mock_observability_manager.get_percentile_metrics.return_value = PercentileMetrics(
            p50_ms=None,
            p95_ms=None,
            p99_ms=None,
        )

        result = cli_runner.invoke(app, ["metrics", "percentiles"])

        assert result.exit_code == 0
        assert "no latency" in result.stdout.lower() or "no data" in result.stdout.lower()

    @pytest.mark.unit
    def test_percentiles_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics percentiles should support JSON output."""
        result = cli_runner.invoke(app, ["metrics", "percentiles", "--output", "json"])

        assert result.exit_code == 0
        mock_observability_manager.get_percentile_metrics.assert_called_once()

    @pytest.mark.unit
    def test_percentiles_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics percentiles should handle KongAPIError gracefully."""
        mock_observability_manager.get_percentile_metrics.side_effect = KongAPIError(
            "Metrics not available",
            status_code=500,
        )

        result = cli_runner.invoke(app, ["metrics", "percentiles"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestPrometheusGetServiceRouteMatch(TestMetricsCommands):
    """Tests for prometheus get command scope-matching branches."""

    @pytest.mark.unit
    def test_get_matching_service_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus get should find and display a plugin scoped to a service."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-svc",
            "name": "prometheus",
            "service": {"id": "svc-123", "name": "my-api"},
            "route": None,
            "config": {},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["metrics", "prometheus", "get", "--service", "my-api"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_get_matching_route_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus get should find and display a plugin scoped to a route."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-route",
            "name": "prometheus",
            "service": None,
            "route": {"id": "rt-456", "name": "my-route"},
            "config": {},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["metrics", "prometheus", "get", "--route", "my-route"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_get_no_match_for_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus get should print scope description when service not matched."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "prometheus",
            "service": None,
            "route": None,
            "config": {},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app, ["metrics", "prometheus", "get", "--service", "nonexistent"]
        )

        assert result.exit_code == 0
        assert "nonexistent" in result.stdout.lower() or "no prometheus" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_no_match_for_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus get should print scope description when route not matched."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "prometheus",
            "service": None,
            "route": None,
            "config": {},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["metrics", "prometheus", "get", "--route", "ghost-route"])

        assert result.exit_code == 0
        assert "ghost-route" in result.stdout.lower() or "no prometheus" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus get should handle KongAPIError gracefully."""
        mock_plugin_manager.list.side_effect = KongAPIError("API error", status_code=500)

        result = cli_runner.invoke(app, ["metrics", "prometheus", "get"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestPrometheusDisableServiceRouteMatch(TestMetricsCommands):
    """Tests for prometheus disable command scope-matching and cancel branches."""

    @pytest.mark.unit
    def test_disable_matching_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus disable should match and remove a service-scoped plugin."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-svc",
            "name": "prometheus",
            "service": {"id": "svc-123", "name": "my-api"},
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["metrics", "prometheus", "disable", "--service", "my-api", "--force"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-svc")

    @pytest.mark.unit
    def test_disable_matching_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus disable should match and remove a route-scoped plugin."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-rt",
            "name": "prometheus",
            "service": None,
            "route": {"id": "rt-456", "name": "my-route"},
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["metrics", "prometheus", "disable", "--route", "my-route", "--force"],
        )

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-rt")

    @pytest.mark.unit
    def test_disable_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus disable without --force should show cancelled when user says no."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "prometheus",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(app, ["metrics", "prometheus", "disable"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_plugin_manager.disable.assert_not_called()

    @pytest.mark.unit
    def test_disable_no_match_for_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus disable should show scope description when service not matched."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "prometheus",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["metrics", "prometheus", "disable", "--service", "ghost-svc", "--force"],
        )

        assert result.exit_code == 0
        assert "ghost-svc" in result.stdout.lower() or "no prometheus" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_no_match_for_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus disable should show scope description when route not matched."""
        mock_plugin: Any = MagicMock()
        mock_plugin.model_dump.return_value = {
            "id": "plugin-1",
            "name": "prometheus",
            "service": None,
            "route": None,
        }
        mock_plugin_manager.list.return_value = [mock_plugin]

        result = cli_runner.invoke(
            app,
            ["metrics", "prometheus", "disable", "--route", "ghost-rt", "--force"],
        )

        assert result.exit_code == 0
        assert "ghost-rt" in result.stdout.lower() or "no prometheus" in result.stdout.lower()

    @pytest.mark.unit
    def test_disable_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """prometheus disable should handle KongAPIError gracefully."""
        mock_plugin_manager.list.side_effect = KongAPIError("API error", status_code=500)

        result = cli_runner.invoke(app, ["metrics", "prometheus", "disable", "--force"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestMetricsShowNonTable(TestMetricsCommands):
    """Tests for metrics show command non-table output path."""

    @pytest.mark.unit
    def test_show_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics show should use formatter for non-table output."""
        result = cli_runner.invoke(app, ["metrics", "show", "--output", "json"])

        assert result.exit_code == 0
        mock_observability_manager.get_metrics_summary.assert_called_once()

    @pytest.mark.unit
    def test_show_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics show should handle KongAPIError gracefully."""
        mock_observability_manager.get_metrics_summary.side_effect = KongAPIError(
            "Scrape failed", status_code=503
        )

        result = cli_runner.invoke(app, ["metrics", "show"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestMetricsListNonTable(TestMetricsCommands):
    """Tests for metrics list command non-table output path."""

    @pytest.mark.unit
    def test_list_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics list should use formatter for non-table output."""
        result = cli_runner.invoke(app, ["metrics", "list", "--output", "json"])

        assert result.exit_code == 0
        mock_observability_manager.list_metrics.assert_called_once()

    @pytest.mark.unit
    def test_list_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics list should handle KongAPIError gracefully."""
        mock_observability_manager.list_metrics.side_effect = KongAPIError(
            "Scrape failed", status_code=503
        )

        result = cli_runner.invoke(app, ["metrics", "list"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestMetricsStatusMemoryAndNonTable(TestMetricsCommands):
    """Tests for metrics status memory table and non-table output paths."""

    @pytest.mark.unit
    def test_status_with_memory_info(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics status should render memory shared dict table when data present."""
        from system_operations_manager.integrations.kong.models.observability import NodeStatus

        mock_observability_manager.get_node_status.return_value = NodeStatus(
            database_reachable=True,
            server_connections_active=10,
            server_connections_reading=1,
            server_connections_writing=2,
            server_connections_waiting=7,
            server_connections_accepted=1000,
            server_connections_handled=1000,
            server_total_requests=5000,
            memory_lua_shared_dicts={
                "kong": {"allocated_slabs": 8, "capacity": 16},
                "kong_db_cache": {"allocated_slabs": 4, "capacity": 32},
            },
        )

        result = cli_runner.invoke(app, ["metrics", "status"])

        assert result.exit_code == 0
        assert "kong" in result.stdout.lower()

    @pytest.mark.unit
    def test_status_disconnected_db(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics status should show disconnected state for unreachable database."""
        from system_operations_manager.integrations.kong.models.observability import NodeStatus

        mock_observability_manager.get_node_status.return_value = NodeStatus(
            database_reachable=False,
            server_connections_active=0,
            server_connections_reading=0,
            server_connections_writing=0,
            server_connections_waiting=0,
            server_connections_accepted=0,
            server_connections_handled=0,
            server_total_requests=0,
        )

        result = cli_runner.invoke(app, ["metrics", "status"])

        assert result.exit_code == 0
        assert "disconnected" in result.stdout.lower()

    @pytest.mark.unit
    def test_status_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """metrics status should handle KongAPIError gracefully."""
        mock_observability_manager.get_node_status.side_effect = KongAPIError(
            "Status unavailable", status_code=503
        )

        result = cli_runner.invoke(app, ["metrics", "status"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
