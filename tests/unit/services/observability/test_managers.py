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


class TestTracingManagerClientErrors:
    """Tests for TracingManager client property error paths."""

    @pytest.fixture
    def jaeger_config(self) -> JaegerConfig:
        """Create Jaeger test config."""
        return JaegerConfig(query_url="http://localhost:16686")

    @pytest.fixture
    def zipkin_config(self) -> ZipkinConfig:
        """Create Zipkin test config."""
        return ZipkinConfig(url="http://localhost:9411")

    @pytest.mark.unit
    def test_jaeger_client_property_raises_when_not_configured(
        self, zipkin_config: ZipkinConfig
    ) -> None:
        """jaeger_client property should raise RuntimeError when Jaeger is not configured."""
        manager = TracingManager(zipkin_config=zipkin_config)

        with pytest.raises(RuntimeError, match="Jaeger is not configured"):
            _ = manager.jaeger_client

    @pytest.mark.unit
    def test_zipkin_client_property_raises_when_not_configured(
        self, jaeger_config: JaegerConfig
    ) -> None:
        """zipkin_client property should raise RuntimeError when Zipkin is not configured."""
        manager = TracingManager(jaeger_config=jaeger_config)

        with pytest.raises(RuntimeError, match="Zipkin is not configured"):
            _ = manager.zipkin_client


