"""Observability manager for Kong metrics, health, and status.

This module provides the ObservabilityManager class for fetching and parsing
observability data from Kong's Admin API and metrics endpoints.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient

from system_operations_manager.integrations.kong.models.observability import (
    MetricsSummary,
    NodeStatus,
    PrometheusMetric,
    TargetHealthDetail,
    UpstreamHealthSummary,
)

logger = structlog.get_logger()


class ObservabilityManager:
    """Manager for Kong observability data.

    Provides methods to fetch and parse:
    - Prometheus metrics from /metrics endpoint
    - Node status from /status endpoint
    - Upstream health from /upstreams/{name}/health

    Example:
        >>> manager = ObservabilityManager(client)
        >>> summary = manager.get_metrics_summary()
        >>> health = manager.get_upstream_health("my-upstream")
    """

    def __init__(self, client: KongAdminClient) -> None:
        """Initialize the observability manager.

        Args:
            client: Kong Admin API client instance.
        """
        self._client = client
        self._log = logger.bind(service="observability")

    # =========================================================================
    # Prometheus Metrics
    # =========================================================================

    def get_raw_metrics(self) -> str:
        """Fetch raw Prometheus metrics text from Kong.

        Kong exposes metrics at /metrics when the prometheus plugin is enabled.

        Returns:
            Raw Prometheus exposition format text.

        Raises:
            KongAPIError: If metrics endpoint is not available.
        """
        self._log.debug("fetching_raw_metrics")
        # The response will be in {"raw": "..."} format for non-JSON responses
        response = self._client.get("metrics")
        return str(response.get("raw", ""))

    def parse_prometheus_metrics(self, raw_text: str) -> list[PrometheusMetric]:
        """Parse Prometheus exposition format into metric objects.

        Args:
            raw_text: Raw Prometheus metrics text.

        Returns:
            List of parsed PrometheusMetric objects.
        """
        metrics: list[PrometheusMetric] = []
        current_help = ""
        current_type = "untyped"

        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Parse HELP lines
            if line.startswith("# HELP "):
                parts = line[7:].split(" ", 1)
                current_help = parts[1] if len(parts) > 1 else ""
                continue

            # Parse TYPE lines
            if line.startswith("# TYPE "):
                parts = line[7:].split(" ", 1)
                current_type = parts[1] if len(parts) > 1 else "untyped"
                continue

            # Skip other comments
            if line.startswith("#"):
                continue

            # Parse metric line: name{labels} value
            metric = self._parse_metric_line(line, current_help, current_type)
            if metric:
                metrics.append(metric)

        return metrics

    def _parse_metric_line(
        self,
        line: str,
        help_text: str,
        metric_type: str,
    ) -> PrometheusMetric | None:
        """Parse a single Prometheus metric line.

        Args:
            line: Metric line (e.g., 'kong_http_requests_total{service="api"} 1234').
            help_text: HELP text from previous line.
            metric_type: TYPE from previous line.

        Returns:
            PrometheusMetric or None if parsing fails.
        """
        # Match: metric_name{label="value",...} value
        # Or: metric_name value (no labels)
        match = re.match(
            r"^([a-zA-Z_:][a-zA-Z0-9_:]*)\{?(.*?)\}?\s+([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?|NaN|[+-]Inf)$",
            line,
        )
        if not match:
            return None

        name = match.group(1)
        labels_str = match.group(2)
        value_str = match.group(3)

        # Parse labels
        labels: dict[str, str] = {}
        if labels_str:
            for label_match in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"', labels_str):
                labels[label_match.group(1)] = label_match.group(2)

        # Parse value
        try:
            value = float(value_str)
        except ValueError:
            return None

        return PrometheusMetric(
            name=name,
            help_text=help_text if help_text else None,
            type=metric_type,  # type: ignore[arg-type]
            labels=labels,
            value=value,
        )

    def get_metrics_summary(
        self,
        service_filter: str | None = None,
        route_filter: str | None = None,
    ) -> MetricsSummary:
        """Get aggregated metrics summary.

        Fetches Prometheus metrics and aggregates them into a summary view
        suitable for CLI display.

        Args:
            service_filter: Filter metrics to specific service.
            route_filter: Filter metrics to specific route.

        Returns:
            MetricsSummary with aggregated data.
        """
        self._log.debug(
            "getting_metrics_summary",
            service=service_filter,
            route=route_filter,
        )

        try:
            raw_metrics = self.get_raw_metrics()
            metrics = self.parse_prometheus_metrics(raw_metrics)
        except Exception as e:
            self._log.warning("metrics_not_available", error=str(e))
            return MetricsSummary()

        summary = MetricsSummary()
        latency_sum = 0.0
        latency_count = 0

        for metric in metrics:
            # Filter by service/route if specified
            if service_filter and metric.labels.get("service") != service_filter:
                continue
            if route_filter and metric.labels.get("route") != route_filter:
                continue

            # Aggregate request counts
            if metric.name == "kong_http_requests_total" and metric.value is not None:
                summary.total_requests += int(metric.value)
                status = metric.labels.get("code", "unknown")
                summary.requests_per_status[status] = summary.requests_per_status.get(
                    status, 0
                ) + int(metric.value)
                service = metric.labels.get("service", "unknown")
                summary.requests_per_service[service] = summary.requests_per_service.get(
                    service, 0
                ) + int(metric.value)

            # Latency metrics (from histogram)
            if metric.name == "kong_request_latency_ms_sum" and metric.value is not None:
                latency_sum += metric.value
            if metric.name == "kong_request_latency_ms_count" and metric.value is not None:
                latency_count += int(metric.value)

            # Connection stats
            if metric.name == "kong_nginx_connections_total" and metric.value is not None:
                state = metric.labels.get("state", "")
                if state == "active":
                    summary.connections_active = int(metric.value)
                elif state == "total" or state == "accepted":
                    summary.connections_total = int(metric.value)

        # Calculate average latency
        if latency_count > 0:
            summary.latency_avg_ms = latency_sum / latency_count

        return summary

    def list_metrics(
        self,
        name_filter: str | None = None,
        type_filter: str | None = None,
    ) -> list[PrometheusMetric]:
        """List all available metrics with optional filtering.

        Args:
            name_filter: Regex pattern to filter metric names.
            type_filter: Filter by metric type (counter, gauge, histogram, summary).

        Returns:
            List of matching PrometheusMetric objects.
        """
        self._log.debug(
            "listing_metrics",
            name_filter=name_filter,
            type_filter=type_filter,
        )

        raw_metrics = self.get_raw_metrics()
        metrics = self.parse_prometheus_metrics(raw_metrics)

        filtered = []
        for metric in metrics:
            if name_filter and not re.search(name_filter, metric.name):
                continue
            if type_filter and metric.type != type_filter:
                continue
            filtered.append(metric)

        return filtered

    # =========================================================================
    # Node Status
    # =========================================================================

    def get_node_status(self) -> NodeStatus:
        """Get Kong node status from /status endpoint.

        Returns:
            NodeStatus with server and memory statistics.
        """
        self._log.debug("getting_node_status")
        status_data = self._client.get_status()

        database = status_data.get("database", {})
        memory = status_data.get("memory", {})
        server = status_data.get("server", {})

        return NodeStatus(
            database_reachable=database.get("reachable", False),
            memory_workers_lua_vms=memory.get("workers_lua_vms"),
            memory_lua_shared_dicts=memory.get("lua_shared_dicts"),
            server_connections_active=server.get("connections_active", 0),
            server_connections_reading=server.get("connections_reading", 0),
            server_connections_writing=server.get("connections_writing", 0),
            server_connections_waiting=server.get("connections_waiting", 0),
            server_connections_accepted=server.get("connections_accepted", 0),
            server_connections_handled=server.get("connections_handled", 0),
            server_total_requests=server.get("total_requests", 0),
        )

    # =========================================================================
    # Upstream Health
    # =========================================================================

    def get_upstream_health(self, upstream_name: str) -> UpstreamHealthSummary:
        """Get health summary for an upstream.

        Args:
            upstream_name: Upstream ID or name.

        Returns:
            UpstreamHealthSummary with target health details.
        """
        self._log.debug("getting_upstream_health", upstream=upstream_name)

        # Get upstream health status
        health_data = self._client.get(f"upstreams/{upstream_name}/health")

        # Get all targets with health info
        targets_data = self._client.get(f"upstreams/{upstream_name}/targets/all")

        targets: list[TargetHealthDetail] = []
        healthy_count = 0
        unhealthy_count = 0

        for target_info in targets_data.get("data", []):
            health = target_info.get("health", "HEALTHCHECKS_OFF")
            target = TargetHealthDetail(
                target=target_info.get("target", "unknown"),
                weight=target_info.get("weight", 100),
                health=health,
                addresses=target_info.get("data", {}).get("addresses"),
            )
            targets.append(target)

            if health == "HEALTHY":
                healthy_count += 1
            elif health == "UNHEALTHY":
                unhealthy_count += 1

        overall_health = health_data.get("data", {}).get("health", "HEALTHCHECKS_OFF")

        return UpstreamHealthSummary(
            upstream_name=upstream_name,
            overall_health=overall_health,
            total_targets=len(targets),
            healthy_targets=healthy_count,
            unhealthy_targets=unhealthy_count,
            targets=targets,
        )

    def list_upstreams_health(self) -> list[UpstreamHealthSummary]:
        """Get health summary for all upstreams.

        Returns:
            List of UpstreamHealthSummary for each upstream.
        """
        self._log.debug("listing_all_upstreams_health")

        # First list all upstreams
        upstreams_response = self._client.get("upstreams")
        summaries = []

        for upstream in upstreams_response.get("data", []):
            name = upstream.get("name") or upstream.get("id")
            if name:
                try:
                    summary = self.get_upstream_health(name)
                    summaries.append(summary)
                except Exception as e:
                    self._log.warning(
                        "failed_to_get_upstream_health",
                        upstream=name,
                        error=str(e),
                    )

        return summaries
