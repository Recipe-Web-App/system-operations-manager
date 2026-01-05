"""Unit tests for Kong ObservabilityManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.observability import (
    TargetHealthDetail,
)
from system_operations_manager.services.kong.observability_manager import (
    ObservabilityManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client: MagicMock) -> ObservabilityManager:
    """Create an ObservabilityManager with mocked client."""
    return ObservabilityManager(mock_client)


class TestObservabilityManagerInit:
    """Tests for ObservabilityManager initialization."""

    @pytest.mark.unit
    def test_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = ObservabilityManager(mock_client)

        assert manager._client is mock_client


class TestObservabilityManagerRawMetrics:
    """Tests for get_raw_metrics method."""

    @pytest.mark.unit
    def test_get_raw_metrics_success(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """get_raw_metrics should return raw Prometheus text."""
        mock_client.get.return_value = {"raw": "kong_http_requests_total 100\n"}

        result = manager.get_raw_metrics()

        assert "kong_http_requests_total" in result
        mock_client.get.assert_called_once_with("metrics")


class TestObservabilityManagerParseMetrics:
    """Tests for parse_prometheus_metrics method."""

    @pytest.mark.unit
    def test_parse_prometheus_metrics_counter(self, manager: ObservabilityManager) -> None:
        """Should parse counter metrics correctly."""
        raw_text = """# HELP kong_http_requests_total Total HTTP requests
# TYPE kong_http_requests_total counter
kong_http_requests_total 1234"""

        metrics = manager.parse_prometheus_metrics(raw_text)

        assert len(metrics) == 1
        assert metrics[0].name == "kong_http_requests_total"
        assert metrics[0].value == 1234
        assert metrics[0].type == "counter"
        assert "Total HTTP requests" in (metrics[0].help_text or "")

    @pytest.mark.unit
    def test_parse_prometheus_metrics_gauge(self, manager: ObservabilityManager) -> None:
        """Should parse gauge metrics correctly."""
        raw_text = """# TYPE kong_memory_lua_shared_dict_bytes gauge
kong_memory_lua_shared_dict_bytes 12345678"""

        metrics = manager.parse_prometheus_metrics(raw_text)

        assert len(metrics) == 1
        assert metrics[0].type == "gauge"
        assert metrics[0].value == 12345678

    @pytest.mark.unit
    def test_parse_prometheus_metrics_histogram(self, manager: ObservabilityManager) -> None:
        """Should parse histogram bucket metrics."""
        raw_text = """# TYPE kong_request_latency_ms histogram
kong_request_latency_ms_bucket{le="10"} 50
kong_request_latency_ms_bucket{le="100"} 100
kong_request_latency_ms_bucket{le="+Inf"} 150"""

        metrics = manager.parse_prometheus_metrics(raw_text)

        assert len(metrics) == 3
        assert all("bucket" in m.name for m in metrics)

    @pytest.mark.unit
    def test_parse_prometheus_metrics_with_labels(self, manager: ObservabilityManager) -> None:
        """Should parse metrics with labels."""
        raw_text = """kong_http_requests_total{service="api",route="my-route",code="200"} 100"""

        metrics = manager.parse_prometheus_metrics(raw_text)

        assert len(metrics) == 1
        assert metrics[0].labels.get("service") == "api"
        assert metrics[0].labels.get("route") == "my-route"
        assert metrics[0].labels.get("code") == "200"

    @pytest.mark.unit
    def test_parse_prometheus_metrics_help_line(self, manager: ObservabilityManager) -> None:
        """Should parse HELP lines."""
        raw_text = """# HELP kong_http_requests_total HTTP requests processed
# TYPE kong_http_requests_total counter
kong_http_requests_total 100"""

        metrics = manager.parse_prometheus_metrics(raw_text)

        assert metrics[0].help_text == "HTTP requests processed"

    @pytest.mark.unit
    def test_parse_prometheus_metrics_type_line(self, manager: ObservabilityManager) -> None:
        """Should parse TYPE lines."""
        raw_text = """# TYPE kong_nginx_connections_total gauge
