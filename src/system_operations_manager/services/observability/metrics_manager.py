"""Metrics manager for Kong observability.

Provides a high-level interface for querying Kong metrics from Prometheus.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

import structlog

if TYPE_CHECKING:
    from system_operations_manager.integrations.observability import (
        PrometheusClient,
        PrometheusConfig,
    )


logger = structlog.get_logger()


class MetricsManager:
    """Manager for Kong metrics queries.

    Provides a simplified interface for common Kong metrics operations
    using Prometheus as the backend.

    Example:
        ```python
        from system_operations_manager.integrations.observability import PrometheusConfig
        from system_operations_manager.services.observability import MetricsManager

        config = PrometheusConfig(url="http://localhost:9090")
        manager = MetricsManager(config)

        # Get request rate for all services
        rates = manager.get_request_rate()

        # Get latency percentiles for a specific service
        latency = manager.get_latency_percentiles(service="my-api")
        ```
    """

    def __init__(self, config: PrometheusConfig) -> None:
        """Initialize metrics manager.

        Args:
            config: Prometheus configuration.
        """
        self.config = config
        self._client: PrometheusClient | None = None

    @property
    def client(self) -> PrometheusClient:
        """Get or create the Prometheus client."""
        if self._client is None:
            from system_operations_manager.integrations.observability import PrometheusClient

            self._client = PrometheusClient(self.config)
        return self._client

    def close(self) -> None:
        """Close the client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> MetricsManager:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def is_available(self) -> bool:
        """Check if Prometheus is available.

        Returns:
            True if Prometheus is healthy and responding.
        """
        try:
            return self.client.health_check()
        except Exception:
            return False

    def get_request_rate(
        self,
        service: str | None = None,
        route: str | None = None,
        time_range: str = "5m",
    ) -> list[dict[str, Any]]:
        """Get Kong HTTP request rate.

        Args:
            service: Filter by service name.
            route: Filter by route name.
            time_range: Rate calculation window (e.g., "5m", "1h").

        Returns:
            List of results with labels and rate values.
        """
        return self.client.get_kong_request_rate(
            service=service,
            route=route,
            time_range=time_range,
        )

    def get_latency_percentiles(
        self,
        service: str | None = None,
        percentiles: list[float] | None = None,
        time_range: str = "5m",
    ) -> dict[float, list[dict[str, Any]]]:
        """Get Kong request latency percentiles.

        Args:
            service: Filter by service name.
            percentiles: Percentiles to calculate (default: p50, p90, p99).
            time_range: Histogram calculation window.

        Returns:
            Dict mapping percentile to results.
        """
        return self.client.get_kong_latency_percentiles(
            service=service,
            percentiles=percentiles,
            time_range=time_range,
        )

    def get_error_rate(
        self,
        service: str | None = None,
        time_range: str = "5m",
    ) -> list[dict[str, Any]]:
        """Get Kong HTTP error rate (4xx + 5xx responses).

        Args:
            service: Filter by service name.
            time_range: Rate calculation window.

        Returns:
            Error rate as fraction of total requests.
        """
        return self.client.get_kong_error_rate(
            service=service,
            time_range=time_range,
        )

    def get_bandwidth(
        self,
        service: str | None = None,
        direction: Literal["ingress", "egress", "both"] = "both",
        time_range: str = "5m",
    ) -> dict[str, list[dict[str, Any]]]:
        """Get Kong bandwidth usage.

        Args:
            service: Filter by service name.
            direction: Traffic direction to query.
            time_range: Rate calculation window.

        Returns:
            Dict with ingress/egress bandwidth in bytes/sec.
        """
        return self.client.get_kong_bandwidth(
            service=service,
            direction=direction,
            time_range=time_range,
        )

    def get_upstream_health(self) -> list[dict[str, Any]]:
        """Get Kong upstream target health status.

        Returns:
            List of upstream targets with health status.
        """
        return self.client.get_kong_upstream_health()

    def query(
        self,
        promql: str,
        time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a custom PromQL query.

        Args:
            promql: PromQL query expression.
            time: Evaluation timestamp (default: now).

        Returns:
            List of query results.
        """
        return self.client.query(promql, time=time)

    def query_range(
        self,
        promql: str,
        start: datetime | None = None,
        end: datetime | None = None,
        step: str = "1m",
    ) -> list[dict[str, Any]]:
        """Execute a custom PromQL range query.

        Args:
            promql: PromQL query expression.
            start: Start timestamp (default: 1 hour ago).
            end: End timestamp (default: now).
            step: Query resolution step.

        Returns:
            List of query results with time series data.
        """
        if end is None:
            end = datetime.now()
        if start is None:
            start = end - timedelta(hours=1)

        return self.client.query_range(promql, start=start, end=end, step=step)

    def get_services(self) -> list[str]:
        """Get list of services with metrics.

        Returns:
            List of service names found in Kong metrics.
        """
        return self.client.get_label_values("service")

    def get_routes(self) -> list[str]:
        """Get list of routes with metrics.

        Returns:
            List of route names found in Kong metrics.
        """
        return self.client.get_label_values("route")

    def get_summary(
        self,
        service: str | None = None,
        time_range: str = "5m",
    ) -> dict[str, Any]:
        """Get a summary of Kong metrics.

        Args:
            service: Filter by service name.
            time_range: Time range for calculations.

        Returns:
            Summary dict with request rate, error rate, and latency.
        """
        summary: dict[str, Any] = {}

        # Get request rate
        request_rates = self.get_request_rate(service=service, time_range=time_range)
        if request_rates:
            total_rate = sum(
                float(r.get("value", [0, 0])[1]) for r in request_rates if r.get("value")
            )
            summary["request_rate_per_second"] = total_rate
        else:
            summary["request_rate_per_second"] = 0.0

        # Get error rate
        error_rates = self.get_error_rate(service=service, time_range=time_range)
        if error_rates and error_rates[0].get("value"):
            error_value = error_rates[0]["value"]
            if len(error_value) > 1:
                summary["error_rate"] = float(error_value[1])
            else:
                summary["error_rate"] = 0.0
        else:
            summary["error_rate"] = 0.0

        # Get latency percentiles
        latencies = self.get_latency_percentiles(service=service, time_range=time_range)
        latency_summary = {}
        for percentile, results in latencies.items():
            if results and results[0].get("value"):
                value = results[0]["value"]
                if len(value) > 1:
                    latency_summary[f"p{int(percentile * 100)}"] = float(value[1])
        summary["latency_ms"] = latency_summary

        return summary
