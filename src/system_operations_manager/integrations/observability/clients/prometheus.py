"""Prometheus Query API client.

Provides methods to query Prometheus for Kong metrics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

import httpx
import structlog

from system_operations_manager.integrations.observability.clients.base import (
    BaseObservabilityClient,
    ObservabilityClientError,
)
from system_operations_manager.integrations.observability.config import PrometheusConfig

logger = structlog.get_logger()


class PrometheusQueryError(ObservabilityClientError):
    """Raised when a Prometheus query fails."""


class PrometheusClient(BaseObservabilityClient):
    """Client for Prometheus Query API.

    Provides methods to query Kong metrics from Prometheus,
    including instant queries, range queries, and metadata.

    Example:
        ```python
        from system_operations_manager.integrations.observability.config import PrometheusConfig
        from system_operations_manager.integrations.observability.clients import PrometheusClient

        config = PrometheusConfig(url="http://localhost:9090")
        with PrometheusClient(config) as client:
            result = client.query("kong_http_requests_total")
            print(result)
        ```
    """

    def __init__(self, config: PrometheusConfig) -> None:
        """Initialize Prometheus client.

        Args:
            config: Prometheus configuration.
        """
        super().__init__(
            base_url=config.url,
            timeout=config.timeout,
        )
        self.config = config
        self._auth_config = (
            (config.username, config.password)
            if config.auth_type == "basic" and config.username and config.password
            else None
        )
        self._token = config.token if config.auth_type == "bearer" else None

    @property
    def client_name(self) -> str:
        """Return the client name for logging."""
        return "Prometheus"

    def _build_client(self, **kwargs: Any) -> httpx.Client:
        """Build httpx client with Prometheus-specific configuration."""
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        return httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            auth=self._auth_config,
            headers=headers if headers else None,
            **kwargs,
        )

    def health_check(self) -> bool:
        """Check if Prometheus is healthy.

        Returns:
            True if Prometheus is healthy.
        """
        try:
            response = self._make_retry_request("GET", "/-/healthy")
            return bool(response.status_code == 200)
        except ObservabilityClientError:
            return False

    def _parse_query_response(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse Prometheus query response.

        Args:
            data: Raw Prometheus response.

        Returns:
            List of result items.

        Raises:
            PrometheusQueryError: If query failed.
        """
        if data.get("status") != "success":
            error = data.get("error", "Unknown error")
            raise PrometheusQueryError(f"Query failed: {error}")

        result_data = data.get("data", {})
        return cast(list[dict[str, Any]], result_data.get("result", []))

    def query(
        self,
        query: str,
        time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Execute an instant query.

        Args:
            query: PromQL query expression.
            time: Evaluation timestamp (default: now).

        Returns:
            List of query results with labels and values.

        Example:
            ```python
            # Get current request rate
            results = client.query('rate(kong_http_requests_total[5m])')
            for result in results:
                print(result['metric'], result['value'])
            ```
        """
        params: dict[str, Any] = {"query": query}
        if time:
            params["time"] = time.timestamp()

        logger.debug("Prometheus instant query", query=query)
        data = self.get("/api/v1/query", params=params)
        return self._parse_query_response(data)

    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime | None = None,
        step: str = "15s",
    ) -> list[dict[str, Any]]:
        """Execute a range query.

        Args:
            query: PromQL query expression.
            start: Start timestamp.
            end: End timestamp (default: now).
            step: Query resolution step (e.g., "15s", "1m", "1h").

        Returns:
            List of query results with labels and time series values.

        Example:
            ```python
            # Get request rate over last hour
            from datetime import datetime, timedelta
            end = datetime.now()
            start = end - timedelta(hours=1)
            results = client.query_range(
                'rate(kong_http_requests_total[5m])',
                start=start,
                end=end,
                step="1m"
            )
            ```
        """
        if end is None:
            end = datetime.now()

        params = {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        }

        logger.debug("Prometheus range query", query=query, start=start, end=end)
        data = self.get("/api/v1/query_range", params=params)
        return self._parse_query_response(data)

    def get_targets(
        self,
        state: Literal["active", "dropped", "any"] = "any",
    ) -> dict[str, list[dict[str, Any]]]:
        """Get scrape targets.

        Args:
            state: Filter by target state.

        Returns:
            Dict with 'activeTargets' and 'droppedTargets' lists.
        """
        params = {}
        if state != "any":
            params["state"] = state

        data = self.get("/api/v1/targets", params=params)
        return cast(dict[str, list[dict[str, Any]]], data.get("data", {}))

    def get_labels(self) -> list[str]:
        """Get all label names.

        Returns:
            List of label names.
        """
        data = self.get("/api/v1/labels")
        if data.get("status") != "success":
            return []
        return cast(list[str], data.get("data", []))

    def get_label_values(self, label_name: str) -> list[str]:
        """Get values for a specific label.

        Args:
            label_name: Name of the label.

        Returns:
            List of label values.
        """
        data = self.get(f"/api/v1/label/{label_name}/values")
        if data.get("status") != "success":
            return []
        return cast(list[str], data.get("data", []))

    def get_series(
        self,
        match: list[str],
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, str]]:
        """Find series matching label selectors.

        Args:
            match: List of series selectors (e.g., ['kong_http_requests_total']).
            start: Start time for search.
            end: End time for search.

        Returns:
            List of matching series label sets.
        """
        params: dict[str, Any] = {"match[]": match}
        if start:
            params["start"] = start.timestamp()
        if end:
            params["end"] = end.timestamp()

        data = self.get("/api/v1/series", params=params)
        if data.get("status") != "success":
            return []
        return cast(list[dict[str, str]], data.get("data", []))

    def get_metadata(self, metric: str | None = None) -> dict[str, list[dict[str, str]]]:
        """Get metric metadata.

        Args:
            metric: Optional metric name to filter.

        Returns:
            Dict mapping metric names to their metadata.
        """
        params = {}
        if metric:
            params["metric"] = metric

        data = self.get("/api/v1/metadata", params=params)
        if data.get("status") != "success":
            return {}
        return cast(dict[str, list[dict[str, str]]], data.get("data", {}))

    # Kong-specific convenience methods

    def get_kong_request_rate(
        self,
        service: str | None = None,
        route: str | None = None,
        time_range: str = "5m",
    ) -> list[dict[str, Any]]:
        """Get Kong HTTP request rate.

        Args:
            service: Filter by service name.
            route: Filter by route name.
            time_range: Rate calculation window.

        Returns:
            Request rate per second grouped by labels.
        """
        labels = []
        if service:
            labels.append(f'service="{service}"')
        if route:
            labels.append(f'route="{route}"')

        selector = ""
        if labels:
            selector = "{" + ",".join(labels) + "}"

        query = f"rate(kong_http_requests_total{selector}[{time_range}])"
        return self.query(query)

    def get_kong_latency_percentiles(
        self,
        service: str | None = None,
        percentiles: list[float] | None = None,
        time_range: str = "5m",
    ) -> dict[float, list[dict[str, Any]]]:
        """Get Kong request latency percentiles.

        Args:
            service: Filter by service name.
            percentiles: Percentiles to calculate (default: [0.5, 0.9, 0.99]).
            time_range: Histogram calculation window.

        Returns:
            Dict mapping percentile to results.
        """
        if percentiles is None:
            percentiles = [0.5, 0.9, 0.99]

        selector = ""
        if service:
            selector = f'{{service="{service}"}}'

        results = {}
        for p in percentiles:
            query = f"histogram_quantile({p}, rate(kong_request_latency_ms_bucket{selector}[{time_range}]))"
            results[p] = self.query(query)

        return results

    def get_kong_upstream_health(self) -> list[dict[str, Any]]:
        """Get Kong upstream health status.

        Returns:
            List of upstream targets with health status.
        """
        return self.query("kong_upstream_target_health")

    def get_kong_error_rate(
        self,
        service: str | None = None,
        time_range: str = "5m",
    ) -> list[dict[str, Any]]:
        """Get Kong HTTP error rate (4xx + 5xx).

        Args:
            service: Filter by service name.
            time_range: Rate calculation window.

        Returns:
            Error rate as fraction of total requests.
        """
        selector = ""
        if service:
            selector = f'{{service="{service}"}}'

        query = (
            f"sum(rate(kong_http_requests_total{selector}{{code=~'4..|5..'}}[{time_range}])) / "
            f"sum(rate(kong_http_requests_total{selector}[{time_range}]))"
        )
        return self.query(query)

    def get_kong_bandwidth(
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
        selector = ""
        if service:
            selector = f'{{service="{service}"}}'

        results = {}
        if direction in ("ingress", "both"):
            results["ingress"] = self.query(
                f"rate(kong_bandwidth_bytes{selector}{{type='ingress'}}[{time_range}])"
            )
        if direction in ("egress", "both"):
            results["egress"] = self.query(
                f"rate(kong_bandwidth_bytes{selector}{{type='egress'}}[{time_range}])"
            )

        return results
