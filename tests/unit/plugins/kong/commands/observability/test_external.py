"""Unit tests for external observability commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.observability import (
    ObservabilityClientError,
)
from system_operations_manager.plugins.kong.commands.observability.external import (
    register_external_logs_commands,
    register_external_metrics_commands,
    register_external_tracing_commands,
)

# =============================================================================
# Metrics command tests
# =============================================================================


class TestMetricsCommands:
    """Tests for external Prometheus metrics commands."""

    @pytest.fixture
    def mock_metrics_manager(self) -> MagicMock:
        """Create a mock MetricsManager."""
        manager = MagicMock()
        manager.query_range.return_value = [
            {
                "metric": {"__name__": "kong_http_requests_total", "service": "api-1"},
                "values": [["1700000000", "100"], ["1700001000", "200"]],
            }
        ]
        manager.get_request_rate.return_value = [
            {
                "metric": {"service": "api-1", "route": "route-1"},
                "value": ["1700000000", "12.34"],
            }
        ]
        manager.get_latency_percentiles.return_value = {
            0.5: [{"value": ["1700000000", "25.5"]}],
            0.9: [{"value": ["1700000000", "85.2"]}],
            0.99: [{"value": ["1700000000", "150.7"]}],
        }
        manager.get_error_rate.return_value = [
            {"value": ["1700000000", "0.005"]},
        ]
        manager.get_summary.return_value = {
            "request_rate_per_second": 42.0,
            "error_rate": 0.01,
            "latency_ms": {"p50": 25.5, "p99": 150.7},
        }
        return manager

    @pytest.fixture
    def app(self, mock_metrics_manager: MagicMock) -> typer.Typer:
        """Create a test app with external metrics commands."""
        app = typer.Typer()
        register_external_metrics_commands(app, lambda: mock_metrics_manager)
        return app

    @pytest.fixture
    def app_none_manager(self) -> typer.Typer:
        """Create a test app whose metrics manager returns None."""
        app = typer.Typer()
        register_external_metrics_commands(app, lambda: None)
        return app


class TestMetricsQueryExec(TestMetricsCommands):
    """Tests for 'query exec' sub-command."""

    @pytest.mark.unit
    def test_exec_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query exec should call query_range and display results."""
        result = cli_runner.invoke(app, ["query", "exec", "rate(kong_http_requests_total[5m])"])

        assert result.exit_code == 0
        mock_metrics_manager.query_range.assert_called_once()

    @pytest.mark.unit
    def test_exec_displays_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """query exec should render a table with Labels and Value columns."""
        result = cli_runner.invoke(app, ["query", "exec", "rate(kong_http_requests_total[5m])"])

        assert result.exit_code == 0
        # Table header columns or row content must appear
        assert "service=api-1" in result.stdout or "api-1" in result.stdout

    @pytest.mark.unit
    def test_exec_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query exec should delegate to formatter for non-table output."""
        result = cli_runner.invoke(
            app,
            ["query", "exec", "rate(kong_http_requests_total[5m])", "--output", "json"],
        )

        assert result.exit_code == 0
        mock_metrics_manager.query_range.assert_called_once()

    @pytest.mark.unit
    def test_exec_custom_range_and_step(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query exec should pass --range and --step to query_range."""
        result = cli_runner.invoke(
            app,
            [
                "query",
                "exec",
                "kong_upstream_target_health",
                "--range",
                "30m",
                "--step",
                "5m",
            ],
        )

        assert result.exit_code == 0
        _, kwargs = mock_metrics_manager.query_range.call_args
        assert kwargs.get("step") == "5m"

    @pytest.mark.unit
    def test_exec_no_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query exec should show 'No results' message when empty list returned."""
        mock_metrics_manager.query_range.return_value = []

        result = cli_runner.invoke(app, ["query", "exec", "nonexistent_metric"])

        assert result.exit_code == 0
        assert "no results" in result.stdout.lower()

    @pytest.mark.unit
    def test_exec_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """query exec should exit with error when Prometheus is not configured."""
        result = cli_runner.invoke(
            app_none_manager, ["query", "exec", "rate(kong_http_requests_total[5m])"]
        )

        assert result.exit_code == 1
        assert "prometheus" in result.stdout.lower() or "not configured" in result.stdout.lower()

    @pytest.mark.unit
    def test_exec_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query exec should display error message and exit 1 on ObservabilityClientError."""
        mock_metrics_manager.query_range.side_effect = ObservabilityClientError(
            "Prometheus unavailable", status_code=503
        )

        result = cli_runner.invoke(app, ["query", "exec", "rate(kong_http_requests_total[5m])"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_exec_error_with_status_code(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query exec error handler should display status code when present."""
        mock_metrics_manager.query_range.side_effect = ObservabilityClientError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(app, ["query", "exec", "rate(kong_http_requests_total[5m])"])

        assert result.exit_code == 1
        assert "500" in result.stdout

    @pytest.mark.unit
    def test_exec_more_than_20_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query exec should truncate output and show 'more' hint for >20 results."""
        mock_metrics_manager.query_range.return_value = [
            {
                "metric": {"service": f"api-{i}"},
                "values": [["1700000000", str(i * 10)]],
            }
            for i in range(25)
        ]

        result = cli_runner.invoke(app, ["query", "exec", "rate(kong_http_requests_total[5m])"])

        assert result.exit_code == 0
        assert "more" in result.stdout.lower() or "5 more" in result.stdout.lower()


class TestMetricsQueryRate(TestMetricsCommands):
    """Tests for 'query rate' sub-command."""

    @pytest.mark.unit
    def test_rate_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query rate should call get_request_rate and display results."""
        result = cli_runner.invoke(app, ["query", "rate"])

        assert result.exit_code == 0
        mock_metrics_manager.get_request_rate.assert_called_once()

    @pytest.mark.unit
    def test_rate_displays_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """query rate should render table rows with rate value."""
        result = cli_runner.invoke(app, ["query", "rate"])

        assert result.exit_code == 0
        # Rate value 12.34 should appear formatted
        assert "12.34" in result.stdout

    @pytest.mark.unit
    def test_rate_with_service_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query rate --service should forward service to the manager call."""
        result = cli_runner.invoke(app, ["query", "rate", "--service", "my-api"])

        assert result.exit_code == 0
        mock_metrics_manager.get_request_rate.assert_called_once_with(
            service="my-api", route=None, time_range="5m"
        )

    @pytest.mark.unit
    def test_rate_with_route_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query rate --route should forward route to the manager call."""
        result = cli_runner.invoke(app, ["query", "rate", "--route", "my-route"])

        assert result.exit_code == 0
        mock_metrics_manager.get_request_rate.assert_called_once_with(
            service=None, route="my-route", time_range="5m"
        )

    @pytest.mark.unit
    def test_rate_no_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query rate should show message when no data returned."""
        mock_metrics_manager.get_request_rate.return_value = []

        result = cli_runner.invoke(app, ["query", "rate"])

        assert result.exit_code == 0
        assert "no request rate" in result.stdout.lower()

    @pytest.mark.unit
    def test_rate_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """query rate should exit 1 when Prometheus is not configured."""
        result = cli_runner.invoke(app_none_manager, ["query", "rate"])

        assert result.exit_code == 1
        assert "prometheus" in result.stdout.lower() or "not configured" in result.stdout.lower()

    @pytest.mark.unit
    def test_rate_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query rate should delegate to formatter for non-table output."""
        result = cli_runner.invoke(app, ["query", "rate", "--output", "json"])

        assert result.exit_code == 0
        mock_metrics_manager.get_request_rate.assert_called_once()

    @pytest.mark.unit
    def test_rate_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query rate should exit 1 and print error on ObservabilityClientError."""
        mock_metrics_manager.get_request_rate.side_effect = ObservabilityClientError(
            "Connection refused"
        )

        result = cli_runner.invoke(app, ["query", "rate"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestMetricsQueryLatency(TestMetricsCommands):
    """Tests for 'query latency' sub-command."""

    @pytest.mark.unit
    def test_latency_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query latency should call get_latency_percentiles and display results."""
        result = cli_runner.invoke(app, ["query", "latency"])

        assert result.exit_code == 0
        mock_metrics_manager.get_latency_percentiles.assert_called_once()

    @pytest.mark.unit
    def test_latency_displays_percentiles(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """query latency should show p50 / p90 / p99 rows in table."""
        result = cli_runner.invoke(app, ["query", "latency"])

        assert result.exit_code == 0
        # At least one percentile label should be present
        assert "p50" in result.stdout or "p90" in result.stdout or "p99" in result.stdout

    @pytest.mark.unit
    def test_latency_with_service_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query latency --service should forward filter to manager."""
        result = cli_runner.invoke(app, ["query", "latency", "--service", "my-api"])

        assert result.exit_code == 0
        mock_metrics_manager.get_latency_percentiles.assert_called_once_with(
            service="my-api", time_range="5m"
        )

    @pytest.mark.unit
    def test_latency_no_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query latency should show message when all results are empty."""
        mock_metrics_manager.get_latency_percentiles.return_value = {}

        result = cli_runner.invoke(app, ["query", "latency"])

        assert result.exit_code == 0
        assert "no latency" in result.stdout.lower()

    @pytest.mark.unit
    def test_latency_all_empty_values(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query latency with empty lists for all percentiles should show no data message."""
        mock_metrics_manager.get_latency_percentiles.return_value = {
            0.5: [],
            0.9: [],
            0.99: [],
        }

        result = cli_runner.invoke(app, ["query", "latency"])

        assert result.exit_code == 0
        assert "no latency" in result.stdout.lower()

    @pytest.mark.unit
    def test_latency_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """query latency should exit 1 when Prometheus is not configured."""
        result = cli_runner.invoke(app_none_manager, ["query", "latency"])

        assert result.exit_code == 1
        assert "prometheus" in result.stdout.lower() or "not configured" in result.stdout.lower()

    @pytest.mark.unit
    def test_latency_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query latency --output json should use formatter."""
        result = cli_runner.invoke(app, ["query", "latency", "--output", "json"])

        assert result.exit_code == 0
        mock_metrics_manager.get_latency_percentiles.assert_called_once()

    @pytest.mark.unit
    def test_latency_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query latency should exit 1 on ObservabilityClientError."""
        mock_metrics_manager.get_latency_percentiles.side_effect = ObservabilityClientError(
            "Prometheus timeout", status_code=408
        )

        result = cli_runner.invoke(app, ["query", "latency"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestMetricsQueryErrors(TestMetricsCommands):
    """Tests for 'query errors' sub-command."""

    @pytest.mark.unit
    def test_errors_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query errors should call get_error_rate and display results."""
        result = cli_runner.invoke(app, ["query", "errors"])

        assert result.exit_code == 0
        mock_metrics_manager.get_error_rate.assert_called_once()

    @pytest.mark.unit
    def test_errors_displays_panel(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """query errors should render an error-rate panel."""
        result = cli_runner.invoke(app, ["query", "errors"])

        assert result.exit_code == 0
        # 0.005 * 100 = 0.50%
        assert "0.50" in result.stdout

    @pytest.mark.unit
    def test_errors_with_service_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query errors --service should forward filter to manager."""
        result = cli_runner.invoke(app, ["query", "errors", "--service", "my-api"])

        assert result.exit_code == 0
        mock_metrics_manager.get_error_rate.assert_called_once_with(
            service="my-api", time_range="5m"
        )

    @pytest.mark.unit
    def test_errors_no_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query errors should show message when no data returned."""
        mock_metrics_manager.get_error_rate.return_value = []

        result = cli_runner.invoke(app, ["query", "errors"])

        assert result.exit_code == 0
        assert "no error rate" in result.stdout.lower()

    @pytest.mark.unit
    def test_errors_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """query errors should exit 1 when Prometheus is not configured."""
        result = cli_runner.invoke(app_none_manager, ["query", "errors"])

        assert result.exit_code == 1
        assert "prometheus" in result.stdout.lower() or "not configured" in result.stdout.lower()

    @pytest.mark.unit
    def test_errors_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query errors --output json should use formatter."""
        result = cli_runner.invoke(app, ["query", "errors", "--output", "json"])

        assert result.exit_code == 0
        mock_metrics_manager.get_error_rate.assert_called_once()

    @pytest.mark.unit
    def test_errors_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query errors should exit 1 on ObservabilityClientError."""
        mock_metrics_manager.get_error_rate.side_effect = ObservabilityClientError("Backend error")

        result = cli_runner.invoke(app, ["query", "errors"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_errors_high_error_rate_shows_red(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query errors should colour the panel red when error rate >= 5%."""
        # 0.10 * 100 = 10%, should trigger red
        mock_metrics_manager.get_error_rate.return_value = [{"value": ["1700000000", "0.10"]}]

        result = cli_runner.invoke(app, ["query", "errors"])

        assert result.exit_code == 0
        assert "10.00" in result.stdout


class TestMetricsQuerySummary(TestMetricsCommands):
    """Tests for 'query summary' sub-command."""

    @pytest.mark.unit
    def test_summary_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query summary should call get_summary and display a table."""
        result = cli_runner.invoke(app, ["query", "summary"])

        assert result.exit_code == 0
        mock_metrics_manager.get_summary.assert_called_once()

    @pytest.mark.unit
    def test_summary_displays_request_rate(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """query summary table should contain Request Rate row."""
        result = cli_runner.invoke(app, ["query", "summary"])

        assert result.exit_code == 0
        assert "42.00" in result.stdout

    @pytest.mark.unit
    def test_summary_displays_latency(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """query summary table should contain latency rows from summary dict."""
        result = cli_runner.invoke(app, ["query", "summary"])

        assert result.exit_code == 0
        assert "p50" in result.stdout or "25.5" in result.stdout

    @pytest.mark.unit
    def test_summary_with_service_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query summary --service should forward filter to manager."""
        result = cli_runner.invoke(app, ["query", "summary", "--service", "my-api"])

        assert result.exit_code == 0
        mock_metrics_manager.get_summary.assert_called_once_with(service="my-api", time_range="5m")

    @pytest.mark.unit
    def test_summary_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """query summary should exit 1 when Prometheus is not configured."""
        result = cli_runner.invoke(app_none_manager, ["query", "summary"])

        assert result.exit_code == 1
        assert "prometheus" in result.stdout.lower() or "not configured" in result.stdout.lower()

    @pytest.mark.unit
    def test_summary_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query summary --output json should use formatter."""
        result = cli_runner.invoke(app, ["query", "summary", "--output", "json"])

        assert result.exit_code == 0
        mock_metrics_manager.get_summary.assert_called_once()

    @pytest.mark.unit
    def test_summary_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query summary should exit 1 on ObservabilityClientError."""
        mock_metrics_manager.get_summary.side_effect = ObservabilityClientError(
            "Query failed", status_code=422
        )

        result = cli_runner.invoke(app, ["query", "summary"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_summary_no_latency_section(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_metrics_manager: MagicMock,
    ) -> None:
        """query summary table should not include latency rows when absent."""
        mock_metrics_manager.get_summary.return_value = {
            "request_rate_per_second": 10.0,
            "error_rate": 0.0,
        }

        result = cli_runner.invoke(app, ["query", "summary"])

        assert result.exit_code == 0
        assert "10.00" in result.stdout


# =============================================================================
# Logs command tests
# =============================================================================


class TestLogsCommands:
    """Tests for external Elasticsearch/Loki log search commands."""

    @pytest.fixture
    def mock_logs_manager(self) -> MagicMock:
        """Create a mock LogsManager."""
        manager = MagicMock()
        manager.search_logs.return_value = [
            {
                "@timestamp": "2024-01-01T12:00:00Z",
                "service": {"name": "api-1"},
                "response": {"status": 200},
                "latencies": {"request": 45},
                "request": {"uri": "/v1/resource"},
            }
        ]
        manager.get_error_logs.return_value = [
            {
                "@timestamp": "2024-01-01T12:01:00Z",
                "service": {"name": "api-1"},
                "response": {"status": 500},
                "request": {"uri": "/v1/broken"},
                "error": "Internal Server Error",
            }
        ]
        manager.get_summary.return_value = {
            "backend": "elasticsearch",
            "total_logs": 5000,
            "error_count": 42,
            "status_distribution": {200: 4900, 404: 58, 500: 42},
        }
        return manager

    @pytest.fixture
    def app(self, mock_logs_manager: MagicMock) -> typer.Typer:
        """Create a test app with external logs commands."""
        app = typer.Typer()
        register_external_logs_commands(app, lambda: mock_logs_manager)
        return app

    @pytest.fixture
    def app_none_manager(self) -> typer.Typer:
        """Create a test app whose logs manager returns None."""
        app = typer.Typer()
        register_external_logs_commands(app, lambda: None)
        return app


class TestLogsSearchQuery(TestLogsCommands):
    """Tests for 'search query' sub-command."""

    @pytest.mark.unit
    def test_search_query_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query should call search_logs and display results."""
        result = cli_runner.invoke(app, ["search", "query", "error"])

        assert result.exit_code == 0
        mock_logs_manager.search_logs.assert_called_once()

    @pytest.mark.unit
    def test_search_query_displays_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """search query should render a table with log entries."""
        result = cli_runner.invoke(app, ["search", "query", "error"])

        assert result.exit_code == 0
        assert "api-1" in result.stdout or "/v1/resource" in result.stdout

    @pytest.mark.unit
    def test_search_query_no_positional_arg(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query should work without positional query argument."""
        result = cli_runner.invoke(app, ["search", "query"])

        assert result.exit_code == 0
        mock_logs_manager.search_logs.assert_called_once()

    @pytest.mark.unit
    def test_search_query_with_service_and_status(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query should forward --service and --status options."""
        result = cli_runner.invoke(
            app,
            ["search", "query", "--service", "my-api", "--status", "500"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_logs_manager.search_logs.call_args[1]
        assert call_kwargs["service"] == "my-api"
        assert call_kwargs["status_code"] == 500

    @pytest.mark.unit
    def test_search_query_no_logs(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query should show message when no logs found."""
        mock_logs_manager.search_logs.return_value = []

        result = cli_runner.invoke(app, ["search", "query"])

        assert result.exit_code == 0
        assert "no logs" in result.stdout.lower()

    @pytest.mark.unit
    def test_search_query_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """search query should exit 1 when log backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["search", "query"])

        assert result.exit_code == 1
        assert (
            "elasticsearch" in result.stdout.lower()
            or "loki" in result.stdout.lower()
            or "not configured" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_search_query_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query --output json should delegate to formatter."""
        result = cli_runner.invoke(app, ["search", "query", "--output", "json"])

        assert result.exit_code == 0
        mock_logs_manager.search_logs.assert_called_once()

    @pytest.mark.unit
    def test_search_query_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query should exit 1 on ObservabilityClientError."""
        mock_logs_manager.search_logs.side_effect = ObservabilityClientError(
            "Elasticsearch down", status_code=503
        )

        result = cli_runner.invoke(app, ["search", "query"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_search_query_timestamp_formatting(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query should extract HH:MM:SS from ISO timestamp strings."""
        mock_logs_manager.search_logs.return_value = [
            {
                "@timestamp": "2024-01-01T15:30:45.123Z",
                "service": "flat-service-name",
                "response": {"status": 200},
                "latencies": {"request": 10},
                "request": {"uri": "/ping"},
            }
        ]

        result = cli_runner.invoke(app, ["search", "query"])

        assert result.exit_code == 0
        # HH:MM:SS slice: "15:30:45"
        assert "15:30:45" in result.stdout

    @pytest.mark.unit
    def test_search_query_flat_service_name(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query should handle service as plain string (not dict)."""
        mock_logs_manager.search_logs.return_value = [
            {
                "@timestamp": "-",
                "service": "plain-service",
                "response": {"status": 201},
                "latencies": {"request": 5},
                "request": {"uri": "/ok"},
            }
        ]

        result = cli_runner.invoke(app, ["search", "query"])

        assert result.exit_code == 0
        assert "plain-service" in result.stdout

    @pytest.mark.unit
    def test_search_query_datetime_timestamp(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search query should format datetime objects in the timestamp column."""
        from datetime import datetime

        ts = datetime(2024, 1, 1, 10, 20, 30)
        mock_logs_manager.search_logs.return_value = [
            {
                "@timestamp": ts,
                "service": {"name": "svc"},
                "response": {"status": 200},
                "latencies": {"request": 3},
                "request": {"uri": "/dt"},
            }
        ]

        result = cli_runner.invoke(app, ["search", "query"])

        assert result.exit_code == 0
        assert "10:20:30" in result.stdout


class TestLogsSearchErrors(TestLogsCommands):
    """Tests for 'search errors' sub-command."""

    @pytest.mark.unit
    def test_search_errors_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search errors should call get_error_logs and display results."""
        result = cli_runner.invoke(app, ["search", "errors"])

        assert result.exit_code == 0
        mock_logs_manager.get_error_logs.assert_called_once()

    @pytest.mark.unit
    def test_search_errors_displays_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """search errors should render a table with error log entries."""
        result = cli_runner.invoke(app, ["search", "errors"])

        assert result.exit_code == 0
        assert "api-1" in result.stdout or "/v1/broken" in result.stdout

    @pytest.mark.unit
    def test_search_errors_no_errors(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search errors should show green message when no error logs found."""
        mock_logs_manager.get_error_logs.return_value = []

        result = cli_runner.invoke(app, ["search", "errors"])

        assert result.exit_code == 0
        assert "no error" in result.stdout.lower()

    @pytest.mark.unit
    def test_search_errors_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """search errors should exit 1 when log backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["search", "errors"])

        assert result.exit_code == 1
        assert "log backend" in result.stdout.lower() or "not configured" in result.stdout.lower()

    @pytest.mark.unit
    def test_search_errors_with_service_and_range(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search errors should forward --service and --range options."""
        result = cli_runner.invoke(
            app, ["search", "errors", "--service", "bad-svc", "--range", "1d"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_logs_manager.get_error_logs.call_args[1]
        assert call_kwargs["service"] == "bad-svc"

    @pytest.mark.unit
    def test_search_errors_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search errors --output json should delegate to formatter."""
        result = cli_runner.invoke(app, ["search", "errors", "--output", "json"])

        assert result.exit_code == 0
        mock_logs_manager.get_error_logs.assert_called_once()

    @pytest.mark.unit
    def test_search_errors_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search errors should exit 1 on ObservabilityClientError."""
        mock_logs_manager.get_error_logs.side_effect = ObservabilityClientError(
            "Loki unavailable", status_code=502
        )

        result = cli_runner.invoke(app, ["search", "errors"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_search_errors_datetime_timestamp(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search errors should format datetime objects in timestamp column."""
        from datetime import datetime

        ts = datetime(2024, 6, 15, 9, 5, 3)
        mock_logs_manager.get_error_logs.return_value = [
            {
                "@timestamp": ts,
                "service": {"name": "svc"},
                "response": {"status": 500},
                "request": {"uri": "/err"},
                "error": "boom",
            }
        ]

        result = cli_runner.invoke(app, ["search", "errors"])

        assert result.exit_code == 0
        assert "09:05:03" in result.stdout


class TestLogsSearchSummary(TestLogsCommands):
    """Tests for 'search summary' sub-command."""

    @pytest.mark.unit
    def test_search_summary_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search summary should call get_summary and display results."""
        result = cli_runner.invoke(app, ["search", "summary"])

        assert result.exit_code == 0
        mock_logs_manager.get_summary.assert_called_once()

    @pytest.mark.unit
    def test_search_summary_displays_backend(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """search summary should show backend name and totals."""
        result = cli_runner.invoke(app, ["search", "summary"])

        assert result.exit_code == 0
        assert "elasticsearch" in result.stdout.lower()

    @pytest.mark.unit
    def test_search_summary_displays_status_distribution(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """search summary should render a second table with status codes."""
        result = cli_runner.invoke(app, ["search", "summary"])

        assert result.exit_code == 0
        # Status codes 200, 404, 500 should appear
        assert "200" in result.stdout

    @pytest.mark.unit
    def test_search_summary_no_status_distribution(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search summary should skip status table when distribution is empty."""
        mock_logs_manager.get_summary.return_value = {
            "backend": "loki",
            "total_logs": 100,
            "error_count": 0,
            "status_distribution": {},
        }

        result = cli_runner.invoke(app, ["search", "summary"])

        assert result.exit_code == 0
        assert "loki" in result.stdout.lower()

    @pytest.mark.unit
    def test_search_summary_with_service_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search summary --service should forward filter to manager."""
        result = cli_runner.invoke(app, ["search", "summary", "--service", "my-api"])

        assert result.exit_code == 0
        call_kwargs = mock_logs_manager.get_summary.call_args[1]
        assert call_kwargs["service"] == "my-api"

    @pytest.mark.unit
    def test_search_summary_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """search summary should exit 1 when log backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["search", "summary"])

        assert result.exit_code == 1
        assert "log backend" in result.stdout.lower() or "not configured" in result.stdout.lower()

    @pytest.mark.unit
    def test_search_summary_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search summary --output json should delegate to formatter."""
        result = cli_runner.invoke(app, ["search", "summary", "--output", "json"])

        assert result.exit_code == 0
        mock_logs_manager.get_summary.assert_called_once()

    @pytest.mark.unit
    def test_search_summary_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_logs_manager: MagicMock,
    ) -> None:
        """search summary should exit 1 on ObservabilityClientError."""
        mock_logs_manager.get_summary.side_effect = ObservabilityClientError("Backend offline")

        result = cli_runner.invoke(app, ["search", "summary"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


# =============================================================================
# Tracing command tests
# =============================================================================


class TestTracingCommands:
    """Tests for external Jaeger/Zipkin tracing commands."""

    @pytest.fixture
    def mock_tracing_manager(self) -> MagicMock:
        """Create a mock TracingManager."""
        manager = MagicMock()
        manager.find_traces.return_value = [
            {
                "traceID": "abc123def456xyz789",
                "spans": [
                    {"duration": 5000, "processID": "p1"},
                    {"duration": 2000, "processID": "p2"},
                ],
                "processes": {
                    "p1": {"serviceName": "gateway"},
                    "p2": {"serviceName": "api-1"},
                },
            }
        ]
        manager.get_trace.return_value = {
            "traceID": "abc123def456xyz789",
            "spans": [
                {
                    "operationName": "GET /v1/resource",
                    "processID": "p1",
                    "duration": 5000,
                    "startTime": 1700000000000,
                },
                {
                    "operationName": "query-db",
                    "processID": "p2",
                    "duration": 2000,
                    "startTime": 1700000001000,
                },
            ],
            "processes": {
                "p1": {"serviceName": "gateway"},
                "p2": {"serviceName": "api-1"},
            },
        }
        manager.get_slow_traces.return_value = [
            {
                "traceID": "slowtrace12345678",
                "spans": [{"duration": 900000}],
                "processes": {},
            }
        ]
        manager.get_error_traces.return_value = [
            {
                "traceID": "errtrace12345678",
                "spans": [
                    {
                        "duration": 3000,
                        "tags": [{"key": "error", "value": True}],
                    }
                ],
                "processes": {},
            }
        ]
        manager.analyze_trace.return_value = {
            "trace_id": "abc123def456xyz789",
            "total_duration_us": 5000,
            "span_count": 2,
            "slowest_span": {
                "operation": "GET /v1/resource",
                "duration_us": 5000,
            },
            "service_breakdown": {
                "gateway": 5000,
                "api-1": 2000,
            },
        }
        manager.get_summary.return_value = {
            "backend": "jaeger",
            "service_name": "kong",
            "trace_count": 100,
            "error_trace_count": 5,
            "duration_stats": {
                "min_us": 500,
                "max_us": 900000,
                "avg_us": 50000,
                "p50_us": 30000,
                "p99_us": 800000,
            },
            "services": ["gateway", "api-1", "api-2"],
        }
        return manager

    @pytest.fixture
    def app(self, mock_tracing_manager: MagicMock) -> typer.Typer:
        """Create a test app with external tracing commands."""
        app = typer.Typer()
        register_external_tracing_commands(app, lambda: mock_tracing_manager)
        return app

    @pytest.fixture
    def app_none_manager(self) -> typer.Typer:
        """Create a test app whose tracing manager returns None."""
        app = typer.Typer()
        register_external_tracing_commands(app, lambda: None)
        return app


class TestTracesFind(TestTracingCommands):
    """Tests for 'traces find' sub-command."""

    @pytest.mark.unit
    def test_find_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces find should call find_traces and display results."""
        result = cli_runner.invoke(app, ["traces", "find"])

        assert result.exit_code == 0
        mock_tracing_manager.find_traces.assert_called_once()

    @pytest.mark.unit
    def test_find_displays_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces find should render a table with trace rows."""
        result = cli_runner.invoke(app, ["traces", "find"])

        assert result.exit_code == 0
        # Trace ID truncated to 16 chars: "abc123def456xyz7"
        assert "abc123def456xyz7" in result.stdout

    @pytest.mark.unit
    def test_find_with_route_filter(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces find --route should forward filter to find_traces."""
        result = cli_runner.invoke(app, ["traces", "find", "--route", "my-route"])

        assert result.exit_code == 0
        call_kwargs = mock_tracing_manager.find_traces.call_args[1]
        assert call_kwargs["route"] == "my-route"

    @pytest.mark.unit
    def test_find_with_min_duration(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces find --min-duration should forward threshold to find_traces."""
        result = cli_runner.invoke(app, ["traces", "find", "--min-duration", "500"])

        assert result.exit_code == 0
        call_kwargs = mock_tracing_manager.find_traces.call_args[1]
        assert call_kwargs["min_duration_ms"] == 500

    @pytest.mark.unit
    def test_find_no_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces find should show 'No traces' message when list is empty."""
        mock_tracing_manager.find_traces.return_value = []

        result = cli_runner.invoke(app, ["traces", "find"])

        assert result.exit_code == 0
        assert "no traces" in result.stdout.lower()

    @pytest.mark.unit
    def test_find_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """traces find should exit 1 when tracing backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["traces", "find"])

        assert result.exit_code == 1
        assert (
            "jaeger" in result.stdout.lower()
            or "zipkin" in result.stdout.lower()
            or "not configured" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_find_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces find --output json should delegate to formatter."""
        result = cli_runner.invoke(app, ["traces", "find", "--output", "json"])

        assert result.exit_code == 0
        mock_tracing_manager.find_traces.assert_called_once()

    @pytest.mark.unit
    def test_find_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces find should exit 1 on ObservabilityClientError."""
        mock_tracing_manager.find_traces.side_effect = ObservabilityClientError(
            "Jaeger unavailable", status_code=503
        )

        result = cli_runner.invoke(app, ["traces", "find"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_find_duration_conversion(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces find should convert microseconds > 1000 to milliseconds."""
        # span duration 5000 us / 1000 = 5.0 ms
        result = cli_runner.invoke(app, ["traces", "find"])

        assert result.exit_code == 0
        assert "5.0ms" in result.stdout


class TestTracesGet(TestTracingCommands):
    """Tests for 'traces get' sub-command."""

    @pytest.mark.unit
    def test_get_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces get should call get_trace and display span table."""
        result = cli_runner.invoke(app, ["traces", "get", "abc123def456xyz789"])

        assert result.exit_code == 0
        mock_tracing_manager.get_trace.assert_called_once_with("abc123def456xyz789")

    @pytest.mark.unit
    def test_get_displays_trace_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces get should print the Trace ID header."""
        result = cli_runner.invoke(app, ["traces", "get", "abc123def456xyz789"])

        assert result.exit_code == 0
        assert "abc123def456xyz789" in result.stdout

    @pytest.mark.unit
    def test_get_displays_spans(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces get should list operation names from spans."""
        result = cli_runner.invoke(app, ["traces", "get", "abc123def456xyz789"])

        assert result.exit_code == 0
        assert "GET /v1/resource" in result.stdout or "query-db" in result.stdout

    @pytest.mark.unit
    def test_get_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """traces get should exit 1 when tracing backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["traces", "get", "someid"])

        assert result.exit_code == 1
        assert (
            "tracing backend" in result.stdout.lower() or "not configured" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_get_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces get --output json should delegate to formatter."""
        result = cli_runner.invoke(app, ["traces", "get", "abc123def456xyz789", "--output", "json"])

        assert result.exit_code == 0
        mock_tracing_manager.get_trace.assert_called_once()

    @pytest.mark.unit
    def test_get_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces get should exit 1 on ObservabilityClientError."""
        mock_tracing_manager.get_trace.side_effect = ObservabilityClientError(
            "Trace not found", status_code=404
        )

        result = cli_runner.invoke(app, ["traces", "get", "missing-id"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_get_duration_conversion(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces get should convert span duration > 1000 us to ms in table."""
        # span duration 5000 us → 5000 / 1000 = 5.0 ms → displayed as "5.00ms"
        result = cli_runner.invoke(app, ["traces", "get", "abc123def456xyz789"])

        assert result.exit_code == 0
        assert "5.00ms" in result.stdout


class TestTracesSlow(TestTracingCommands):
    """Tests for 'traces slow' sub-command."""

    @pytest.mark.unit
    def test_slow_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces slow should call get_slow_traces and display results."""
        result = cli_runner.invoke(app, ["traces", "slow"])

        assert result.exit_code == 0
        mock_tracing_manager.get_slow_traces.assert_called_once()

    @pytest.mark.unit
    def test_slow_displays_trace_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces slow should render a table with truncated trace IDs."""
        result = cli_runner.invoke(app, ["traces", "slow"])

        assert result.exit_code == 0
        assert "slowtrace1234567" in result.stdout

    @pytest.mark.unit
    def test_slow_custom_threshold(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces slow --threshold should forward value to get_slow_traces."""
        result = cli_runner.invoke(app, ["traces", "slow", "--threshold", "1000"])

        assert result.exit_code == 0
        call_kwargs = mock_tracing_manager.get_slow_traces.call_args[1]
        assert call_kwargs["threshold_ms"] == 1000

    @pytest.mark.unit
    def test_slow_no_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces slow should show success message when no slow traces found."""
        mock_tracing_manager.get_slow_traces.return_value = []

        result = cli_runner.invoke(app, ["traces", "slow", "--threshold", "500"])

        assert result.exit_code == 0
        assert "no traces slower than 500ms" in result.stdout.lower()

    @pytest.mark.unit
    def test_slow_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """traces slow should exit 1 when tracing backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["traces", "slow"])

        assert result.exit_code == 1
        assert (
            "tracing backend" in result.stdout.lower() or "not configured" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_slow_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces slow --output json should delegate to formatter."""
        result = cli_runner.invoke(app, ["traces", "slow", "--output", "json"])

        assert result.exit_code == 0
        mock_tracing_manager.get_slow_traces.assert_called_once()

    @pytest.mark.unit
    def test_slow_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces slow should exit 1 on ObservabilityClientError."""
        mock_tracing_manager.get_slow_traces.side_effect = ObservabilityClientError(
            "Jaeger query failed", status_code=500
        )

        result = cli_runner.invoke(app, ["traces", "slow"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestTracesErrors(TestTracingCommands):
    """Tests for 'traces errors' sub-command."""

    @pytest.mark.unit
    def test_errors_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces errors should call get_error_traces and display results."""
        result = cli_runner.invoke(app, ["traces", "errors"])

        assert result.exit_code == 0
        mock_tracing_manager.get_error_traces.assert_called_once()

    @pytest.mark.unit
    def test_errors_displays_table(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces errors should render a table with error trace rows."""
        result = cli_runner.invoke(app, ["traces", "errors"])

        assert result.exit_code == 0
        assert "errtrace1234567" in result.stdout

    @pytest.mark.unit
    def test_errors_no_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces errors should show green message when no error traces found."""
        mock_tracing_manager.get_error_traces.return_value = []

        result = cli_runner.invoke(app, ["traces", "errors"])

        assert result.exit_code == 0
        assert "no error traces" in result.stdout.lower()

    @pytest.mark.unit
    def test_errors_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """traces errors should exit 1 when tracing backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["traces", "errors"])

        assert result.exit_code == 1
        assert (
            "tracing backend" in result.stdout.lower() or "not configured" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_errors_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces errors --output json should delegate to formatter."""
        result = cli_runner.invoke(app, ["traces", "errors", "--output", "json"])

        assert result.exit_code == 0
        mock_tracing_manager.get_error_traces.assert_called_once()

    @pytest.mark.unit
    def test_errors_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces errors should exit 1 on ObservabilityClientError."""
        mock_tracing_manager.get_error_traces.side_effect = ObservabilityClientError(
            "Tracing backend error"
        )

        result = cli_runner.invoke(app, ["traces", "errors"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()

    @pytest.mark.unit
    def test_errors_counts_error_spans(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces errors table should count spans with error tag set to true."""
        mock_tracing_manager.get_error_traces.return_value = [
            {
                "traceID": "errtrace12345678",
                "spans": [
                    {"duration": 1000, "tags": [{"key": "error", "value": True}]},
                    {"duration": 500, "tags": [{"key": "error", "value": False}]},
                    {"duration": 200, "tags": []},
                ],
                "processes": {},
            }
        ]

        result = cli_runner.invoke(app, ["traces", "errors"])

        assert result.exit_code == 0
        # Only 1 span has error=True, so "1" should appear in the Error Spans column
        assert "1" in result.stdout


class TestTracesAnalyze(TestTracingCommands):
    """Tests for 'traces analyze' sub-command."""

    @pytest.mark.unit
    def test_analyze_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces analyze should call analyze_trace and display summary table."""
        result = cli_runner.invoke(app, ["traces", "analyze", "abc123def456xyz789"])

        assert result.exit_code == 0
        mock_tracing_manager.analyze_trace.assert_called_once_with("abc123def456xyz789")

    @pytest.mark.unit
    def test_analyze_displays_duration(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces analyze should show total duration in the summary table."""
        result = cli_runner.invoke(app, ["traces", "analyze", "abc123def456xyz789"])

        assert result.exit_code == 0
        # total_duration_us=5000 → 5000/1000 = 5.0 ms
        assert "5.00ms" in result.stdout

    @pytest.mark.unit
    def test_analyze_displays_service_breakdown(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces analyze should render service breakdown table."""
        result = cli_runner.invoke(app, ["traces", "analyze", "abc123def456xyz789"])

        assert result.exit_code == 0
        assert "gateway" in result.stdout or "api-1" in result.stdout

    @pytest.mark.unit
    def test_analyze_no_service_breakdown(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces analyze should skip service breakdown table when absent."""
        mock_tracing_manager.analyze_trace.return_value = {
            "trace_id": "abc123",
            "total_duration_us": 1000,
            "span_count": 1,
        }

        result = cli_runner.invoke(app, ["traces", "analyze", "abc123"])

        assert result.exit_code == 0
        # Should still succeed with just summary table
        assert "1.00ms" in result.stdout

    @pytest.mark.unit
    def test_analyze_slowest_span_with_name_fallback(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces analyze should fall back to 'name' key for slowest span operation."""
        mock_tracing_manager.analyze_trace.return_value = {
            "trace_id": "abc123",
            "total_duration_us": 2000,
            "span_count": 1,
            "slowest_span": {"name": "my-operation", "duration_us": 2000},
            "service_breakdown": {},
        }

        result = cli_runner.invoke(app, ["traces", "analyze", "abc123"])

        assert result.exit_code == 0
        assert "my-operation" in result.stdout

    @pytest.mark.unit
    def test_analyze_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """traces analyze should exit 1 when tracing backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["traces", "analyze", "someid"])

        assert result.exit_code == 1
        assert (
            "tracing backend" in result.stdout.lower() or "not configured" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_analyze_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces analyze --output json should delegate to formatter."""
        result = cli_runner.invoke(
            app, ["traces", "analyze", "abc123def456xyz789", "--output", "json"]
        )

        assert result.exit_code == 0
        mock_tracing_manager.analyze_trace.assert_called_once()

    @pytest.mark.unit
    def test_analyze_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces analyze should exit 1 on ObservabilityClientError."""
        mock_tracing_manager.analyze_trace.side_effect = ObservabilityClientError(
            "Analysis failed", status_code=500
        )

        result = cli_runner.invoke(app, ["traces", "analyze", "abc123def456xyz789"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestTracesSummary(TestTracingCommands):
    """Tests for 'traces summary' sub-command."""

    @pytest.mark.unit
    def test_summary_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces summary should call get_summary and display results."""
        result = cli_runner.invoke(app, ["traces", "summary"])

        assert result.exit_code == 0
        mock_tracing_manager.get_summary.assert_called_once()

    @pytest.mark.unit
    def test_summary_displays_backend(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces summary should show backend and service name."""
        result = cli_runner.invoke(app, ["traces", "summary"])

        assert result.exit_code == 0
        assert "jaeger" in result.stdout.lower()

    @pytest.mark.unit
    def test_summary_displays_duration_stats(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces summary should render duration stats rows when present."""
        result = cli_runner.invoke(app, ["traces", "summary"])

        assert result.exit_code == 0
        # min_us=500 → 500/1000 = 0.50ms
        assert "0.50ms" in result.stdout or "Min Duration" in result.stdout

    @pytest.mark.unit
    def test_summary_no_duration_stats(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces summary should skip duration stats when not present."""
        mock_tracing_manager.get_summary.return_value = {
            "backend": "zipkin",
            "service_name": "svc",
            "trace_count": 10,
            "error_trace_count": 0,
        }

        result = cli_runner.invoke(app, ["traces", "summary"])

        assert result.exit_code == 0
        assert "zipkin" in result.stdout.lower()

    @pytest.mark.unit
    def test_summary_displays_services(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """traces summary should list traced services."""
        result = cli_runner.invoke(app, ["traces", "summary"])

        assert result.exit_code == 0
        assert "gateway" in result.stdout or "api-1" in result.stdout

    @pytest.mark.unit
    def test_summary_no_services(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces summary should not error when services list is absent."""
        mock_tracing_manager.get_summary.return_value = {
            "backend": "jaeger",
            "service_name": "kong",
            "trace_count": 5,
            "error_trace_count": 0,
            "services": [],
        }

        result = cli_runner.invoke(app, ["traces", "summary"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_summary_with_custom_range(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces summary --range should use the custom time window."""
        result = cli_runner.invoke(app, ["traces", "summary", "--range", "1d"])

        assert result.exit_code == 0
        mock_tracing_manager.get_summary.assert_called_once()

    @pytest.mark.unit
    def test_summary_manager_none(
        self,
        cli_runner: CliRunner,
        app_none_manager: typer.Typer,
    ) -> None:
        """traces summary should exit 1 when tracing backend is not configured."""
        result = cli_runner.invoke(app_none_manager, ["traces", "summary"])

        assert result.exit_code == 1
        assert (
            "tracing backend" in result.stdout.lower() or "not configured" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_summary_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces summary --output json should delegate to formatter."""
        result = cli_runner.invoke(app, ["traces", "summary", "--output", "json"])

        assert result.exit_code == 0
        mock_tracing_manager.get_summary.assert_called_once()

    @pytest.mark.unit
    def test_summary_observability_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """traces summary should exit 1 on ObservabilityClientError."""
        mock_tracing_manager.get_summary.side_effect = ObservabilityClientError(
            "Jaeger unreachable"
        )

        result = cli_runner.invoke(app, ["traces", "summary"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
