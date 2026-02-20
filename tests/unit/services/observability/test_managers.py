"""Unit tests for observability service managers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.observability.config import (
    ElasticsearchConfig,
    JaegerConfig,
    LokiConfig,
    PrometheusConfig,
    ZipkinConfig,
)
from system_operations_manager.services.observability import (
    LogsManager,
    MetricsManager,
    TracingManager,
)


class TestMetricsManager:
    """Tests for MetricsManager."""

    @pytest.fixture
    def config(self) -> PrometheusConfig:
        """Create test config."""
        return PrometheusConfig(url="http://localhost:9090")

    @pytest.fixture
    def mock_prometheus_client(self, mocker: Any) -> MagicMock:
        """Create mock Prometheus client."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.integrations.observability.PrometheusClient",
            return_value=mock_client,
        )
        return mock_client

    @pytest.mark.unit
    def test_manager_initialization(self, config: PrometheusConfig) -> None:
        """Manager should initialize correctly."""
        manager = MetricsManager(config)

        assert manager.config == config

    @pytest.mark.unit
    def test_is_available(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """is_available should check backend health."""
        mock_prometheus_client.health_check.return_value = True

        manager = MetricsManager(config)

        assert manager.is_available() is True
        mock_prometheus_client.health_check.assert_called()

    @pytest.mark.unit
    def test_is_available_when_down(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """is_available should return False when backend is down."""
        mock_prometheus_client.health_check.return_value = False

        manager = MetricsManager(config)

        assert manager.is_available() is False

    @pytest.mark.unit
    def test_get_request_rate(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_request_rate should call client method."""
        mock_prometheus_client.get_kong_request_rate.return_value = [
            {"metric": {"service": "my-api"}, "value": [1234567890, "100"]},
        ]

        manager = MetricsManager(config)
        results = manager.get_request_rate(service="my-api")

        mock_prometheus_client.get_kong_request_rate.assert_called_with(
            service="my-api", route=None, time_range="5m"
        )
        assert len(results) == 1

    @pytest.mark.unit
    def test_get_latency_percentiles(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_latency_percentiles should call client method."""
        mock_prometheus_client.get_kong_latency_percentiles.return_value = {
            0.5: [{"value": [1234567890, "0.05"]}],
            0.9: [{"value": [1234567890, "0.1"]}],
        }

        manager = MetricsManager(config)
        results = manager.get_latency_percentiles()

        mock_prometheus_client.get_kong_latency_percentiles.assert_called()
        assert 0.5 in results
        assert 0.9 in results

    @pytest.mark.unit
    def test_get_error_rate(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_error_rate should call client method."""
        mock_prometheus_client.get_kong_error_rate.return_value = [
            {"value": [1234567890, "0.01"]},
        ]

        manager = MetricsManager(config)
        results = manager.get_error_rate()

        mock_prometheus_client.get_kong_error_rate.assert_called()
        assert len(results) == 1

    @pytest.mark.unit
    def test_get_summary(self, config: PrometheusConfig, mock_prometheus_client: MagicMock) -> None:
        """get_summary should aggregate metrics."""
        mock_prometheus_client.get_kong_request_rate.return_value = [
            {"value": [1234567890, "100"]},
        ]
        mock_prometheus_client.get_kong_error_rate.return_value = [
            {"value": [1234567890, "0.01"]},
        ]
        mock_prometheus_client.get_kong_latency_percentiles.return_value = {
            0.5: [{"value": [1234567890, "50"]}],
            0.9: [{"value": [1234567890, "100"]}],
            0.99: [{"value": [1234567890, "200"]}],
        }

        manager = MetricsManager(config)
        summary = manager.get_summary()

        assert "request_rate_per_second" in summary
        assert "error_rate" in summary
        assert "latency_ms" in summary

    @pytest.mark.unit
    def test_context_manager(self, config: PrometheusConfig) -> None:
        """Manager should work as context manager."""
        with MetricsManager(config) as manager:
            assert manager is not None
            # Close is called on exit


class TestLogsManager:
    """Tests for LogsManager."""

    @pytest.fixture
    def es_config(self) -> ElasticsearchConfig:
        """Create ES test config."""
        return ElasticsearchConfig(hosts=["http://localhost:9200"])

    @pytest.fixture
    def loki_config(self) -> LokiConfig:
        """Create Loki test config."""
        return LokiConfig(url="http://localhost:3100")

    @pytest.fixture
    def mock_es_client(self, mocker: Any) -> MagicMock:
        """Create mock Elasticsearch client."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.integrations.observability.ElasticsearchClient",
            return_value=mock_client,
        )
        return mock_client

    @pytest.fixture
    def mock_loki_client(self, mocker: Any) -> MagicMock:
        """Create mock Loki client."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.integrations.observability.LokiClient",
            return_value=mock_client,
        )
        return mock_client

    @pytest.mark.unit
    def test_manager_initialization_with_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """Manager should initialize with Elasticsearch."""
        manager = LogsManager(elasticsearch_config=es_config)

        assert manager.backend == "elasticsearch"

    @pytest.mark.unit
    def test_manager_initialization_with_loki(
        self, loki_config: LokiConfig, mock_loki_client: MagicMock
    ) -> None:
        """Manager should initialize with Loki."""
        manager = LogsManager(loki_config=loki_config)

        assert manager.backend == "loki"

    @pytest.mark.unit
    def test_manager_requires_backend(self) -> None:
        """Manager should require at least one backend."""
        with pytest.raises(ValueError, match="At least one logs backend"):
            LogsManager()

    @pytest.mark.unit
    def test_is_available_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """is_available should check ES health."""
        mock_es_client.health_check.return_value = True

        manager = LogsManager(elasticsearch_config=es_config)

        assert manager.is_available() is True

    @pytest.mark.unit
    def test_is_available_loki(self, loki_config: LokiConfig, mock_loki_client: MagicMock) -> None:
        """is_available should check Loki health."""
        mock_loki_client.health_check.return_value = True

        manager = LogsManager(loki_config=loki_config)

        assert manager.is_available() is True

    @pytest.mark.unit
    def test_search_logs_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """search_logs should call ES client."""
        mock_es_client.search_logs.return_value = [
            {"@timestamp": "2024-01-01T00:00:00Z", "message": "test log"},
        ]

        manager = LogsManager(elasticsearch_config=es_config)
        logs = manager.search_logs(query="error")

        mock_es_client.search_logs.assert_called()
        assert len(logs) == 1

    @pytest.mark.unit
    def test_search_logs_loki(self, loki_config: LokiConfig, mock_loki_client: MagicMock) -> None:
        """search_logs should call Loki client."""
        mock_loki_client.search_kong_logs.return_value = [
            {"timestamp": datetime.now(), "line": "test log"},
        ]

        manager = LogsManager(loki_config=loki_config)
        logs = manager.search_logs(query="error")

        mock_loki_client.search_kong_logs.assert_called()
        assert len(logs) == 1

    @pytest.mark.unit
    def test_get_error_logs(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """get_error_logs should return error logs."""
        mock_es_client.search_error_logs.return_value = [
            {"response_status": 500, "message": "internal error"},
        ]

        manager = LogsManager(elasticsearch_config=es_config)
        errors = manager.get_error_logs()

        mock_es_client.search_error_logs.assert_called()
        assert len(errors) == 1

    @pytest.mark.unit
    def test_from_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """from_elasticsearch classmethod should create ES-backed manager."""
        manager = LogsManager.from_elasticsearch(es_config)

        assert manager.backend == "elasticsearch"

    @pytest.mark.unit
    def test_from_loki(self, loki_config: LokiConfig, mock_loki_client: MagicMock) -> None:
        """from_loki classmethod should create Loki-backed manager."""
        manager = LogsManager.from_loki(loki_config)

        assert manager.backend == "loki"

    @pytest.mark.unit
    def test_es_client_not_configured_raises(
        self, loki_config: LokiConfig, mock_loki_client: MagicMock
    ) -> None:
        """Accessing es_client on a Loki-only manager should raise RuntimeError."""
        manager = LogsManager(loki_config=loki_config)

        with pytest.raises(RuntimeError, match="Elasticsearch is not configured"):
            _ = manager.es_client

    @pytest.mark.unit
    def test_loki_client_not_configured_raises(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """Accessing loki_client on an ES-only manager should raise RuntimeError."""
        manager = LogsManager(elasticsearch_config=es_config)

        with pytest.raises(RuntimeError, match="Loki is not configured"):
            _ = manager.loki_client

    @pytest.mark.unit
    def test_close_es_client(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """close() should call close on the ES client and clear the reference."""
        manager = LogsManager(elasticsearch_config=es_config)
        # Trigger client creation
        _ = manager.es_client

        manager.close()

        mock_es_client.close.assert_called_once()
        assert manager._es_client is None

    @pytest.mark.unit
    def test_close_loki_client(self, loki_config: LokiConfig, mock_loki_client: MagicMock) -> None:
        """close() should call close on the Loki client and clear the reference."""
        manager = LogsManager(loki_config=loki_config)
        # Trigger client creation
        _ = manager.loki_client

        manager.close()

        mock_loki_client.close.assert_called_once()
        assert manager._loki_client is None

    @pytest.mark.unit
    def test_context_manager(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """LogsManager should work as a context manager and call close on exit."""
        with LogsManager(elasticsearch_config=es_config) as manager:
            assert manager is not None
            # Force client creation so close() has something to close
            _ = manager.es_client

        mock_es_client.close.assert_called_once()

    @pytest.mark.unit
    def test_is_available_exception_returns_false(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """is_available should return False when health_check raises an exception."""
        mock_es_client.health_check.side_effect = ConnectionError("refused")

        manager = LogsManager(elasticsearch_config=es_config)

        assert manager.is_available() is False

    @pytest.mark.unit
    def test_get_error_logs_loki(
        self, loki_config: LokiConfig, mock_loki_client: MagicMock
    ) -> None:
        """get_error_logs should delegate to loki_client.get_kong_error_logs."""
        mock_loki_client.get_kong_error_logs.return_value = [
            {"timestamp": datetime.now(), "line": "error log entry"},
        ]

        manager = LogsManager(loki_config=loki_config)
        errors = manager.get_error_logs(service="my-api", limit=50)

        mock_loki_client.get_kong_error_logs.assert_called_once_with(
            service="my-api",
            start_time=None,
            end_time=None,
            limit=50,
        )
        assert len(errors) == 1

    @pytest.mark.unit
    def test_get_services_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """get_services on ES backend should return keys from aggregate_by_service."""
        mock_es_client.aggregate_by_service.return_value = {
            "api-svc": 120,
            "auth-svc": 80,
        }

        manager = LogsManager(elasticsearch_config=es_config)
        services = manager.get_services()

        mock_es_client.aggregate_by_service.assert_called_once()
        assert set(services) == {"api-svc", "auth-svc"}

    @pytest.mark.unit
    def test_get_services_loki(self, loki_config: LokiConfig, mock_loki_client: MagicMock) -> None:
        """get_services on Loki backend should delegate to get_kong_services."""
        mock_loki_client.get_kong_services.return_value = ["svc-a", "svc-b"]

        manager = LogsManager(loki_config=loki_config)
        services = manager.get_services()

        mock_loki_client.get_kong_services.assert_called_once()
        assert services == ["svc-a", "svc-b"]

    @pytest.mark.unit
    def test_get_routes_loki(self, loki_config: LokiConfig, mock_loki_client: MagicMock) -> None:
        """get_routes on Loki backend should delegate to get_kong_routes."""
        mock_loki_client.get_kong_routes.return_value = ["/v1/foo", "/v1/bar"]

        manager = LogsManager(loki_config=loki_config)
        routes = manager.get_routes()

        mock_loki_client.get_kong_routes.assert_called_once()
        assert routes == ["/v1/foo", "/v1/bar"]

    @pytest.mark.unit
    def test_get_routes_elasticsearch_empty(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """get_routes on ES backend should return an empty list."""
        manager = LogsManager(elasticsearch_config=es_config)
        routes = manager.get_routes()

        assert routes == []

    @pytest.mark.unit
    def test_get_status_distribution_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """get_status_distribution on ES backend should delegate to aggregate_by_status."""
        mock_es_client.aggregate_by_status.return_value = {200: 500, 404: 10, 500: 5}

        manager = LogsManager(elasticsearch_config=es_config)
        dist = manager.get_status_distribution(service="my-api")

        mock_es_client.aggregate_by_status.assert_called_once_with(
            start_time=None,
            end_time=None,
            service="my-api",
        )
        assert dist == {200: 500, 404: 10, 500: 5}

    @pytest.mark.unit
    def test_get_status_distribution_loki_unsupported(
        self, loki_config: LokiConfig, mock_loki_client: MagicMock
    ) -> None:
        """get_status_distribution on Loki backend should return empty dict."""
        manager = LogsManager(loki_config=loki_config)
        dist = manager.get_status_distribution()

        assert dist == {}

    @pytest.mark.unit
    def test_get_service_distribution_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """get_service_distribution on ES backend should delegate to aggregate_by_service."""
        mock_es_client.aggregate_by_service.return_value = {"svc-a": 300, "svc-b": 150}

        manager = LogsManager(elasticsearch_config=es_config)
        dist = manager.get_service_distribution()

        mock_es_client.aggregate_by_service.assert_called_once_with(
            start_time=None,
            end_time=None,
        )
        assert dist == {"svc-a": 300, "svc-b": 150}

    @pytest.mark.unit
    def test_get_service_distribution_loki_unsupported(
        self, loki_config: LokiConfig, mock_loki_client: MagicMock
    ) -> None:
        """get_service_distribution on Loki backend should return empty dict."""
        manager = LogsManager(loki_config=loki_config)
        dist = manager.get_service_distribution()

        assert dist == {}

    @pytest.mark.unit
    def test_count_logs_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """count_logs on ES backend should delegate to es_client.count_logs."""
        mock_es_client.count_logs.return_value = 42

        manager = LogsManager(elasticsearch_config=es_config)
        count = manager.count_logs(service="my-api")

        mock_es_client.count_logs.assert_called_once_with(
            start_time=None,
            end_time=None,
            service="my-api",
        )
        assert count == 42

    @pytest.mark.unit
    def test_count_logs_loki_unsupported(
        self, loki_config: LokiConfig, mock_loki_client: MagicMock
    ) -> None:
        """count_logs on Loki backend should return 0."""
        manager = LogsManager(loki_config=loki_config)
        count = manager.count_logs()

        assert count == 0

    @pytest.mark.unit
    def test_get_summary_elasticsearch(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """get_summary on ES backend should return aggregated statistics."""
        mock_es_client.count_logs.return_value = 600
        mock_es_client.aggregate_by_status.return_value = {200: 550, 500: 50}
        mock_es_client.aggregate_by_service.return_value = {"svc-a": 400, "svc-b": 200}

        manager = LogsManager(elasticsearch_config=es_config)
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        summary = manager.get_summary(start_time=start, end_time=end)

        assert summary["backend"] == "elasticsearch"
        assert summary["total_logs"] == 600
        assert summary["status_distribution"] == {200: 550, 500: 50}
        assert summary["error_count"] == 50
        assert summary["service_distribution"] == {"svc-a": 400, "svc-b": 200}
        assert "time_range" in summary
        assert summary["time_range"]["start"] == start.isoformat()
        assert summary["time_range"]["end"] == end.isoformat()

    @pytest.mark.unit
    def test_get_summary_with_service_filter(
        self, es_config: ElasticsearchConfig, mock_es_client: MagicMock
    ) -> None:
        """get_summary with a service filter should omit service_distribution."""
        mock_es_client.count_logs.return_value = 100
        mock_es_client.aggregate_by_status.return_value = {200: 95, 404: 5}

        manager = LogsManager(elasticsearch_config=es_config)
        summary = manager.get_summary(service="my-api")

        assert "service_distribution" not in summary
        assert summary["total_logs"] == 100
        assert summary["error_count"] == 5

    @pytest.mark.unit
    def test_get_summary_loki(self, loki_config: LokiConfig, mock_loki_client: MagicMock) -> None:
        """get_summary on Loki backend should return zeros and empty distributions."""
        manager = LogsManager(loki_config=loki_config)
        start = datetime(2024, 6, 1, 12, 0, 0)
        end = datetime(2024, 6, 1, 13, 0, 0)
        summary = manager.get_summary(start_time=start, end_time=end)

        assert summary["backend"] == "loki"
        assert summary["total_logs"] == 0
        assert summary["status_distribution"] == {}
        assert summary["error_count"] == 0
        assert summary["service_distribution"] == {}


class TestTracingManager:
    """Tests for TracingManager."""

    @pytest.fixture
    def jaeger_config(self) -> JaegerConfig:
        """Create Jaeger test config."""
        return JaegerConfig(query_url="http://localhost:16686")

    @pytest.fixture
    def zipkin_config(self) -> ZipkinConfig:
        """Create Zipkin test config."""
        return ZipkinConfig(url="http://localhost:9411")

    @pytest.fixture
    def mock_jaeger_client(self, mocker: Any) -> MagicMock:
        """Create mock Jaeger client."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.integrations.observability.JaegerClient",
            return_value=mock_client,
        )
        return mock_client

    @pytest.fixture
    def mock_zipkin_client(self, mocker: Any) -> MagicMock:
        """Create mock Zipkin client."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.integrations.observability.ZipkinClient",
            return_value=mock_client,
        )
        return mock_client

    @pytest.mark.unit
    def test_manager_initialization_with_jaeger(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """Manager should initialize with Jaeger."""
        manager = TracingManager(jaeger_config=jaeger_config)

        assert manager.backend == "jaeger"

    @pytest.mark.unit
    def test_manager_initialization_with_zipkin(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """Manager should initialize with Zipkin."""
        manager = TracingManager(zipkin_config=zipkin_config)

        assert manager.backend == "zipkin"

    @pytest.mark.unit
    def test_manager_requires_backend(self) -> None:
        """Manager should require at least one backend."""
        with pytest.raises(ValueError, match="At least one tracing backend"):
            TracingManager()

    @pytest.mark.unit
    def test_from_jaeger_factory(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """from_jaeger should create manager with Jaeger backend."""
        manager = TracingManager.from_jaeger(jaeger_config)

        assert manager.backend == "jaeger"

    @pytest.mark.unit
    def test_from_zipkin_factory(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """from_zipkin should create manager with Zipkin backend."""
        manager = TracingManager.from_zipkin(zipkin_config)

        assert manager.backend == "zipkin"

    @pytest.mark.unit
    def test_is_available_jaeger(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """is_available should check Jaeger health."""
        mock_jaeger_client.health_check.return_value = True

        manager = TracingManager(jaeger_config=jaeger_config)

        assert manager.is_available() is True

    @pytest.mark.unit
    def test_find_traces_jaeger(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """find_traces should call Jaeger client."""
        mock_jaeger_client.get_kong_traces.return_value = [
            {"traceID": "abc123", "spans": []},
        ]

        manager = TracingManager(jaeger_config=jaeger_config)
        traces = manager.find_traces(limit=10)

        mock_jaeger_client.get_kong_traces.assert_called()
        assert len(traces) == 1

    @pytest.mark.unit
    def test_get_trace_jaeger(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_trace should return trace with spans."""
        mock_jaeger_client.get_trace.return_value = {
            "traceID": "abc123",
            "spans": [{"spanID": "span1", "operationName": "HTTP GET"}],
            "processes": {},
        }

        manager = TracingManager(jaeger_config=jaeger_config)
        trace = manager.get_trace("abc123")

        mock_jaeger_client.get_trace.assert_called_with("abc123")
        assert trace["traceID"] == "abc123"

    @pytest.mark.unit
    def test_get_slow_traces(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_slow_traces should return traces above threshold."""
        mock_jaeger_client.get_kong_slow_traces.return_value = [
            {"traceID": "slow1", "spans": [{"duration": 600000}]},
        ]

        manager = TracingManager(jaeger_config=jaeger_config)
        traces = manager.get_slow_traces(threshold_ms=500)

        mock_jaeger_client.get_kong_slow_traces.assert_called()
        assert len(traces) == 1

    @pytest.mark.unit
    def test_get_error_traces(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_error_traces should return error traces."""
        mock_jaeger_client.get_kong_error_traces.return_value = [
            {"traceID": "error1", "spans": [{"tags": [{"key": "error", "value": True}]}]},
        ]

        manager = TracingManager(jaeger_config=jaeger_config)
        traces = manager.get_error_traces()

        mock_jaeger_client.get_kong_error_traces.assert_called()
        assert len(traces) == 1

    @pytest.mark.unit
    def test_analyze_trace(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """analyze_trace should return trace analysis."""
        mock_jaeger_client.analyze_trace.return_value = {
            "trace_id": "abc123",
            "span_count": 5,
            "total_duration_us": 100000,
        }

        manager = TracingManager(jaeger_config=jaeger_config)
        analysis = manager.analyze_trace("abc123")

        mock_jaeger_client.analyze_trace.assert_called_with("abc123")
        assert analysis["span_count"] == 5

    @pytest.mark.unit
    def test_get_services(self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock) -> None:
        """get_services should return service names."""
        mock_jaeger_client.get_services.return_value = ["kong", "backend"]

        manager = TracingManager(jaeger_config=jaeger_config)
        services = manager.get_services()

        assert "kong" in services
        assert "backend" in services

    @pytest.mark.unit
    def test_get_dependencies(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_dependencies should return service graph."""
        mock_jaeger_client.get_dependencies.return_value = [
            {"parent": "kong", "child": "backend", "callCount": 100},
        ]

        manager = TracingManager(jaeger_config=jaeger_config)
        deps = manager.get_dependencies()

        mock_jaeger_client.get_dependencies.assert_called()
        assert len(deps) == 1

    @pytest.mark.unit
    def test_context_manager(self, jaeger_config: JaegerConfig) -> None:
        """Manager should work as context manager."""
        with TracingManager(jaeger_config=jaeger_config) as manager:
            assert manager is not None
            # Close is called on exit

    @pytest.mark.unit
    def test_zipkin_normalization(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """Zipkin traces should be normalized to Jaeger format."""
        mock_zipkin_client.get_kong_traces.return_value = [
            [
                {
                    "traceId": "abc123",
                    "id": "span1",
                    "name": "HTTP GET",
                    "localEndpoint": {"serviceName": "kong"},
                    "duration": 1000,
                    "timestamp": 1234567890000000,
                },
            ],
        ]

        manager = TracingManager(zipkin_config=zipkin_config)
        traces = manager.find_traces()

        # Traces should be in Jaeger-like format
        assert len(traces) == 1
        assert "traceID" in traces[0]
        assert "spans" in traces[0]
        assert "processes" in traces[0]
