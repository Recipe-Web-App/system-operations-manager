"""Grafana Loki client for log search.

Provides methods to query Kong logs from Loki.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal, cast

import httpx
import structlog

from system_operations_manager.integrations.observability.clients.base import (
    BaseObservabilityClient,
    ObservabilityClientError,
)
from system_operations_manager.integrations.observability.config import LokiConfig

logger = structlog.get_logger()


class LokiQueryError(ObservabilityClientError):
    """Raised when a Loki query fails."""


class LokiClient(BaseObservabilityClient):
    """Client for Grafana Loki log queries.

    Provides methods to query and search Kong logs stored in Loki.

    Example:
        ```python
        from system_operations_manager.integrations.observability.config import LokiConfig
        from system_operations_manager.integrations.observability.clients import LokiClient

        config = LokiConfig(url="http://localhost:3100")
        with LokiClient(config) as client:
            logs = client.query('{job="kong"} |= "error"')
            print(logs)
        ```
    """

    def __init__(self, config: LokiConfig) -> None:
        """Initialize Loki client.

        Args:
            config: Loki configuration.
        """
        super().__init__(
            base_url=config.url,
            timeout=config.timeout,
        )
        self.config = config
        self._org_id = config.org_id

    @property
    def client_name(self) -> str:
        """Return the client name for logging."""
        return "Loki"

    def _build_client(self, **kwargs: Any) -> httpx.Client:
        """Build httpx client with Loki-specific configuration."""
        headers = {}
        if self._org_id:
            headers["X-Scope-OrgID"] = self._org_id

        auth = None
        if self.config.username and self.config.password:
            auth = (self.config.username, self.config.password)

        return httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            auth=auth,
            headers=headers if headers else None,
            **kwargs,
        )

    def health_check(self) -> bool:
        """Check if Loki is healthy.

        Returns:
            True if Loki is healthy.
        """
        try:
            response = self._make_retry_request("GET", "/ready")
            return bool(response.status_code == 200)
        except ObservabilityClientError:
            return False

    def _datetime_to_ns(self, dt: datetime) -> int:
        """Convert datetime to nanoseconds since epoch.

        Args:
            dt: Datetime to convert.

        Returns:
            Nanoseconds since epoch.
        """
        return int(dt.timestamp() * 1_000_000_000)

    def _parse_query_response(
        self,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Parse Loki query response into log entries.

        Args:
            data: Raw Loki response.

        Returns:
            List of log entries with timestamps and messages.
        """
        if data.get("status") != "success":
            error = data.get("error", "Unknown error")
            raise LokiQueryError(f"Query failed: {error}")

        result_data = data.get("data", {})
        result_type = result_data.get("resultType", "")
        results = result_data.get("result", [])

        entries = []
        if result_type == "streams":
            for stream in results:
                labels = stream.get("stream", {})
                for value in stream.get("values", []):
                    timestamp_ns, line = value
                    entries.append(
                        {
                            "timestamp": datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000),
                            "labels": labels,
                            "line": line,
                        }
                    )
        elif result_type == "matrix":
            for series in results:
                labels = series.get("metric", {})
                for value in series.get("values", []):
                    timestamp, val = value
                    entries.append(
                        {
                            "timestamp": datetime.fromtimestamp(float(timestamp)),
                            "labels": labels,
                            "value": float(val),
                        }
                    )

        return entries

    def query(
        self,
        query: str,
        limit: int = 100,
        time: datetime | None = None,
        direction: Literal["forward", "backward"] = "backward",
    ) -> list[dict[str, Any]]:
        """Execute an instant log query.

        Args:
            query: LogQL query string.
            limit: Maximum number of entries.
            time: Evaluation time (default: now).
            direction: Log order direction.

        Returns:
            List of log entries.

        Example:
            ```python
            # Get recent error logs
            logs = client.query('{job="kong"} |= "error"', limit=50)
            for log in logs:
                print(log['timestamp'], log['line'])
            ```
        """
        if time is None:
            time = datetime.now()

        params = {
            "query": query,
            "limit": limit,
            "time": self._datetime_to_ns(time),
            "direction": direction,
        }

        logger.debug("Loki instant query", query=query)
        data = self.get("/loki/api/v1/query", params=params)
        return self._parse_query_response(data)

    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime | None = None,
        limit: int = 1000,
        step: str | None = None,
        direction: Literal["forward", "backward"] = "backward",
    ) -> list[dict[str, Any]]:
        """Execute a range log query.

        Args:
            query: LogQL query string.
            start: Start time.
            end: End time (default: now).
            limit: Maximum number of entries.
            step: Query resolution step for metric queries.
            direction: Log order direction.

        Returns:
            List of log entries or metric values.

        Example:
            ```python
            from datetime import datetime, timedelta
            end = datetime.now()
            start = end - timedelta(hours=1)
            logs = client.query_range(
                '{job="kong"} |= "error"',
                start=start,
                end=end
            )
            ```
        """
        if end is None:
            end = datetime.now()

        params: dict[str, Any] = {
            "query": query,
            "start": self._datetime_to_ns(start),
            "end": self._datetime_to_ns(end),
            "limit": limit,
            "direction": direction,
        }

        if step:
            params["step"] = step

        logger.debug("Loki range query", query=query, start=start, end=end)
        data = self.get("/loki/api/v1/query_range", params=params)
        return self._parse_query_response(data)

    def get_labels(self) -> list[str]:
        """Get all label names.

        Returns:
            List of label names.
        """
        data = self.get("/loki/api/v1/labels")
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
        data = self.get(f"/loki/api/v1/label/{label_name}/values")
        if data.get("status") != "success":
            return []
        return cast(list[str], data.get("data", []))

    def get_series(
        self,
        match: list[str],
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, str]]:
        """Find log streams matching label selectors.

        Args:
            match: List of stream selectors.
            start: Start time.
            end: End time.

        Returns:
            List of matching label sets.
        """
        if end is None:
            end = datetime.now()
        if start is None:
            start = end - timedelta(hours=1)

        params = {
            "match[]": match,
            "start": self._datetime_to_ns(start),
            "end": self._datetime_to_ns(end),
        }

        data = self.get("/loki/api/v1/series", params=params)
        if data.get("status") != "success":
            return []
        return cast(list[dict[str, str]], data.get("data", []))

    # Kong-specific convenience methods

    def search_kong_logs(
        self,
        query_text: str | None = None,
        service: str | None = None,
        route: str | None = None,
        status_code: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search Kong access logs.

        Args:
            query_text: Text to search for in log lines.
            service: Filter by service name.
            route: Filter by route name.
            status_code: Filter by HTTP status code.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum results.

        Returns:
            List of matching log entries.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        # Build label selector
        labels = ['job="kong"']
        if service:
            labels.append(f'service="{service}"')
        if route:
            labels.append(f'route="{route}"')

        selector = "{" + ",".join(labels) + "}"

        # Build line filters
        filters = []
        if query_text:
            filters.append(f'|= "{query_text}"')
        if status_code:
            filters.append(f"| json | response_status = {status_code}")

        query = selector + " ".join(filters)

        return self.query_range(query, start=start_time, end=end_time, limit=limit)

    def get_kong_error_logs(
        self,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get Kong error logs (4xx and 5xx responses).

        Args:
            service: Filter by service name.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum results.

        Returns:
            List of error log entries.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        labels = ['job="kong"']
        if service:
            labels.append(f'service="{service}"')

        selector = "{" + ",".join(labels) + "}"
        query = f"{selector} | json | response_status >= 400"

        return self.query_range(query, start=start_time, end=end_time, limit=limit)

    def get_kong_log_rate(
        self,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        interval: str = "1m",
    ) -> list[dict[str, Any]]:
        """Get Kong log rate over time.

        Args:
            service: Filter by service name.
            start_time: Start of time range.
            end_time: End of time range.
            interval: Rate calculation interval.

        Returns:
            List of time buckets with log rates.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        labels = ['job="kong"']
        if service:
            labels.append(f'service="{service}"')

        selector = "{" + ",".join(labels) + "}"
        query = f"rate({selector}[{interval}])"

        return self.query_range(query, start=start_time, end=end_time, step=interval)

    def get_kong_services(self) -> list[str]:
        """Get list of Kong services with logs.

        Returns:
            List of service names.
        """
        return self.get_label_values("service")

    def get_kong_routes(self) -> list[str]:
        """Get list of Kong routes with logs.

        Returns:
            List of route names.
        """
        return self.get_label_values("route")
