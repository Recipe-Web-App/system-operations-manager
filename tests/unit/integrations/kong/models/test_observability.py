"""Unit tests for Kong observability models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.models.observability import (
    MetricsSummary,
    NodeStatus,
    PrometheusMetric,
    TargetHealthDetail,
    UpstreamHealthSummary,
)


class TestPrometheusMetric:
    """Tests for PrometheusMetric model."""

    @pytest.mark.unit
    def test_create_counter_metric(self) -> None:
        """Should create counter metric with value."""
        metric = PrometheusMetric(
            name="kong_http_requests_total",
            help_text="Total number of HTTP requests",
            type="counter",
            labels={"service": "api", "status": "200"},
            value=1500.0,
        )

        assert metric.name == "kong_http_requests_total"
        assert metric.type == "counter"
        assert metric.labels == {"service": "api", "status": "200"}
        assert metric.value == 1500.0

    @pytest.mark.unit
    def test_create_gauge_metric(self) -> None:
        """Should create gauge metric with value."""
        metric = PrometheusMetric(
            name="kong_nginx_connections_active",
            type="gauge",
            value=42.0,
        )

        assert metric.type == "gauge"
        assert metric.value == 42.0

    @pytest.mark.unit
    def test_create_histogram_metric(self) -> None:
        """Should create histogram metric with buckets."""
        metric = PrometheusMetric(
            name="kong_request_latency_ms",
            type="histogram",
            buckets=[
                {"le": 1.0, "count": 100},
                {"le": 5.0, "count": 150},
                {"le": 10.0, "count": 180},
            ],
        )

        assert metric.type == "histogram"
        assert metric.buckets is not None
        assert len(metric.buckets) == 3

    @pytest.mark.unit
    def test_create_summary_metric(self) -> None:
        """Should create summary metric with quantiles."""
        metric = PrometheusMetric(
            name="kong_request_duration",
            type="summary",
            quantiles=[
                {"quantile": 0.5, "value": 10.5},
                {"quantile": 0.9, "value": 25.3},
                {"quantile": 0.99, "value": 98.7},
            ],
        )

        assert metric.type == "summary"
        assert metric.quantiles is not None
        assert len(metric.quantiles) == 3

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values for optional fields."""
        metric = PrometheusMetric(name="test_metric")

        assert metric.type == "untyped"
        assert metric.labels == {}
        assert metric.value is None
        assert metric.buckets is None
        assert metric.quantiles is None


class TestMetricsSummary:
    """Tests for MetricsSummary model."""

    @pytest.mark.unit
    def test_create_summary(self) -> None:
        """Should create metrics summary."""
        summary = MetricsSummary(
            total_requests=10000,
            requests_per_status={"200": 8000, "404": 500, "500": 100},
            requests_per_service={"api": 7000, "web": 3000},
            latency_avg_ms=15.5,
            latency_p99_ms=120.3,
            connections_active=50,
            connections_total=100000,
        )

        assert summary.total_requests == 10000
        assert summary.requests_per_status["200"] == 8000
        assert summary.latency_avg_ms == 15.5
        assert summary.latency_p99_ms == 120.3

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values."""
        summary = MetricsSummary()

        assert summary.total_requests == 0
        assert summary.requests_per_status == {}
        assert summary.latency_avg_ms is None
        assert summary.connections_active == 0


class TestTargetHealthDetail:
    """Tests for TargetHealthDetail model."""

    @pytest.mark.unit
    def test_create_healthy_target(self) -> None:
        """Should create healthy target."""
        target = TargetHealthDetail(
            target="192.168.1.1:8080",
            weight=100,
            health="HEALTHY",
            addresses=[
                {"ip": "192.168.1.1", "port": 8080, "health": "HEALTHY"},
            ],
        )

        assert target.target == "192.168.1.1:8080"
        assert target.health == "HEALTHY"
        assert target.weight == 100
        assert target.addresses is not None
        assert len(target.addresses) == 1

    @pytest.mark.unit
    def test_create_unhealthy_target(self) -> None:
        """Should create unhealthy target."""
        target = TargetHealthDetail(
            target="backend.example.com:8080",
            health="UNHEALTHY",
        )

        assert target.health == "UNHEALTHY"

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values."""
        target = TargetHealthDetail(target="localhost:8080")

        assert target.weight == 100
        assert target.health == "HEALTHCHECKS_OFF"
        assert target.addresses is None


class TestUpstreamHealthSummary:
    """Tests for UpstreamHealthSummary model."""

    @pytest.mark.unit
    def test_create_summary_with_targets(self) -> None:
        """Should create summary with target details."""
        targets = [
            TargetHealthDetail(target="192.168.1.1:8080", health="HEALTHY"),
            TargetHealthDetail(target="192.168.1.2:8080", health="HEALTHY"),
            TargetHealthDetail(target="192.168.1.3:8080", health="UNHEALTHY"),
        ]

        summary = UpstreamHealthSummary(
            upstream_name="api-upstream",
            overall_health="HEALTHY",
            total_targets=3,
            healthy_targets=2,
            unhealthy_targets=1,
            targets=targets,
        )

        assert summary.upstream_name == "api-upstream"
        assert summary.overall_health == "HEALTHY"
        assert summary.total_targets == 3
        assert summary.healthy_targets == 2
        assert summary.unhealthy_targets == 1
        assert len(summary.targets) == 3

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values."""
        summary = UpstreamHealthSummary(upstream_name="test-upstream")

        assert summary.overall_health == "HEALTHCHECKS_OFF"
        assert summary.total_targets == 0
        assert summary.healthy_targets == 0
        assert summary.targets == []


class TestNodeStatus:
    """Tests for NodeStatus model."""

    @pytest.mark.unit
    def test_create_node_status(self) -> None:
        """Should create node status with connection stats."""
        status = NodeStatus(
            database_reachable=True,
            server_connections_active=50,
            server_connections_reading=10,
            server_connections_writing=15,
            server_connections_waiting=25,
            server_connections_accepted=100000,
            server_connections_handled=100000,
            server_total_requests=500000,
        )

        assert status.database_reachable is True
        assert status.server_connections_active == 50
        assert status.server_total_requests == 500000

    @pytest.mark.unit
    def test_create_node_status_with_memory(self) -> None:
        """Should create node status with memory stats."""
        status = NodeStatus(
            database_reachable=True,
            memory_workers_lua_vms={"worker_1": {"allocated": 1048576}},
            memory_lua_shared_dicts={"cache": {"capacity": 5242880, "allocated": 1024000}},
        )

        assert status.memory_workers_lua_vms is not None
        assert status.memory_lua_shared_dicts is not None

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values."""
        status = NodeStatus()

        assert status.database_reachable is False
        assert status.server_connections_active == 0
        assert status.memory_workers_lua_vms is None
