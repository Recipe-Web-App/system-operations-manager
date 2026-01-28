"""Pydantic models for Kong Observability data.

This module provides models for Prometheus metrics, health status,
node statistics, and observability plugin configurations.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field

from system_operations_manager.integrations.kong.models.base import KongEntityBase

# Prometheus metric types
MetricType = Literal["counter", "gauge", "histogram", "summary", "untyped"]

# Health status values
HealthStatus = Literal["HEALTHY", "UNHEALTHY", "DNS_ERROR", "HEALTHCHECKS_OFF"]


class PrometheusMetric(KongEntityBase):
    """A single Prometheus metric with its values.

    Represents a parsed metric from Kong's Prometheus /metrics endpoint.
    Supports counter, gauge, histogram, and summary metric types.

    Attributes:
        name: Metric name (e.g., 'kong_http_requests_total').
        help_text: Metric description from HELP line.
        type: Metric type (counter, gauge, histogram, summary, untyped).
        labels: Label key-value pairs.
        value: Metric value (for counter/gauge).
        buckets: Histogram buckets (for histogram type).
        quantiles: Quantile values (for summary type).
    """

    model_config = ConfigDict(extra="allow")
    _entity_name: ClassVar[str] = "prometheus_metric"

    name: str = Field(description="Metric name")
    help_text: str | None = Field(default=None, description="Metric description")
    type: MetricType = Field(default="untyped", description="Metric type")
    labels: dict[str, str] = Field(default_factory=dict, description="Metric labels")
    value: float | None = Field(default=None, description="Metric value")
    buckets: list[dict[str, float]] | None = Field(default=None, description="Histogram buckets")
    quantiles: list[dict[str, float]] | None = Field(default=None, description="Summary quantiles")


class MetricsSummary(KongEntityBase):
    """Aggregated metrics summary for CLI display.

    Provides a high-level overview of Kong traffic and performance
    suitable for table output.

    Attributes:
        total_requests: Total HTTP requests count.
        requests_per_status: Request counts by HTTP status code.
        requests_per_service: Request counts by service name.
        latency_avg_ms: Average request latency in milliseconds.
        latency_p99_ms: 99th percentile latency in milliseconds.
        connections_active: Current active connections.
        connections_total: Total connections handled.
    """

    model_config = ConfigDict(extra="allow")
    _entity_name: ClassVar[str] = "metrics_summary"

    total_requests: int = Field(default=0, description="Total HTTP requests")
    requests_per_status: dict[str, int] = Field(
        default_factory=dict, description="Requests by HTTP status code"
    )
    requests_per_service: dict[str, int] = Field(
        default_factory=dict, description="Requests by service name"
    )
    latency_avg_ms: float | None = Field(default=None, description="Average latency (ms)")
    latency_p99_ms: float | None = Field(default=None, description="P99 latency (ms)")
    connections_active: int = Field(default=0, description="Active connections")
    connections_total: int = Field(default=0, description="Total connections")


class TargetHealthDetail(KongEntityBase):
    """Detailed health status for an upstream target.

    Provides health information for a single target in an upstream's
    load balancing pool.

    Attributes:
        target: Target address (host:port).
        weight: Load balancing weight.
        health: Health status (HEALTHY, UNHEALTHY, DNS_ERROR, HEALTHCHECKS_OFF).
        addresses: Resolved IP addresses with individual health status.
    """

    model_config = ConfigDict(extra="allow")
    _entity_name: ClassVar[str] = "target_health_detail"

    target: str = Field(description="Target address (host:port)")
    weight: int = Field(default=100, description="Target weight")
    health: str = Field(default="HEALTHCHECKS_OFF", description="Health status")
    addresses: list[dict[str, Any]] | None = Field(
        default=None, description="Resolved IP addresses with health"
    )


class UpstreamHealthSummary(KongEntityBase):
    """Summary of upstream health including all targets.

    Provides an overview of an upstream's health status with
    aggregate counts and detailed target information.

    Attributes:
        upstream_name: Upstream identifier or name.
        overall_health: Overall upstream health status.
        total_targets: Total number of targets.
        healthy_targets: Number of healthy targets.
        unhealthy_targets: Number of unhealthy targets.
        targets: Detailed health for each target.
    """

    model_config = ConfigDict(extra="allow")
    _entity_name: ClassVar[str] = "upstream_health_summary"

    upstream_name: str = Field(description="Upstream name or ID")
    overall_health: str = Field(default="HEALTHCHECKS_OFF", description="Overall health")
    total_targets: int = Field(default=0, description="Total targets")
    healthy_targets: int = Field(default=0, description="Healthy targets")
    unhealthy_targets: int = Field(default=0, description="Unhealthy targets")
    targets: list[TargetHealthDetail] = Field(
        default_factory=list, description="Target health details"
    )


class NodeStatus(KongEntityBase):
    """Kong node status from /status endpoint.

    Provides server statistics and database connectivity information
    for a Kong node.

    Attributes:
        database_reachable: Whether database is reachable.
        memory_workers_lua_vms: Memory stats for Lua VMs per worker.
        memory_lua_shared_dicts: Shared dictionary memory usage.
        server_connections_active: Current active connections.
        server_connections_reading: Connections being read.
        server_connections_writing: Connections being written.
        server_connections_waiting: Idle keepalive connections.
        server_connections_accepted: Total accepted connections.
        server_connections_handled: Total handled connections.
        server_total_requests: Total requests served.
    """

    model_config = ConfigDict(extra="allow")
    _entity_name: ClassVar[str] = "node_status"

    database_reachable: bool = Field(default=False, description="Database connectivity")
    memory_workers_lua_vms: dict[str, Any] | None = Field(
        default=None, description="Lua VM memory per worker"
    )
    memory_lua_shared_dicts: dict[str, Any] | None = Field(
        default=None, description="Shared dictionary memory"
    )
    server_connections_active: int = Field(default=0, description="Active connections")
    server_connections_reading: int = Field(default=0, description="Connections being read")
    server_connections_writing: int = Field(default=0, description="Connections being written")
    server_connections_waiting: int = Field(default=0, description="Idle keepalive connections")
    server_connections_accepted: int = Field(default=0, description="Total accepted connections")
    server_connections_handled: int = Field(default=0, description="Total handled connections")
    server_total_requests: int = Field(default=0, description="Total requests served")
