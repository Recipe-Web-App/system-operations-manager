"""Shared fixtures for Kong observability command tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.models.observability import (
    MetricsSummary,
    NodeStatus,
    PrometheusMetric,
    TargetHealthDetail,
    UpstreamHealthSummary,
)
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity


def _create_mock_entity(data: dict[str, Any]) -> MagicMock:
    """Create a mock entity that behaves like a Pydantic model.

    The formatter calls model_dump() on entities, so we need mocks
    that support this interface.
    """
    mock = MagicMock()
    mock.model_dump.return_value = data
    for key, value in data.items():
        setattr(mock, key, value)
    return mock


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_plugin_manager() -> MagicMock:
    """Create a mock KongPluginManager for observability commands."""
    manager = MagicMock()
    manager.enable.return_value = KongPluginEntity(
        id="plugin-123",
        name="prometheus",
        enabled=True,
        config={},
    )
    manager.list.return_value = []
    manager.disable.return_value = None
    return manager


@pytest.fixture
def mock_upstream_manager() -> MagicMock:
    """Create a mock UpstreamManager."""
    manager = MagicMock()
    return manager


@pytest.fixture
def mock_observability_manager() -> MagicMock:
    """Create a mock ObservabilityManager."""
    manager = MagicMock()

    # Default metrics summary
    manager.get_metrics_summary.return_value = MetricsSummary(
        total_requests=10000,
        requests_per_status={"200": 9500, "404": 400, "500": 100},
        requests_per_service={"api-1": 6000, "api-2": 4000},
        latency_avg_ms=45.5,
        connections_active=150,
        connections_total=50000,
    )

    # Default metrics list
    manager.list_metrics.return_value = [
        PrometheusMetric(
            name="kong_http_requests_total",
            type="counter",
            help_text="Total HTTP requests",
            labels={"service": "api-1", "code": "200"},
            value=5000.0,
        ),
        PrometheusMetric(
            name="kong_http_requests_total",
            type="counter",
            help_text="Total HTTP requests",
            labels={"service": "api-2", "code": "200"},
            value=4500.0,
        ),
    ]

    # Default node status
    manager.get_node_status.return_value = NodeStatus(
        database_reachable=True,
        server_connections_active=150,
        server_connections_reading=10,
        server_connections_writing=20,
        server_connections_waiting=120,
        server_connections_accepted=100000,
        server_connections_handled=100000,
        server_total_requests=500000,
    )

    # Default upstream health
    manager.get_upstream_health.return_value = UpstreamHealthSummary(
        upstream_name="test-upstream",
        overall_health="HEALTHY",
        total_targets=3,
        healthy_targets=3,
        unhealthy_targets=0,
        targets=[
            TargetHealthDetail(target="api1:8080", weight=100, health="HEALTHY"),
            TargetHealthDetail(target="api2:8080", weight=100, health="HEALTHY"),
            TargetHealthDetail(target="api3:8080", weight=100, health="HEALTHY"),
        ],
    )

    # Default upstreams health list
    manager.list_upstreams_health.return_value = [
        UpstreamHealthSummary(
            upstream_name="upstream-1",
            overall_health="HEALTHY",
            total_targets=2,
            healthy_targets=2,
            unhealthy_targets=0,
            targets=[],
        ),
        UpstreamHealthSummary(
            upstream_name="upstream-2",
            overall_health="UNHEALTHY",
            total_targets=3,
            healthy_targets=1,
            unhealthy_targets=2,
            targets=[],
        ),
    ]

    return manager


@pytest.fixture
def get_plugin_manager(mock_plugin_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock plugin manager."""
    return lambda: mock_plugin_manager


@pytest.fixture
def get_upstream_manager(mock_upstream_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory function returning the mock upstream manager."""
    return lambda: mock_upstream_manager


@pytest.fixture
def get_observability_manager(
    mock_observability_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory function returning the mock observability manager."""
    return lambda: mock_observability_manager


@pytest.fixture
def sample_prometheus_text() -> str:
    """Sample Prometheus metrics text for parsing tests."""
    return """
# HELP kong_http_requests_total Total number of HTTP requests
# TYPE kong_http_requests_total counter
kong_http_requests_total{service="api-1",code="200"} 5000
kong_http_requests_total{service="api-1",code="404"} 200
kong_http_requests_total{service="api-2",code="200"} 4500
kong_http_requests_total{service="api-2",code="500"} 100

# HELP kong_nginx_connections_total Total number of connections
# TYPE kong_nginx_connections_total gauge
kong_nginx_connections_total{state="active"} 150
kong_nginx_connections_total{state="total"} 50000
"""