class TestTracingManagerClose:
    """Tests for TracingManager.close() method."""

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
    def test_close_calls_jaeger_client_close_and_clears_reference(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """close() should call close on the Jaeger client and set internal reference to None."""
        manager = TracingManager(jaeger_config=jaeger_config)
        # Force client creation via property access
        _ = manager.jaeger_client

        manager.close()

        mock_jaeger_client.close.assert_called_once()
        manager_any: Any = manager
        assert manager_any._jaeger_client is None

    @pytest.mark.unit
    def test_close_calls_zipkin_client_close_and_clears_reference(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """close() should call close on the Zipkin client and set internal reference to None."""
        manager = TracingManager(zipkin_config=zipkin_config)
        # Force client creation via property access
        _ = manager.zipkin_client

        manager.close()

        mock_zipkin_client.close.assert_called_once()
        manager_any: Any = manager
        assert manager_any._zipkin_client is None

    @pytest.mark.unit
    def test_close_without_clients_is_safe(self, jaeger_config: JaegerConfig) -> None:
        """close() should not raise when no clients have been created."""
        manager = TracingManager(jaeger_config=jaeger_config)
        # No clients created; calling close should be a no-op
        manager.close()

    @pytest.mark.unit
    def test_context_manager_closes_jaeger_client(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """Context manager exit should call close on the Jaeger client."""
        with TracingManager(jaeger_config=jaeger_config) as manager:
            _ = manager.jaeger_client

        mock_jaeger_client.close.assert_called_once()

    @pytest.mark.unit
    def test_context_manager_closes_zipkin_client(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """Context manager exit should call close on the Zipkin client."""
        with TracingManager(zipkin_config=zipkin_config) as manager:
            _ = manager.zipkin_client

        mock_zipkin_client.close.assert_called_once()


class TestTracingManagerZipkinPaths:
    """Tests for TracingManager methods that execute the Zipkin backend branch."""

    @pytest.fixture
    def zipkin_config(self) -> ZipkinConfig:
        """Create Zipkin test config."""
        return ZipkinConfig(url="http://localhost:9411")

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
    def test_is_available_zipkin_returns_true(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """is_available should delegate to zipkin_client.health_check and return True."""
        mock_zipkin_client.health_check.return_value = True

        manager = TracingManager(zipkin_config=zipkin_config)

        assert manager.is_available() is True
        mock_zipkin_client.health_check.assert_called_once()

    @pytest.mark.unit
    def test_is_available_zipkin_exception_returns_false(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """is_available should return False when zipkin_client.health_check raises."""
        mock_zipkin_client.health_check.side_effect = ConnectionError("refused")

        manager = TracingManager(zipkin_config=zipkin_config)

        assert manager.is_available() is False

    @pytest.mark.unit
    def test_is_available_jaeger_exception_returns_false(self, mocker: Any) -> None:
        """is_available should return False when jaeger_client.health_check raises."""
        mock_client = MagicMock()
        mock_client.health_check.side_effect = ConnectionError("refused")
        mocker.patch(
            "system_operations_manager.integrations.observability.JaegerClient",
            return_value=mock_client,
        )
        jaeger_config = JaegerConfig(query_url="http://localhost:16686")
        manager = TracingManager(jaeger_config=jaeger_config)

        assert manager.is_available() is False

    @pytest.mark.unit
    def test_get_trace_zipkin_normalizes_spans(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_trace on Zipkin backend should normalize the span list to Jaeger format."""
        mock_zipkin_client.get_trace.return_value = [
            {
                "traceId": "trace99",
                "id": "spanA",
                "name": "GET /api",
                "localEndpoint": {"serviceName": "kong"},
                "duration": 2500,
                "timestamp": 1700000000000000,
                "tags": {"http.status_code": "200"},
            }
        ]

        manager = TracingManager(zipkin_config=zipkin_config)
        trace = manager.get_trace("trace99")

        mock_zipkin_client.get_trace.assert_called_once_with("trace99")
        assert trace["traceID"] == "trace99"
        assert len(trace["spans"]) == 1
        assert trace["spans"][0]["operationName"] == "GET /api"

    @pytest.mark.unit
    def test_get_slow_traces_zipkin_converts_ms_to_us(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_slow_traces on Zipkin backend should convert threshold from ms to us."""
        mock_zipkin_client.get_kong_slow_traces.return_value = [
            [
                {
                    "traceId": "slowTrace1",
                    "id": "s1",
                    "name": "POST /slow",
                    "localEndpoint": {"serviceName": "kong"},
                    "duration": 800000,
                    "timestamp": 1700000000000000,
                    "tags": {},
                }
            ]
        ]

        manager = TracingManager(zipkin_config=zipkin_config)
        traces = manager.get_slow_traces(threshold_ms=500)

        mock_zipkin_client.get_kong_slow_traces.assert_called_once_with(
            threshold_us=500000,
            service_name="kong",
            start_time=None,
            end_time=None,
            limit=20,
        )
        assert len(traces) == 1
        assert traces[0]["traceID"] == "slowTrace1"

    @pytest.mark.unit
    def test_get_slow_traces_zipkin_with_time_range(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_slow_traces on Zipkin backend should pass through time range parameters."""
        mock_zipkin_client.get_kong_slow_traces.return_value = []

        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        manager = TracingManager(zipkin_config=zipkin_config)
        traces = manager.get_slow_traces(threshold_ms=200, start_time=start, end_time=end, limit=5)

        mock_zipkin_client.get_kong_slow_traces.assert_called_once_with(
            threshold_us=200000,
            service_name="kong",
            start_time=start,
            end_time=end,
            limit=5,
        )
        assert traces == []

    @pytest.mark.unit
    def test_get_error_traces_zipkin_normalizes_response(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_error_traces on Zipkin backend should normalize and return error traces."""
        mock_zipkin_client.get_kong_error_traces.return_value = [
            [
                {
                    "traceId": "errTrace1",
                    "id": "errSpan1",
                    "name": "GET /broken",
                    "localEndpoint": {"serviceName": "kong"},
                    "duration": 300,
                    "timestamp": 1700000000000000,
                    "tags": {"error": "true"},
                }
            ]
        ]

        manager = TracingManager(zipkin_config=zipkin_config)
        traces = manager.get_error_traces()

        mock_zipkin_client.get_kong_error_traces.assert_called_once_with(
            service_name="kong",
            start_time=None,
            end_time=None,
            limit=20,
        )
        assert len(traces) == 1
        assert traces[0]["traceID"] == "errTrace1"

    @pytest.mark.unit
    def test_get_error_traces_zipkin_with_params(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_error_traces on Zipkin backend should forward time range and limit."""
        mock_zipkin_client.get_kong_error_traces.return_value = []

        start = datetime(2024, 3, 1, 0, 0, 0)
        end = datetime(2024, 3, 1, 2, 0, 0)
        manager = TracingManager(zipkin_config=zipkin_config)
        traces = manager.get_error_traces(start_time=start, end_time=end, limit=10)

        mock_zipkin_client.get_kong_error_traces.assert_called_once_with(
            service_name="kong",
            start_time=start,
            end_time=end,
            limit=10,
        )
        assert traces == []

    @pytest.mark.unit
    def test_analyze_trace_zipkin(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """analyze_trace on Zipkin backend should delegate to zipkin_client.analyze_trace."""
        expected: dict[str, Any] = {"trace_id": "t1", "span_count": 3, "total_duration_us": 50000}
        mock_zipkin_client.analyze_trace.return_value = expected

        manager = TracingManager(zipkin_config=zipkin_config)
        result = manager.analyze_trace("t1")

        mock_zipkin_client.analyze_trace.assert_called_once_with("t1")
        assert result == expected

    @pytest.mark.unit
    def test_get_services_zipkin(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_services on Zipkin backend should delegate to zipkin_client.get_services."""
        mock_zipkin_client.get_services.return_value = ["kong", "upstream-svc"]

        manager = TracingManager(zipkin_config=zipkin_config)
        services = manager.get_services()

        mock_zipkin_client.get_services.assert_called_once()
        assert "kong" in services

    @pytest.mark.unit
    def test_get_operations_jaeger_uses_service_name_default(self, mocker: Any) -> None:
        """get_operations on Jaeger backend should use service_name when service is None."""
        mock_client = MagicMock()
        mock_client.get_operations.return_value = ["GET /api", "POST /api"]
        mocker.patch(
            "system_operations_manager.integrations.observability.JaegerClient",
            return_value=mock_client,
        )
        jaeger_config = JaegerConfig(query_url="http://localhost:16686")
        manager = TracingManager(jaeger_config=jaeger_config, service_name="my-kong")

        ops = manager.get_operations()

        mock_client.get_operations.assert_called_once_with("my-kong")
        assert ops == ["GET /api", "POST /api"]

    @pytest.mark.unit
    def test_get_operations_jaeger_uses_explicit_service(self, mocker: Any) -> None:
        """get_operations on Jaeger backend should use the provided service name."""
        mock_client = MagicMock()
        mock_client.get_operations.return_value = ["DELETE /resource"]
        mocker.patch(
            "system_operations_manager.integrations.observability.JaegerClient",
            return_value=mock_client,
        )
        jaeger_config = JaegerConfig(query_url="http://localhost:16686")
        manager = TracingManager(jaeger_config=jaeger_config)

        ops = manager.get_operations(service="custom-svc")

        mock_client.get_operations.assert_called_once_with("custom-svc")
        assert ops == ["DELETE /resource"]

    @pytest.mark.unit
    def test_get_operations_zipkin_uses_get_spans(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_operations on Zipkin backend should call zipkin_client.get_spans."""
        mock_zipkin_client.get_spans.return_value = ["span-a", "span-b"]

        manager = TracingManager(zipkin_config=zipkin_config, service_name="kong")

        ops = manager.get_operations()

        mock_zipkin_client.get_spans.assert_called_once_with("kong")
        assert ops == ["span-a", "span-b"]

    @pytest.mark.unit
    def test_get_operations_zipkin_with_explicit_service(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_operations on Zipkin backend should pass explicit service to get_spans."""
        mock_zipkin_client.get_spans.return_value = ["span-x"]

        manager = TracingManager(zipkin_config=zipkin_config)

        ops = manager.get_operations(service="other-svc")

        mock_zipkin_client.get_spans.assert_called_once_with("other-svc")
        assert ops == ["span-x"]

    @pytest.mark.unit
    def test_get_dependencies_zipkin_converts_hours_to_ms(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_dependencies on Zipkin backend should convert lookback hours to milliseconds."""
        mock_zipkin_client.get_dependencies.return_value = [
            {"parent": "kong", "child": "db", "callCount": 50}
        ]

        manager = TracingManager(zipkin_config=zipkin_config)
        deps = manager.get_dependencies(lookback_hours=2)

        mock_zipkin_client.get_dependencies.assert_called_once_with(
            end_time=None,
            lookback=2 * 60 * 60 * 1000,
        )
        assert len(deps) == 1

    @pytest.mark.unit
    def test_get_dependencies_zipkin_with_end_time(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_dependencies on Zipkin backend should forward end_time."""
        mock_zipkin_client.get_dependencies.return_value = []

        end = datetime(2024, 6, 1, 12, 0, 0)
        manager = TracingManager(zipkin_config=zipkin_config)
        deps = manager.get_dependencies(end_time=end, lookback_hours=1)

        mock_zipkin_client.get_dependencies.assert_called_once_with(
            end_time=end,
            lookback=3600000,
        )
        assert deps == []


class TestTracingManagerNormalizeZipkinTrace:
    """Tests for TracingManager._normalize_zipkin_trace helper."""

    @pytest.fixture
    def jaeger_config(self) -> JaegerConfig:
        """Create Jaeger test config."""
        return JaegerConfig(query_url="http://localhost:16686")

    @pytest.mark.unit
    def test_normalize_zipkin_trace_empty_spans_returns_skeleton(
        self, jaeger_config: JaegerConfig
    ) -> None:
        """_normalize_zipkin_trace with an empty list should return the empty skeleton."""
        manager = TracingManager(jaeger_config=jaeger_config)
        result = manager._normalize_zipkin_trace([])

        assert result == {"spans": [], "processes": {}}

    @pytest.mark.unit
    def test_normalize_zipkin_trace_multiple_spans_same_service(
        self, jaeger_config: JaegerConfig
    ) -> None:
        """_normalize_zipkin_trace should deduplicate processes for same service."""
        spans = [
            {
                "traceId": "tid1",
                "id": "s1",
                "name": "op-a",
                "localEndpoint": {"serviceName": "kong"},
                "duration": 100,
                "timestamp": 1000,
                "tags": {"k": "v"},
            },
            {
                "traceId": "tid1",
                "id": "s2",
                "name": "op-b",
                "localEndpoint": {"serviceName": "kong"},
                "duration": 200,
                "timestamp": 2000,
                "tags": {},
            },
        ]
        manager = TracingManager(jaeger_config=jaeger_config)
        result = manager._normalize_zipkin_trace(spans)

        assert result["traceID"] == "tid1"
        assert len(result["spans"]) == 2
        # Both spans share the same service; only one process entry should be created
        assert len(result["processes"]) == 1

    @pytest.mark.unit
    def test_normalize_zipkin_trace_multiple_services_creates_multiple_processes(
        self, jaeger_config: JaegerConfig
    ) -> None:
        """_normalize_zipkin_trace should create one process entry per distinct service."""
        spans = [
            {
                "traceId": "tid2",
                "id": "s1",
                "name": "op-a",
                "localEndpoint": {"serviceName": "service-alpha"},
                "duration": 100,
                "timestamp": 1000,
                "tags": {},
            },
            {
                "traceId": "tid2",
                "id": "s2",
                "name": "op-b",
                "localEndpoint": {"serviceName": "service-beta"},
                "duration": 200,
                "timestamp": 2000,
                "tags": {"x": "y"},
            },
        ]
        manager = TracingManager(jaeger_config=jaeger_config)
        result = manager._normalize_zipkin_trace(spans)

        assert result["traceID"] == "tid2"
        assert len(result["spans"]) == 2
        assert len(result["processes"]) == 2
        service_names = {p["serviceName"] for p in result["processes"].values()}
        assert service_names == {"service-alpha", "service-beta"}

    @pytest.mark.unit
    def test_normalize_zipkin_trace_tags_converted_to_list(
        self, jaeger_config: JaegerConfig
    ) -> None:
        """_normalize_zipkin_trace should convert span tags dict to key/value list."""
        spans = [
            {
                "traceId": "tid3",
                "id": "s1",
                "name": "op",
                "localEndpoint": {"serviceName": "svc"},
                "duration": 50,
                "timestamp": 500,
                "tags": {"http.method": "GET", "http.status_code": "200"},
            }
        ]
        manager = TracingManager(jaeger_config=jaeger_config)
        result = manager._normalize_zipkin_trace(spans)

        normalized_span = result["spans"][0]
        tag_keys = {t["key"] for t in normalized_span["tags"]}
        assert "http.method" in tag_keys
        assert "http.status_code" in tag_keys


class TestTracingManagerGetSummary:
    """Tests for TracingManager.get_summary() method."""

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
    def test_get_summary_jaeger_with_explicit_time_range(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_summary with explicit times should include backend, service, and time_range."""
        mock_jaeger_client.get_kong_traces.return_value = []
        mock_jaeger_client.get_kong_error_traces.return_value = []
        mock_jaeger_client.get_services.return_value = ["kong", "backend"]

        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        manager = TracingManager(jaeger_config=jaeger_config)
        summary = manager.get_summary(start_time=start, end_time=end)

        assert summary["backend"] == "jaeger"
        assert summary["service_name"] == "kong"
        assert summary["time_range"]["start"] == start.isoformat()
        assert summary["time_range"]["end"] == end.isoformat()
        assert summary["trace_count"] == 0
        assert summary["error_trace_count"] == 0
        assert summary["services"] == ["kong", "backend"]

    @pytest.mark.unit
    def test_get_summary_uses_defaults_for_missing_times(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_summary with no times provided should default to now minus one hour."""
        mock_jaeger_client.get_kong_traces.return_value = []
        mock_jaeger_client.get_kong_error_traces.return_value = []
        mock_jaeger_client.get_services.return_value = []

        manager = TracingManager(jaeger_config=jaeger_config)
        summary = manager.get_summary()

        assert "time_range" in summary
        assert "start" in summary["time_range"]
        assert "end" in summary["time_range"]
        # Both values should be valid ISO format strings
        datetime.fromisoformat(summary["time_range"]["start"])
        datetime.fromisoformat(summary["time_range"]["end"])

    @pytest.mark.unit
    def test_get_summary_uses_default_end_time_only(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_summary with only start_time provided should default end_time to now."""
        mock_jaeger_client.get_kong_traces.return_value = []
        mock_jaeger_client.get_kong_error_traces.return_value = []
        mock_jaeger_client.get_services.return_value = []

        start = datetime(2024, 5, 1, 0, 0, 0)
        manager = TracingManager(jaeger_config=jaeger_config)
        summary = manager.get_summary(start_time=start)

        assert summary["time_range"]["start"] == start.isoformat()
        datetime.fromisoformat(summary["time_range"]["end"])

    @pytest.mark.unit
    def test_get_summary_duration_stats_populated_when_traces_have_spans(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_summary should compute duration_stats when traces contain spans."""
        traces = [
            {"traceID": "t1", "spans": [{"duration": 100}, {"duration": 200}]},
            {"traceID": "t2", "spans": [{"duration": 300}]},
            {"traceID": "t3", "spans": [{"duration": 50}, {"duration": 400}]},
        ]
        mock_jaeger_client.get_kong_traces.return_value = traces
        mock_jaeger_client.get_kong_error_traces.return_value = []
        mock_jaeger_client.get_services.return_value = []

        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        manager = TracingManager(jaeger_config=jaeger_config)
        summary = manager.get_summary(start_time=start, end_time=end)

        assert summary["trace_count"] == 3
        stats = summary["duration_stats"]
        assert "min_us" in stats
        assert "max_us" in stats
        assert "avg_us" in stats
        assert "p50_us" in stats
        assert "p90_us" in stats
        assert "p99_us" in stats
        assert stats["min_us"] == 200
        assert stats["max_us"] == 400

    @pytest.mark.unit
    def test_get_summary_duration_stats_empty_when_no_spans(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_summary should set duration_stats to empty dict when traces have no spans."""
        mock_jaeger_client.get_kong_traces.return_value = [
            {"traceID": "t1", "spans": []},
        ]
        mock_jaeger_client.get_kong_error_traces.return_value = []
        mock_jaeger_client.get_services.return_value = []

        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        manager = TracingManager(jaeger_config=jaeger_config)
        summary = manager.get_summary(start_time=start, end_time=end)

        assert summary["duration_stats"] == {}

    @pytest.mark.unit
    def test_get_summary_duration_stats_empty_when_no_traces(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_summary should set duration_stats to empty dict when there are no traces."""
        mock_jaeger_client.get_kong_traces.return_value = []
        mock_jaeger_client.get_kong_error_traces.return_value = []
        mock_jaeger_client.get_services.return_value = []

        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        manager = TracingManager(jaeger_config=jaeger_config)
        summary = manager.get_summary(start_time=start, end_time=end)

        assert summary["duration_stats"] == {}

    @pytest.mark.unit
    def test_get_summary_error_trace_count(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_summary should report the correct number of error traces."""
        mock_jaeger_client.get_kong_traces.return_value = []
        mock_jaeger_client.get_kong_error_traces.return_value = [
            {"traceID": "e1", "spans": []},
            {"traceID": "e2", "spans": []},
        ]
        mock_jaeger_client.get_services.return_value = []

        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        manager = TracingManager(jaeger_config=jaeger_config)
        summary = manager.get_summary(start_time=start, end_time=end)

        assert summary["error_trace_count"] == 2

    @pytest.mark.unit
    def test_get_summary_zipkin_backend(
        self, zipkin_config: ZipkinConfig, mock_zipkin_client: MagicMock
    ) -> None:
        """get_summary should work correctly with a Zipkin backend."""
        mock_zipkin_client.get_kong_traces.return_value = [
            [
                {
                    "traceId": "zt1",
                    "id": "zs1",
                    "name": "GET /z",
                    "localEndpoint": {"serviceName": "kong"},
                    "duration": 150,
                    "timestamp": 1700000000000000,
                    "tags": {},
                }
            ]
        ]
        mock_zipkin_client.get_kong_error_traces.return_value = []
        mock_zipkin_client.get_services.return_value = ["kong"]

        start = datetime(2024, 2, 1, 0, 0, 0)
        end = datetime(2024, 2, 1, 1, 0, 0)
        manager = TracingManager(zipkin_config=zipkin_config)
        summary = manager.get_summary(start_time=start, end_time=end)

        assert summary["backend"] == "zipkin"
        assert summary["trace_count"] == 1
        assert summary["error_trace_count"] == 0
        assert "kong" in summary["services"]

    @pytest.mark.unit
    def test_get_summary_custom_limit_and_service_name(
        self, jaeger_config: JaegerConfig, mock_jaeger_client: MagicMock
    ) -> None:
        """get_summary should pass limit to find_traces and get_error_traces."""
        mock_jaeger_client.get_kong_traces.return_value = []
        mock_jaeger_client.get_kong_error_traces.return_value = []
        mock_jaeger_client.get_services.return_value = []

        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        manager = TracingManager(jaeger_config=jaeger_config, service_name="custom-kong")
        summary = manager.get_summary(start_time=start, end_time=end, limit=50)

        assert summary["service_name"] == "custom-kong"
        # Verify limit was forwarded to the underlying client calls
        call_kwargs: Any = mock_jaeger_client.get_kong_traces.call_args
        assert call_kwargs.kwargs.get("limit") == 50


class TestMetricsManagerMissingBranches:
    """Tests that cover the previously uncovered lines in MetricsManager.

    Targets: lines 66-67, 85-86, 167, 179, 195, 215-220, 228, 236, 262, 271-273.
    """

    @pytest.fixture
    def config(self) -> PrometheusConfig:
        """Create a Prometheus test configuration."""
        return PrometheusConfig(url="http://localhost:9090")

    @pytest.fixture
    def mock_prometheus_client(self, mocker: Any) -> MagicMock:
        """Patch PrometheusClient and return the mock instance."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.integrations.observability.PrometheusClient",
            return_value=mock_client,
        )
        return mock_client

    # -------------------------------------------------------------------------
    # lines 66-67: close() flushes _client when it is not None
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_close_calls_client_close_and_nullifies_reference(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """close() must call close() on the live client and set _client to None."""
        manager = MetricsManager(config)
        # Access .client to force lazy initialisation (sets _client).
        _ = manager.client

        manager.close()

        mock_prometheus_client.close.assert_called_once()
        assert manager._client is None

    @pytest.mark.unit
    def test_close_is_idempotent_when_client_never_created(self, config: PrometheusConfig) -> None:
        """close() with _client already None must not raise and must stay None."""
        manager = MetricsManager(config)
        manager.close()

        assert manager._client is None

    @pytest.mark.unit
    def test_context_manager_exit_closes_live_client(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """Leaving the context manager must close an initialised client."""
        with MetricsManager(config) as manager:
            _ = manager.client  # force _client initialisation

        mock_prometheus_client.close.assert_called_once()
        assert manager._client is None

    # -------------------------------------------------------------------------
    # lines 85-86: is_available() returns False on any exception
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_is_available_returns_false_on_connection_error(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """is_available() must swallow ConnectionError and return False."""
        mock_prometheus_client.health_check.side_effect = ConnectionError("refused")

        manager = MetricsManager(config)

        assert manager.is_available() is False

    @pytest.mark.unit
    def test_is_available_returns_false_on_runtime_error(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """is_available() must swallow RuntimeError and return False."""
        mock_prometheus_client.health_check.side_effect = RuntimeError("boom")

        manager = MetricsManager(config)

        assert manager.is_available() is False

    @pytest.mark.unit
    def test_is_available_returns_false_on_value_error(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """is_available() must swallow ValueError and return False."""
        mock_prometheus_client.health_check.side_effect = ValueError("bad value")

        manager = MetricsManager(config)

        assert manager.is_available() is False

    # -------------------------------------------------------------------------
    # line 167: get_bandwidth() delegates to client.get_kong_bandwidth
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_get_bandwidth_both_directions(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_bandwidth() with direction='both' should forward all args to the client."""
        expected: Any = {
            "ingress": [{"value": [1609459200, "1024"]}],
            "egress": [{"value": [1609459200, "512"]}],
        }
        mock_prometheus_client.get_kong_bandwidth.return_value = expected

        manager = MetricsManager(config)
        result = manager.get_bandwidth(service="api", direction="both", time_range="10m")

        mock_prometheus_client.get_kong_bandwidth.assert_called_once_with(
            service="api",
            direction="both",
            time_range="10m",
        )
        assert result == expected

    @pytest.mark.unit
    def test_get_bandwidth_ingress_only(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_bandwidth() with direction='ingress' should pass that through."""
        expected: Any = {"ingress": [{"value": [1609459200, "4096"]}]}
        mock_prometheus_client.get_kong_bandwidth.return_value = expected

        manager = MetricsManager(config)
        result = manager.get_bandwidth(direction="ingress")

        mock_prometheus_client.get_kong_bandwidth.assert_called_once_with(
            service=None,
            direction="ingress",
            time_range="5m",
        )
        assert result == expected

    @pytest.mark.unit
    def test_get_bandwidth_egress_only(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_bandwidth() with direction='egress' should pass that through."""
        expected: Any = {"egress": [{"value": [1609459200, "256"]}]}
        mock_prometheus_client.get_kong_bandwidth.return_value = expected

        manager = MetricsManager(config)
        result = manager.get_bandwidth(direction="egress")

        mock_prometheus_client.get_kong_bandwidth.assert_called_once_with(
            service=None,
            direction="egress",
            time_range="5m",
        )
        assert result == expected

    # -------------------------------------------------------------------------
    # line 179: get_upstream_health() delegates to client.get_kong_upstream_health
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_get_upstream_health_returns_client_result(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_upstream_health() should return what the Prometheus client returns."""
        expected: Any = [
            {"upstream": "svc-upstream", "target": "10.0.0.1:8080", "status": "healthy"},
            {"upstream": "svc-upstream", "target": "10.0.0.2:8080", "status": "unhealthy"},
        ]
        mock_prometheus_client.get_kong_upstream_health.return_value = expected

        manager = MetricsManager(config)
        result = manager.get_upstream_health()

        mock_prometheus_client.get_kong_upstream_health.assert_called_once()
        assert result == expected

    @pytest.mark.unit
    def test_get_upstream_health_returns_empty_list(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_upstream_health() should propagate an empty list when there are no targets."""
        mock_prometheus_client.get_kong_upstream_health.return_value = []

        manager = MetricsManager(config)
        result = manager.get_upstream_health()

        assert result == []

    # -------------------------------------------------------------------------
    # line 195: query() delegates to client.query
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_query_without_time(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """query() with no time argument should call client.query with time=None."""
        expected: Any = [{"metric": {}, "value": [1609459200, "99"]}]
        mock_prometheus_client.query.return_value = expected

        manager = MetricsManager(config)
        result = manager.query("up")

        mock_prometheus_client.query.assert_called_once_with("up", time=None)
        assert result == expected

    @pytest.mark.unit
    def test_query_with_explicit_timestamp(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """query() should forward an explicit timestamp to the client unchanged."""
        ts = datetime(2024, 3, 1, 9, 0, 0)
        expected: Any = [{"metric": {}, "value": [1709283600, "3"]}]
        mock_prometheus_client.query.return_value = expected

        manager = MetricsManager(config)
        result = manager.query("kong_http_status_total", time=ts)

        mock_prometheus_client.query.assert_called_once_with("kong_http_status_total", time=ts)
        assert result == expected

    # -------------------------------------------------------------------------
    # lines 215-220: query_range() default start / end logic
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_query_range_explicit_start_and_end_passed_through(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """query_range() with explicit start and end should not modify them."""
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 1, 1, 0, 0)
        mock_prometheus_client.query_range.return_value = []

        manager = MetricsManager(config)
        manager.query_range("up", start=start, end=end, step="30s")

        mock_prometheus_client.query_range.assert_called_once_with(
            "up", start=start, end=end, step="30s"
        )

    @pytest.mark.unit
    def test_query_range_end_defaults_to_now_start_defaults_to_one_hour_ago(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock, mocker: Any
    ) -> None:
        """query_range() with no start/end should default end=now, start=now-1h."""
        from datetime import timedelta

        fixed_now = datetime(2024, 6, 15, 12, 0, 0)
        mock_dt: Any = mocker.patch(
            "system_operations_manager.services.observability.metrics_manager.datetime"
        )
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        mock_prometheus_client.query_range.return_value = []

        manager = MetricsManager(config)
        manager.query_range("up")

        call_kwargs: Any = mock_prometheus_client.query_range.call_args
        _, kwargs = call_kwargs
        assert kwargs["end"] == fixed_now
        assert kwargs["start"] == fixed_now - timedelta(hours=1)

    @pytest.mark.unit
    def test_query_range_with_only_end_provided_computes_start(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """query_range() with only end provided should compute start as end minus 1 hour."""
        from datetime import timedelta

        end = datetime(2024, 4, 10, 18, 0, 0)
        mock_prometheus_client.query_range.return_value = []

        manager = MetricsManager(config)
        manager.query_range("up", end=end)

        call_kwargs: Any = mock_prometheus_client.query_range.call_args
        _, kwargs = call_kwargs
        assert kwargs["end"] == end
        assert kwargs["start"] == end - timedelta(hours=1)

    @pytest.mark.unit
    def test_query_range_with_only_start_provided_computes_end(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """query_range() with only start provided should default end to datetime.now()."""
        start = datetime(2024, 4, 10, 17, 0, 0)
        mock_prometheus_client.query_range.return_value = []

        manager = MetricsManager(config)
        manager.query_range("up", start=start)

        call_kwargs: Any = mock_prometheus_client.query_range.call_args
        _, kwargs = call_kwargs
        assert kwargs["start"] == start
        assert isinstance(kwargs["end"], datetime)

    # -------------------------------------------------------------------------
    # line 228: get_services() delegates to client.get_label_values("service")
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_get_services_delegates_to_client(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_services() should call get_label_values with the 'service' label."""
        expected: Any = ["billing-svc", "auth-svc", "orders-svc"]
        mock_prometheus_client.get_label_values.return_value = expected

        manager = MetricsManager(config)
        result = manager.get_services()

        mock_prometheus_client.get_label_values.assert_called_once_with("service")
        assert result == expected

    @pytest.mark.unit
    def test_get_services_returns_empty_list_when_none_present(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_services() should propagate an empty list from the client."""
        mock_prometheus_client.get_label_values.return_value = []

        manager = MetricsManager(config)
        result = manager.get_services()

        assert result == []

    # -------------------------------------------------------------------------
    # line 236: get_routes() delegates to client.get_label_values("route")
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_get_routes_delegates_to_client(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_routes() should call get_label_values with the 'route' label."""
        expected: Any = ["/v1/users", "/v1/orders", "/health"]
        mock_prometheus_client.get_label_values.return_value = expected

        manager = MetricsManager(config)
        result = manager.get_routes()

        mock_prometheus_client.get_label_values.assert_called_once_with("route")
        assert result == expected

    @pytest.mark.unit
    def test_get_routes_returns_empty_list_when_none_present(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_routes() should propagate an empty list from the client."""
        mock_prometheus_client.get_label_values.return_value = []

        manager = MetricsManager(config)
        result = manager.get_routes()

        assert result == []

    # -------------------------------------------------------------------------
    # line 262: get_summary() else branch - empty request_rates list
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_get_summary_empty_request_rates_sets_rate_to_zero(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_summary() should set request_rate_per_second=0.0 when rate list is empty."""
        mock_prometheus_client.get_kong_request_rate.return_value = []
        mock_prometheus_client.get_kong_error_rate.return_value = [
            {"value": [1609459200, "0.02"]},
        ]
        mock_prometheus_client.get_kong_latency_percentiles.return_value = {}

        manager = MetricsManager(config)
        summary = manager.get_summary()

        assert summary["request_rate_per_second"] == 0.0

    # -------------------------------------------------------------------------
    # lines 271-273: get_summary() else branch - missing or empty error_rates
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_get_summary_empty_error_rates_list_sets_error_rate_to_zero(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_summary() should set error_rate=0.0 when the error rate list is empty."""
        mock_prometheus_client.get_kong_request_rate.return_value = []
        mock_prometheus_client.get_kong_error_rate.return_value = []
        mock_prometheus_client.get_kong_latency_percentiles.return_value = {}

        manager = MetricsManager(config)
        summary = manager.get_summary()

        assert summary["error_rate"] == 0.0

    @pytest.mark.unit
    def test_get_summary_error_rate_entry_without_value_key_sets_error_rate_to_zero(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_summary() should set error_rate=0.0 when the first entry lacks 'value'."""
        mock_prometheus_client.get_kong_request_rate.return_value = []
        mock_prometheus_client.get_kong_error_rate.return_value = [{}]
        mock_prometheus_client.get_kong_latency_percentiles.return_value = {}

        manager = MetricsManager(config)
        summary = manager.get_summary()

        assert summary["error_rate"] == 0.0

    @pytest.mark.unit
    def test_get_summary_error_rate_value_list_with_single_element_sets_zero(
        self, config: PrometheusConfig, mock_prometheus_client: MagicMock
    ) -> None:
        """get_summary() should set error_rate=0.0 when the value list has only one element."""
        mock_prometheus_client.get_kong_request_rate.return_value = []
        # A value list with only a timestamp and no rate component.
        mock_prometheus_client.get_kong_error_rate.return_value = [
            {"value": [1609459200]},
        ]
        mock_prometheus_client.get_kong_latency_percentiles.return_value = {}

        manager = MetricsManager(config)
        summary = manager.get_summary()

        assert summary["error_rate"] == 0.0
