"""Jaeger Query API client for distributed tracing.

Provides methods to query Kong traces from Jaeger.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

import httpx
import structlog

from system_operations_manager.integrations.observability.clients.base import (
    BaseObservabilityClient,
    ObservabilityClientError,
)
from system_operations_manager.integrations.observability.config import JaegerConfig

logger = structlog.get_logger()


class JaegerQueryError(ObservabilityClientError):
    """Raised when a Jaeger query fails."""


class JaegerClient(BaseObservabilityClient):
    """Client for Jaeger Query API.

    Provides methods to query distributed traces from Jaeger.

    Example:
        ```python
        from system_operations_manager.integrations.observability.config import JaegerConfig
        from system_operations_manager.integrations.observability.clients import JaegerClient

        config = JaegerConfig(query_url="http://localhost:16686")
        with JaegerClient(config) as client:
            traces = client.find_traces(service="kong")
            print(traces)
        ```
    """

    def __init__(self, config: JaegerConfig) -> None:
        """Initialize Jaeger client.

        Args:
            config: Jaeger configuration.
        """
        super().__init__(
            base_url=config.query_url,
            timeout=config.timeout,
        )
        self.config = config

    @property
    def client_name(self) -> str:
        """Return the client name for logging."""
        return "Jaeger"

    def _build_client(self, **kwargs: Any) -> httpx.Client:
        """Build httpx client with Jaeger-specific configuration."""
        auth = None
        if self.config.username and self.config.password:
            auth = (self.config.username, self.config.password)

        return httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            auth=auth,
            **kwargs,
        )

    def health_check(self) -> bool:
        """Check if Jaeger Query is healthy.

        Returns:
            True if Jaeger is healthy.
        """
        try:
            # Jaeger doesn't have a standard health endpoint,
            # so we try to get services as a health check
            self.get_services()
            return True
        except ObservabilityClientError:
            return False

    def _datetime_to_microseconds(self, dt: datetime) -> int:
        """Convert datetime to microseconds since epoch.

        Args:
            dt: Datetime to convert.

        Returns:
            Microseconds since epoch.
        """
        return int(dt.timestamp() * 1_000_000)

    def get_services(self) -> list[str]:
        """Get list of all services.

        Returns:
            List of service names.
        """
        data = self.get("/api/services")
        return cast(list[str], data.get("data", []))

    def get_operations(self, service: str) -> list[str]:
        """Get operations for a service.

        Args:
            service: Service name.

        Returns:
            List of operation names.
        """
        data = self.get(f"/api/services/{service}/operations")
        return cast(list[str], data.get("data", []))

    def find_traces(
        self,
        service: str,
        operation: str | None = None,
        tags: dict[str, str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        min_duration: str | None = None,
        max_duration: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find traces matching criteria.

        Args:
            service: Service name (required).
            operation: Filter by operation name.
            tags: Filter by span tags (key=value pairs).
            start_time: Start of time range.
            end_time: End of time range.
            min_duration: Minimum trace duration (e.g., "100ms", "1s").
            max_duration: Maximum trace duration.
            limit: Maximum number of traces.

        Returns:
            List of traces with spans.

        Example:
            ```python
            # Find slow traces for Kong service
            traces = client.find_traces(
                service="kong",
                min_duration="500ms",
                limit=10
            )
            for trace in traces:
                print(trace['traceID'], len(trace['spans']))
            ```
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        params: dict[str, Any] = {
            "service": service,
            "start": self._datetime_to_microseconds(start_time),
            "end": self._datetime_to_microseconds(end_time),
            "limit": limit,
        }

        if operation:
            params["operation"] = operation

        if tags:
            # Jaeger expects tags as JSON string
            import json

            params["tags"] = json.dumps(tags)

        if min_duration:
            params["minDuration"] = min_duration

        if max_duration:
            params["maxDuration"] = max_duration

        logger.debug("Jaeger find traces", service=service, operation=operation)
        data = self.get("/api/traces", params=params)
        return cast(list[dict[str, Any]], data.get("data", []))

    def get_trace(self, trace_id: str) -> dict[str, Any]:
        """Get a specific trace by ID.

        Args:
            trace_id: The trace ID.

        Returns:
            Trace data with all spans.
        """
        data = self.get(f"/api/traces/{trace_id}")
        traces = cast(list[dict[str, Any]], data.get("data", []))
        if not traces:
            raise JaegerQueryError(f"Trace not found: {trace_id}", status_code=404)
        return traces[0]

    def compare_traces(
        self,
        trace_id_a: str,
        trace_id_b: str,
    ) -> dict[str, Any]:
        """Compare two traces.

        Args:
            trace_id_a: First trace ID.
            trace_id_b: Second trace ID.

        Returns:
            Comparison data.
        """
        # Get both traces
        trace_a = self.get_trace(trace_id_a)
        trace_b = self.get_trace(trace_id_b)

        # Calculate basic comparison metrics
        spans_a = trace_a.get("spans", [])
        spans_b = trace_b.get("spans", [])

        duration_a = max((s.get("duration", 0) for s in spans_a), default=0)
        duration_b = max((s.get("duration", 0) for s in spans_b), default=0)

        return {
            "trace_a": {
                "traceID": trace_id_a,
                "span_count": len(spans_a),
                "duration_us": duration_a,
            },
            "trace_b": {
                "traceID": trace_id_b,
                "span_count": len(spans_b),
                "duration_us": duration_b,
            },
            "duration_diff_us": duration_b - duration_a,
            "span_count_diff": len(spans_b) - len(spans_a),
        }

    def get_dependencies(
        self,
        end_time: datetime | None = None,
        lookback: str = "1h",
    ) -> list[dict[str, Any]]:
        """Get service dependency graph.

        Args:
            end_time: End time for the query.
            lookback: Time period to look back (e.g., "1h", "24h").

        Returns:
            List of service dependencies.
        """
        if end_time is None:
            end_time = datetime.now()

        params = {
            "endTs": int(end_time.timestamp() * 1000),
            "lookback": lookback,
        }

        data = self.get("/api/dependencies", params=params)
        return cast(list[dict[str, Any]], data.get("data", []))

    # Kong-specific convenience methods

    def get_kong_traces(
        self,
        service_name: str = "kong",
        route: str | None = None,
        upstream: str | None = None,
        status_code: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        min_duration: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get Kong request traces.

        Args:
            service_name: Kong service name in Jaeger.
            route: Filter by Kong route name.
            upstream: Filter by upstream service.
            status_code: Filter by HTTP status code.
            start_time: Start of time range.
            end_time: End of time range.
            min_duration: Minimum trace duration.
            limit: Maximum traces to return.

        Returns:
            List of Kong traces.
        """
        tags = {}
        if route:
            tags["kong.route"] = route
        if upstream:
            tags["kong.upstream"] = upstream
        if status_code:
            tags["http.status_code"] = str(status_code)

        return self.find_traces(
            service=service_name,
            tags=tags if tags else None,
            start_time=start_time,
            end_time=end_time,
            min_duration=min_duration,
            limit=limit,
        )

    def get_kong_slow_traces(
        self,
        threshold: str = "500ms",
        service_name: str = "kong",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get slow Kong request traces.

        Args:
            threshold: Minimum duration threshold.
            service_name: Kong service name in Jaeger.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum traces to return.

        Returns:
            List of slow traces.
        """
        return self.find_traces(
            service=service_name,
            min_duration=threshold,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_kong_error_traces(
        self,
        service_name: str = "kong",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get Kong error traces (5xx responses).

        Args:
            service_name: Kong service name in Jaeger.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum traces to return.

        Returns:
            List of error traces.
        """
        return self.find_traces(
            service=service_name,
            tags={"error": "true"},
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def analyze_trace(self, trace_id: str) -> dict[str, Any]:
        """Analyze a trace for performance insights.

        Args:
            trace_id: The trace ID to analyze.

        Returns:
            Analysis with timing breakdown and insights.
        """
        trace = self.get_trace(trace_id)
        spans = trace.get("spans", [])

        if not spans:
            return {"error": "No spans in trace"}

        # Calculate timing statistics
        durations = [s.get("duration", 0) for s in spans]
        total_duration = max(durations) if durations else 0

        # Find root span and calculate service breakdown
        service_times: dict[str, int] = {}
        for span in spans:
            service = span.get("processID", "unknown")
            process = trace.get("processes", {}).get(service, {})
            service_name = process.get("serviceName", service)
            duration = span.get("duration", 0)
            service_times[service_name] = service_times.get(service_name, 0) + duration

        # Find the slowest span
        slowest_span = max(spans, key=lambda s: s.get("duration", 0)) if spans else None

        return {
            "trace_id": trace_id,
            "total_duration_us": total_duration,
            "span_count": len(spans),
            "service_breakdown": service_times,
            "slowest_span": {
                "operation": slowest_span.get("operationName") if slowest_span else None,
                "duration_us": slowest_span.get("duration") if slowest_span else 0,
            },
        }
