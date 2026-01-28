"""Zipkin API client for distributed tracing.

Provides methods to query Kong traces from Zipkin.
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
from system_operations_manager.integrations.observability.config import ZipkinConfig

logger = structlog.get_logger()


class ZipkinQueryError(ObservabilityClientError):
    """Raised when a Zipkin query fails."""


class ZipkinClient(BaseObservabilityClient):
    """Client for Zipkin API.

    Provides methods to query distributed traces from Zipkin.

    Example:
        ```python
        from system_operations_manager.integrations.observability.config import ZipkinConfig
        from system_operations_manager.integrations.observability.clients import ZipkinClient

        config = ZipkinConfig(url="http://localhost:9411")
        with ZipkinClient(config) as client:
            traces = client.find_traces(service_name="kong")
            print(traces)
        ```
    """

    def __init__(self, config: ZipkinConfig) -> None:
        """Initialize Zipkin client.

        Args:
            config: Zipkin configuration.
        """
        super().__init__(
            base_url=config.url,
            timeout=config.timeout,
        )
        self.config = config

    @property
    def client_name(self) -> str:
        """Return the client name for logging."""
        return "Zipkin"

    def _build_client(self, **kwargs: Any) -> httpx.Client:
        """Build httpx client with Zipkin-specific configuration."""
        return httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            **kwargs,
        )

    def health_check(self) -> bool:
        """Check if Zipkin is healthy.

        Returns:
            True if Zipkin is healthy.
        """
        try:
            response = self._make_retry_request("GET", "/health")
            return bool(response.status_code == 200)
        except ObservabilityClientError:
            return False

    def _datetime_to_milliseconds(self, dt: datetime) -> int:
        """Convert datetime to milliseconds since epoch.

        Args:
            dt: Datetime to convert.

        Returns:
            Milliseconds since epoch.
        """
        return int(dt.timestamp() * 1000)

    def get_services(self) -> list[str]:
        """Get list of all services.

        Returns:
            List of service names.
        """
        response = self._make_retry_request("GET", "/api/v2/services")
        return cast(list[str], response.json())

    def get_spans(self, service_name: str) -> list[str]:
        """Get span names for a service.

        Args:
            service_name: Name of the service.

        Returns:
            List of span names.
        """
        response = self._make_retry_request("GET", f"/api/v2/spans?serviceName={service_name}")
        return cast(list[str], response.json())

    def get_remote_services(self, service_name: str) -> list[str]:
        """Get remote services called by a service.

        Args:
            service_name: Name of the calling service.

        Returns:
            List of remote service names.
        """
        response = self._make_retry_request(
            "GET", f"/api/v2/remoteServices?serviceName={service_name}"
        )
        return cast(list[str], response.json())

    def find_traces(
        self,
        service_name: str | None = None,
        span_name: str | None = None,
        remote_service_name: str | None = None,
        annotation_query: str | None = None,
        tags: dict[str, str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
        limit: int = 10,
    ) -> list[list[dict[str, Any]]]:
        """Find traces matching criteria.

        Args:
            service_name: Filter by service name.
            span_name: Filter by span name.
            remote_service_name: Filter by remote service.
            annotation_query: Filter by annotation.
            tags: Filter by tags.
            start_time: Start of time range.
            end_time: End of time range.
            min_duration: Minimum trace duration in microseconds.
            max_duration: Maximum trace duration in microseconds.
            limit: Maximum number of traces.

        Returns:
            List of traces (each trace is a list of spans).

        Example:
            ```python
            # Find traces for Kong service
            traces = client.find_traces(
                service_name="kong",
                limit=10
            )
            for trace in traces:
                print(f"Trace with {len(trace)} spans")
            ```
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        params: dict[str, Any] = {
            "endTs": self._datetime_to_milliseconds(end_time),
            "lookback": int((end_time - start_time).total_seconds() * 1000),
            "limit": limit,
        }

        if service_name:
            params["serviceName"] = service_name

        if span_name:
            params["spanName"] = span_name

        if remote_service_name:
            params["remoteServiceName"] = remote_service_name

        if annotation_query:
            params["annotationQuery"] = annotation_query

        if tags:
            # Zipkin expects tags as key=value pairs
            tag_strs = [f"{k}={v}" for k, v in tags.items()]
            params["annotationQuery"] = " and ".join(tag_strs)

        if min_duration:
            params["minDuration"] = min_duration

        if max_duration:
            params["maxDuration"] = max_duration

        logger.debug("Zipkin find traces", service=service_name, span=span_name)
        response = self._make_retry_request("GET", "/api/v2/traces", params=params)
        return cast(list[list[dict[str, Any]]], response.json())

    def get_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """Get a specific trace by ID.

        Args:
            trace_id: The trace ID.

        Returns:
            List of spans in the trace.
        """
        response = self._make_retry_request("GET", f"/api/v2/trace/{trace_id}")
        spans = cast(list[dict[str, Any]], response.json())
        if not spans:
            raise ZipkinQueryError(f"Trace not found: {trace_id}", status_code=404)
        return spans

    def get_dependencies(
        self,
        end_time: datetime | None = None,
        lookback: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get service dependency graph.

        Args:
            end_time: End time for the query.
            lookback: Lookback period in milliseconds.

        Returns:
            List of service dependencies.
        """
        if end_time is None:
            end_time = datetime.now()

        params: dict[str, Any] = {
            "endTs": self._datetime_to_milliseconds(end_time),
        }

        if lookback:
            params["lookback"] = lookback

        response = self._make_retry_request("GET", "/api/v2/dependencies", params=params)
        return cast(list[dict[str, Any]], response.json())

    # Kong-specific convenience methods

    def get_kong_traces(
        self,
        service_name: str = "kong",
        route: str | None = None,
        upstream: str | None = None,
        status_code: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        min_duration: int | None = None,
        limit: int = 10,
    ) -> list[list[dict[str, Any]]]:
        """Get Kong request traces.

        Args:
            service_name: Kong service name in Zipkin.
            route: Filter by Kong route name.
            upstream: Filter by upstream service.
            status_code: Filter by HTTP status code.
            start_time: Start of time range.
            end_time: End of time range.
            min_duration: Minimum trace duration in microseconds.
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
            service_name=service_name,
            tags=tags if tags else None,
            start_time=start_time,
            end_time=end_time,
            min_duration=min_duration,
            limit=limit,
        )

    def get_kong_slow_traces(
        self,
        threshold_us: int = 500000,
        service_name: str = "kong",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10,
    ) -> list[list[dict[str, Any]]]:
        """Get slow Kong request traces.

        Args:
            threshold_us: Minimum duration threshold in microseconds.
            service_name: Kong service name in Zipkin.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum traces to return.

        Returns:
            List of slow traces.
        """
        return self.find_traces(
            service_name=service_name,
            min_duration=threshold_us,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_kong_error_traces(
        self,
        service_name: str = "kong",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10,
    ) -> list[list[dict[str, Any]]]:
        """Get Kong error traces.

        Args:
            service_name: Kong service name in Zipkin.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum traces to return.

        Returns:
            List of error traces.
        """
        return self.find_traces(
            service_name=service_name,
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
        spans = self.get_trace(trace_id)

        if not spans:
            return {"error": "No spans in trace"}

        # Calculate timing statistics
        durations = [s.get("duration", 0) for s in spans]
        total_duration = max(durations) if durations else 0

        # Find service breakdown
        service_times: dict[str, int] = {}
        for span in spans:
            local_endpoint = span.get("localEndpoint", {})
            service_name = local_endpoint.get("serviceName", "unknown")
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
                "name": slowest_span.get("name") if slowest_span else None,
                "duration_us": slowest_span.get("duration") if slowest_span else 0,
            },
        }

    def get_trace_summary(self, traces: list[list[dict[str, Any]]]) -> dict[str, Any]:
        """Get summary statistics for a list of traces.

        Args:
            traces: List of traces from find_traces.

        Returns:
            Summary statistics.
        """
        if not traces:
            return {"trace_count": 0}

        durations = []
        span_counts = []
        services_seen: set[str] = set()

        for trace in traces:
            if trace:
                # Get trace duration from root span
                trace_duration = max((s.get("duration", 0) for s in trace), default=0)
                durations.append(trace_duration)
                span_counts.append(len(trace))

                for span in trace:
                    local_endpoint = span.get("localEndpoint", {})
                    service_name = local_endpoint.get("serviceName")
                    if service_name:
                        services_seen.add(service_name)

        return {
            "trace_count": len(traces),
            "avg_duration_us": sum(durations) / len(durations) if durations else 0,
            "max_duration_us": max(durations) if durations else 0,
            "min_duration_us": min(durations) if durations else 0,
            "avg_span_count": sum(span_counts) / len(span_counts) if span_counts else 0,
            "services": sorted(services_seen),
        }