kong_nginx_connections_total 50"""

        metrics = manager.parse_prometheus_metrics(raw_text)

        assert metrics[0].type == "gauge"


class TestObservabilityManagerParseMetricLine:
    """Tests for _parse_metric_line method."""

    @pytest.mark.unit
    def test_parse_metric_line_with_labels(self, manager: ObservabilityManager) -> None:
        """Should parse metric line with labels."""
        line = 'kong_http_requests_total{service="api",code="200"} 100'

        metric = manager._parse_metric_line(line, "help", "counter")

        assert metric is not None
        assert metric.name == "kong_http_requests_total"
        assert metric.value == 100
        assert metric.labels == {"service": "api", "code": "200"}

    @pytest.mark.unit
    def test_parse_metric_line_without_labels(self, manager: ObservabilityManager) -> None:
        """Should parse metric line without labels."""
        line = "kong_http_requests_total 100"

        metric = manager._parse_metric_line(line, "", "counter")

        assert metric is not None
        assert metric.name == "kong_http_requests_total"
        assert metric.value == 100
        assert metric.labels == {}

    @pytest.mark.unit
    def test_parse_metric_line_nan_value(self, manager: ObservabilityManager) -> None:
        """Should handle NaN values."""
        line = "kong_some_metric NaN"

        metric = manager._parse_metric_line(line, "", "gauge")

        # NaN should fail float conversion, returning None
        assert metric is None or (metric is not None and metric.value != metric.value)

    @pytest.mark.unit
    def test_parse_metric_line_inf_value(self, manager: ObservabilityManager) -> None:
        """Should handle Inf values."""
        line = "kong_some_metric +Inf"

        metric = manager._parse_metric_line(line, "", "gauge")

        assert metric is not None
        assert metric.value == float("inf")

    @pytest.mark.unit
    def test_parse_metric_line_invalid(self, manager: ObservabilityManager) -> None:
        """Should return None for invalid lines."""
        line = "this is not a valid metric line"

        metric = manager._parse_metric_line(line, "", "")

        assert metric is None


class TestObservabilityManagerMetricsSummary:
    """Tests for get_metrics_summary method."""

    @pytest.mark.unit
    def test_get_metrics_summary_success(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should aggregate metrics into summary."""
        mock_client.get.return_value = {
            "raw": """# TYPE kong_http_requests_total counter
kong_http_requests_total{service="api",code="200"} 100
kong_http_requests_total{service="api",code="500"} 5
kong_request_latency_ms_sum 5000
kong_request_latency_ms_count 100"""
        }

        summary = manager.get_metrics_summary()

        assert summary.total_requests == 105
        assert summary.requests_per_status.get("200") == 100
        assert summary.requests_per_status.get("500") == 5
        assert summary.latency_avg_ms == 50.0

    @pytest.mark.unit
    def test_get_metrics_summary_with_service_filter(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should filter by service."""
        mock_client.get.return_value = {
            "raw": """kong_http_requests_total{service="api"} 100
kong_http_requests_total{service="other"} 50"""
        }

        summary = manager.get_metrics_summary(service_filter="api")

        assert summary.total_requests == 100

    @pytest.mark.unit
    def test_get_metrics_summary_with_route_filter(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should filter by route."""
        mock_client.get.return_value = {
            "raw": """kong_http_requests_total{route="route-1"} 100
kong_http_requests_total{route="route-2"} 50"""
        }

        summary = manager.get_metrics_summary(route_filter="route-1")

        assert summary.total_requests == 100

    @pytest.mark.unit
    def test_get_metrics_summary_metrics_unavailable(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should return empty summary when metrics unavailable."""
        mock_client.get.side_effect = Exception("Metrics endpoint not available")

        summary = manager.get_metrics_summary()

        assert summary.total_requests == 0


class TestObservabilityManagerListMetrics:
    """Tests for list_metrics method."""

    @pytest.mark.unit
    def test_list_metrics_all(self, manager: ObservabilityManager, mock_client: MagicMock) -> None:
        """Should list all metrics."""
        mock_client.get.return_value = {
            "raw": """kong_http_requests_total 100
kong_nginx_connections_total 50"""
        }

        metrics = manager.list_metrics()

        assert len(metrics) == 2

    @pytest.mark.unit
    def test_list_metrics_name_filter(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should filter by name pattern."""
        mock_client.get.return_value = {
            "raw": """kong_http_requests_total 100
kong_nginx_connections_total 50"""
        }

        metrics = manager.list_metrics(name_filter="http")

        assert len(metrics) == 1
        assert "http" in metrics[0].name

    @pytest.mark.unit
    def test_list_metrics_type_filter(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should filter by type."""
        mock_client.get.return_value = {
            "raw": """# TYPE kong_http_requests_total counter
kong_http_requests_total 100
# TYPE kong_connections gauge
kong_connections 50"""
        }

        metrics = manager.list_metrics(type_filter="counter")

        assert len(metrics) == 1
        assert metrics[0].type == "counter"


class TestObservabilityManagerNodeStatus:
    """Tests for get_node_status method."""

    @pytest.mark.unit
    def test_get_node_status_success(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should return node status."""
        mock_client.get_status.return_value = {
            "database": {"reachable": True},
            "memory": {"workers_lua_vms": {"worker_1": {"allocated": 1048576}}},
            "server": {
                "connections_active": 10,
                "connections_reading": 1,
                "connections_writing": 2,
                "connections_waiting": 7,
                "connections_accepted": 100,
                "connections_handled": 100,
                "total_requests": 1000,
            },
        }

        status = manager.get_node_status()

        assert status.database_reachable is True
        assert status.server_connections_active == 10
        assert status.server_total_requests == 1000

    @pytest.mark.unit
    def test_get_node_status_database_reachable(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should detect database reachability."""
        mock_client.get_status.return_value = {
            "database": {"reachable": True},
            "memory": {},
            "server": {},
        }

        status = manager.get_node_status()

        assert status.database_reachable is True

    @pytest.mark.unit
    def test_get_node_status_memory_stats(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should include memory statistics."""
        mock_client.get_status.return_value = {
            "database": {},
            "memory": {
                "workers_lua_vms": {"worker_1": {"http_allocated_gc": 1024}},
                "lua_shared_dicts": {"kong": {"allocated_slabs": 2048}},
            },
            "server": {},
        }

        status = manager.get_node_status()

        assert status.memory_workers_lua_vms is not None
        assert status.memory_lua_shared_dicts is not None

    @pytest.mark.unit
    def test_get_node_status_server_connections(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should include server connection stats."""
        mock_client.get_status.return_value = {
            "database": {},
            "memory": {},
            "server": {
                "connections_active": 5,
                "connections_reading": 1,
                "connections_writing": 2,
                "connections_waiting": 2,
            },
        }

        status = manager.get_node_status()

        assert status.server_connections_active == 5
        assert status.server_connections_reading == 1


class TestObservabilityManagerUpstreamHealth:
    """Tests for get_upstream_health method."""

    @pytest.mark.unit
    def test_get_upstream_health_all_healthy(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should return healthy summary when all targets healthy."""
        mock_client.get.side_effect = [
            {"data": {"health": "HEALTHY"}},  # health endpoint
            {
                "data": [
                    {"target": "192.168.1.1:8080", "weight": 100, "health": "HEALTHY"},
                    {"target": "192.168.1.2:8080", "weight": 100, "health": "HEALTHY"},
                ]
            },  # targets
        ]

        health = manager.get_upstream_health("my-upstream")

        assert health.overall_health == "HEALTHY"
        assert health.total_targets == 2
        assert health.healthy_targets == 2
        assert health.unhealthy_targets == 0

    @pytest.mark.unit
    def test_get_upstream_health_some_unhealthy(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should count unhealthy targets."""
        mock_client.get.side_effect = [
            {"data": {"health": "UNHEALTHY"}},
            {
                "data": [
                    {"target": "192.168.1.1:8080", "weight": 100, "health": "HEALTHY"},
                    {"target": "192.168.1.2:8080", "weight": 100, "health": "UNHEALTHY"},
                ]
            },
        ]

        health = manager.get_upstream_health("my-upstream")

        assert health.healthy_targets == 1
        assert health.unhealthy_targets == 1

    @pytest.mark.unit
    def test_get_upstream_health_dns_error(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should handle DNS_ERROR health status."""
        mock_client.get.side_effect = [
            {"data": {"health": "DNS_ERROR"}},
            {
                "data": [
                    {"target": "bad.dns.name:8080", "weight": 100, "health": "DNS_ERROR"},
                ]
            },
        ]

        health = manager.get_upstream_health("my-upstream")

        assert len(health.targets) == 1
        assert health.targets[0].health == "DNS_ERROR"

    @pytest.mark.unit
    def test_get_upstream_health_healthchecks_off(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should handle HEALTHCHECKS_OFF status."""
        mock_client.get.side_effect = [
            {"data": {"health": "HEALTHCHECKS_OFF"}},
            {
                "data": [
                    {"target": "192.168.1.1:8080", "weight": 100},
                ]
            },
        ]

        health = manager.get_upstream_health("my-upstream")

        assert health.overall_health == "HEALTHCHECKS_OFF"


class TestObservabilityManagerListUpstreamsHealth:
    """Tests for list_upstreams_health method."""

    @pytest.mark.unit
    def test_list_upstreams_health_success(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should list health for all upstreams."""
        mock_client.get.side_effect = [
            {"data": [{"name": "upstream-1"}, {"name": "upstream-2"}]},
            {"data": {"health": "HEALTHY"}},
            {"data": []},
            {"data": {"health": "UNHEALTHY"}},
            {"data": []},
        ]

        summaries = manager.list_upstreams_health()

        assert len(summaries) == 2

    @pytest.mark.unit
    def test_list_upstreams_health_partial_failure(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should handle partial failures gracefully."""

        def get_side_effect(endpoint: str) -> dict[str, Any]:
            if endpoint == "upstreams":
                return {"data": [{"name": "up-1"}, {"name": "up-2"}]}
            if "up-1" in endpoint:
                return {"data": {"health": "HEALTHY"}} if "health" in endpoint else {"data": []}
            raise Exception("Failed to get health")

        mock_client.get.side_effect = get_side_effect

        summaries = manager.list_upstreams_health()

        # Should have at least one successful result
        assert len(summaries) >= 1


class TestObservabilityManagerPercentileMetrics:
    """Tests for get_percentile_metrics method."""

    @pytest.mark.unit
    def test_get_percentile_metrics_success(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should calculate percentiles from histogram buckets."""
        mock_client.get.return_value = {
            "raw": """# TYPE kong_request_latency_ms histogram
kong_request_latency_ms_bucket{le="10"} 50
kong_request_latency_ms_bucket{le="50"} 90
kong_request_latency_ms_bucket{le="100"} 95
kong_request_latency_ms_bucket{le="500"} 99
kong_request_latency_ms_bucket{le="+Inf"} 100"""
        }

        percentiles = manager.get_percentile_metrics()

        assert percentiles.p50_ms is not None
        assert percentiles.p95_ms is not None
        assert percentiles.p99_ms is not None

    @pytest.mark.unit
    def test_get_percentile_metrics_with_filter(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should filter percentiles by service."""
        mock_client.get.return_value = {
            "raw": """kong_request_latency_ms_bucket{service="api",le="10"} 50
kong_request_latency_ms_bucket{service="api",le="+Inf"} 100"""
        }

        percentiles = manager.get_percentile_metrics(service_filter="api")

        assert percentiles.service == "api"

    @pytest.mark.unit
    def test_get_percentile_metrics_unavailable(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should return empty percentiles when metrics unavailable."""
        mock_client.get.side_effect = Exception("Metrics not available")

        percentiles = manager.get_percentile_metrics()

        assert percentiles.p50_ms is None
        assert percentiles.p95_ms is None
        assert percentiles.p99_ms is None


class TestObservabilityManagerCalculatePercentile:
    """Tests for _calculate_percentile method."""

    @pytest.mark.unit
    def test_calculate_percentile_empty_buckets(self, manager: ObservabilityManager) -> None:
        """Should return None for empty buckets."""
        result = manager._calculate_percentile({}, 0, 0.50)

        assert result is None

    @pytest.mark.unit
    def test_calculate_percentile_p50(self, manager: ObservabilityManager) -> None:
        """Should calculate P50 correctly."""
        buckets: dict[float, float] = {10.0: 50.0, 50.0: 90.0, 100.0: 100.0}

        result = manager._calculate_percentile(buckets, 100, 0.50)

        assert result is not None
        assert result <= 10.0  # P50 should be at or below the 10ms bucket

    @pytest.mark.unit
    def test_calculate_percentile_p95(self, manager: ObservabilityManager) -> None:
        """Should calculate P95 correctly."""
        buckets: dict[float, float] = {10.0: 50.0, 50.0: 90.0, 100.0: 100.0}

        result = manager._calculate_percentile(buckets, 100, 0.95)

        assert result is not None
        assert result >= 50.0  # P95 should be above the P50 bucket

    @pytest.mark.unit
    def test_calculate_percentile_p99(self, manager: ObservabilityManager) -> None:
        """Should calculate P99 correctly."""
        buckets: dict[float, float] = {10.0: 50.0, 50.0: 90.0, 100.0: 99.0}

        result = manager._calculate_percentile(buckets, 100, 0.99)

        assert result is not None

    @pytest.mark.unit
    def test_calculate_percentile_interpolation(self, manager: ObservabilityManager) -> None:
        """Should interpolate within bucket boundaries."""
        # 75% of observations are at le=100
        buckets: dict[float, float] = {50.0: 50.0, 100.0: 100.0}

        result = manager._calculate_percentile(buckets, 100, 0.75)

        assert result is not None
        # Should be interpolated between 50 and 100
        assert 50.0 < result < 100.0


class TestObservabilityManagerHealthFailures:
    """Tests for get_health_failures method."""

    @pytest.mark.unit
    def test_get_health_failures_unhealthy(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should detect unhealthy targets."""
        mock_client.get.side_effect = [
            {"data": {"health": "UNHEALTHY"}},
            {
                "data": [
                    {"target": "192.168.1.1:8080", "health": "HEALTHY", "weight": 100},
                    {"target": "192.168.1.2:8080", "health": "UNHEALTHY", "weight": 100},
                ]
            },
        ]

        failures = manager.get_health_failures("my-upstream")

        assert len(failures) == 1
        assert failures[0].target == "192.168.1.2:8080"
        assert failures[0].failure_type == "health_check_failed"

    @pytest.mark.unit
    def test_get_health_failures_dns_error(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should detect DNS errors."""
        mock_client.get.side_effect = [
            {"data": {"health": "DNS_ERROR"}},
            {
                "data": [
                    {"target": "bad.host:8080", "health": "DNS_ERROR", "weight": 100},
                ]
            },
        ]

        failures = manager.get_health_failures("my-upstream")

        assert len(failures) == 1
        assert failures[0].failure_type == "dns_error"

    @pytest.mark.unit
    def test_get_health_failures_empty(
        self, manager: ObservabilityManager, mock_client: MagicMock
    ) -> None:
        """Should return empty list when no failures."""
        mock_client.get.side_effect = [
            {"data": {"health": "HEALTHY"}},
            {
                "data": [
                    {"target": "192.168.1.1:8080", "health": "HEALTHY", "weight": 100},
                ]
            },
        ]

        failures = manager.get_health_failures("my-upstream")

        assert len(failures) == 0


class TestObservabilityManagerFailureDetails:
    """Tests for _get_failure_details method."""

    @pytest.mark.unit
    def test_get_failure_details_dns(self, manager: ObservabilityManager) -> None:
        """Should format DNS error details."""
        target = TargetHealthDetail(
            target="bad.host:8080",
            weight=100,
            health="DNS_ERROR",
        )

        details = manager._get_failure_details(target)

        assert "DNS resolution failed" in details

    @pytest.mark.unit
    def test_get_failure_details_unhealthy_addresses(self, manager: ObservabilityManager) -> None:
        """Should list unhealthy addresses."""
        target = TargetHealthDetail(
            target="my-host:8080",
            weight=100,
            health="UNHEALTHY",
            addresses=[
                {"ip": "192.168.1.1", "health": "UNHEALTHY"},
                {"ip": "192.168.1.2", "health": "HEALTHY"},
            ],
        )

        details = manager._get_failure_details(target)

        assert "192.168.1.1" in details
        assert "192.168.1.2" not in details

    @pytest.mark.unit
    def test_get_failure_details_generic(self, manager: ObservabilityManager) -> None:
        """Should provide generic details when no address info."""
        target = TargetHealthDetail(
            target="my-host:8080",
            weight=100,
            health="UNHEALTHY",
        )

        details = manager._get_failure_details(target)

        assert "marked unhealthy" in details
        assert "weight: 100" in details
