"""Tracing manager for Kong observability.

Provides a high-level interface for querying Kong traces from
Jaeger or Zipkin.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

import structlog

if TYPE_CHECKING:
    from system_operations_manager.integrations.observability import (
        JaegerClient,
        JaegerConfig,
        ZipkinClient,
        ZipkinConfig,
    )


logger = structlog.get_logger()


class TracingManager:
    """Manager for Kong distributed tracing queries.

    Provides a unified interface for querying Kong traces from either
    Jaeger or Zipkin backends.

    Example:
        ```python
        from system_operations_manager.integrations.observability import JaegerConfig
        from system_operations_manager.services.observability import TracingManager

        config = JaegerConfig(query_url="http://localhost:16686")
        manager = TracingManager.from_jaeger(config)

        # Find recent traces
        traces = manager.find_traces(limit=20)

        # Find slow traces
        slow_traces = manager.get_slow_traces(threshold_ms=500)
        ```
    """

    def __init__(
        self,
        jaeger_config: JaegerConfig | None = None,
        zipkin_config: ZipkinConfig | None = None,
        service_name: str = "kong",
    ) -> None:
        """Initialize tracing manager.

        At least one backend configuration must be provided.

        Args:
            jaeger_config: Jaeger configuration.
            zipkin_config: Zipkin configuration.
            service_name: Default Kong service name in traces.

        Raises:
            ValueError: If no backend configuration is provided.
        """
        if jaeger_config is None and zipkin_config is None:
            raise ValueError("At least one tracing backend must be configured")

        self._jaeger_config = jaeger_config
        self._zipkin_config = zipkin_config
        self._jaeger_client: JaegerClient | None = None
        self._zipkin_client: ZipkinClient | None = None
        self.service_name = service_name

    @classmethod
    def from_jaeger(
        cls,
        config: JaegerConfig,
        service_name: str = "kong",
    ) -> TracingManager:
        """Create a TracingManager with Jaeger backend.

        Args:
            config: Jaeger configuration.
            service_name: Default Kong service name.

        Returns:
            TracingManager instance.
        """
        return cls(jaeger_config=config, service_name=service_name)

    @classmethod
    def from_zipkin(
        cls,
        config: ZipkinConfig,
        service_name: str = "kong",
    ) -> TracingManager:
        """Create a TracingManager with Zipkin backend.

        Args:
            config: Zipkin configuration.
            service_name: Default Kong service name.

        Returns:
            TracingManager instance.
        """
        return cls(zipkin_config=config, service_name=service_name)

    @property
    def backend(self) -> Literal["jaeger", "zipkin"]:
        """Get the configured backend type."""
        if self._jaeger_config is not None:
            return "jaeger"
        return "zipkin"

    @property
    def jaeger_client(self) -> JaegerClient:
        """Get or create the Jaeger client."""
        if self._jaeger_config is None:
            raise RuntimeError("Jaeger is not configured")

        if self._jaeger_client is None:
            from system_operations_manager.integrations.observability import JaegerClient

            self._jaeger_client = JaegerClient(self._jaeger_config)
        return self._jaeger_client

    @property
    def zipkin_client(self) -> ZipkinClient:
        """Get or create the Zipkin client."""
        if self._zipkin_config is None:
            raise RuntimeError("Zipkin is not configured")

        if self._zipkin_client is None:
            from system_operations_manager.integrations.observability import ZipkinClient

            self._zipkin_client = ZipkinClient(self._zipkin_config)
        return self._zipkin_client

    def close(self) -> None:
        """Close all client connections."""
        if self._jaeger_client is not None:
            self._jaeger_client.close()
            self._jaeger_client = None
        if self._zipkin_client is not None:
            self._zipkin_client.close()
            self._zipkin_client = None

    def __enter__(self) -> TracingManager:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def is_available(self) -> bool:
        """Check if the tracing backend is available.

        Returns:
            True if backend is healthy and responding.
        """
        try:
            if self.backend == "jaeger":
                return self.jaeger_client.health_check()
            return self.zipkin_client.health_check()
        except Exception:
            return False

    def find_traces(
        self,
        route: str | None = None,
        upstream: str | None = None,
        status_code: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        min_duration_ms: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find Kong traces matching criteria.

        Args:
            route: Filter by Kong route name.
            upstream: Filter by upstream service.
            status_code: Filter by HTTP status code.
            start_time: Start of time range.
            end_time: End of time range.
            min_duration_ms: Minimum trace duration in milliseconds.
            limit: Maximum traces to return.

        Returns:
            List of traces.
        """
        if self.backend == "jaeger":
            min_duration = f"{min_duration_ms}ms" if min_duration_ms else None
            return self.jaeger_client.get_kong_traces(
                service_name=self.service_name,
                route=route,
                upstream=upstream,
                status_code=status_code,
                start_time=start_time,
                end_time=end_time,
                min_duration=min_duration,
                limit=limit,
            )

        # Zipkin uses microseconds
        min_duration_us = min_duration_ms * 1000 if min_duration_ms else None
        traces = self.zipkin_client.get_kong_traces(
            service_name=self.service_name,
            route=route,
            upstream=upstream,
            status_code=status_code,
            start_time=start_time,
            end_time=end_time,
            min_duration=min_duration_us,
            limit=limit,
        )
        # Normalize Zipkin response format to match Jaeger
        return self._normalize_zipkin_traces(traces)

    def get_trace(self, trace_id: str) -> dict[str, Any]:
        """Get a specific trace by ID.

        Args:
            trace_id: The trace ID.

        Returns:
            Trace data with all spans.
        """
        if self.backend == "jaeger":
            return self.jaeger_client.get_trace(trace_id)

        spans = self.zipkin_client.get_trace(trace_id)
        return self._normalize_zipkin_trace(spans)

    def get_slow_traces(
        self,
        threshold_ms: int = 500,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get slow Kong request traces.

        Args:
            threshold_ms: Minimum duration threshold in milliseconds.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum traces to return.

        Returns:
            List of slow traces.
        """
        if self.backend == "jaeger":
            return self.jaeger_client.get_kong_slow_traces(
                threshold=f"{threshold_ms}ms",
                service_name=self.service_name,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )

        # Zipkin uses microseconds
        threshold_us = threshold_ms * 1000
        traces = self.zipkin_client.get_kong_slow_traces(
            threshold_us=threshold_us,
            service_name=self.service_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        return self._normalize_zipkin_traces(traces)

    def get_error_traces(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get Kong error traces.

        Args:
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum traces to return.

        Returns:
            List of error traces.
        """
        if self.backend == "jaeger":
            return self.jaeger_client.get_kong_error_traces(
                service_name=self.service_name,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )

        traces = self.zipkin_client.get_kong_error_traces(
            service_name=self.service_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        return self._normalize_zipkin_traces(traces)

    def analyze_trace(self, trace_id: str) -> dict[str, Any]:
        """Analyze a trace for performance insights.

        Args:
            trace_id: The trace ID to analyze.

        Returns:
            Analysis with timing breakdown and insights.
        """
        if self.backend == "jaeger":
            return self.jaeger_client.analyze_trace(trace_id)
        return self.zipkin_client.analyze_trace(trace_id)

    def get_services(self) -> list[str]:
        """Get list of services with traces.

        Returns:
            List of service names.
        """
        if self.backend == "jaeger":
            return self.jaeger_client.get_services()
        return self.zipkin_client.get_services()

    def get_operations(self, service: str | None = None) -> list[str]:
        """Get list of operations/spans for a service.

        Args:
            service: Service name (default: Kong service name).

        Returns:
            List of operation/span names.
        """
        service = service or self.service_name

        if self.backend == "jaeger":
            return self.jaeger_client.get_operations(service)
        return self.zipkin_client.get_spans(service)

    def get_dependencies(
        self,
        end_time: datetime | None = None,
        lookback_hours: int = 1,
    ) -> list[dict[str, Any]]:
        """Get service dependency graph.

        Args:
            end_time: End time for the query.
            lookback_hours: Hours to look back.

        Returns:
            List of service dependencies.
        """
        if self.backend == "jaeger":
            return self.jaeger_client.get_dependencies(
                end_time=end_time,
                lookback=f"{lookback_hours}h",
            )

        lookback_ms = lookback_hours * 60 * 60 * 1000
        return self.zipkin_client.get_dependencies(
            end_time=end_time,
            lookback=lookback_ms,
        )

    def _normalize_zipkin_trace(self, spans: list[dict[str, Any]]) -> dict[str, Any]:
        """Normalize a Zipkin trace to Jaeger format.

        Args:
            spans: List of Zipkin spans.

        Returns:
            Trace dict in Jaeger-like format.
        """
        if not spans:
            return {"spans": [], "processes": {}}

        # Extract trace ID from first span
        trace_id = spans[0].get("traceId", "unknown")

        # Build processes dict from services
        processes: dict[str, dict[str, Any]] = {}
        normalized_spans = []

        for span in spans:
            local_endpoint = span.get("localEndpoint", {})
            service_name = local_endpoint.get("serviceName", "unknown")

            # Generate a process ID
            process_id = f"p{len(processes) + 1}"
            if service_name not in [p.get("serviceName") for p in processes.values()]:
                processes[process_id] = {"serviceName": service_name}

            normalized_spans.append(
                {
                    "traceID": trace_id,
                    "spanID": span.get("id"),
                    "operationName": span.get("name"),
                    "duration": span.get("duration", 0),
                    "startTime": span.get("timestamp", 0),
                    "processID": process_id,
                    "tags": [{"key": k, "value": v} for k, v in span.get("tags", {}).items()],
                }
            )

        return {
            "traceID": trace_id,
            "spans": normalized_spans,
            "processes": processes,
        }

    def _normalize_zipkin_traces(
        self,
        traces: list[list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Normalize Zipkin traces to Jaeger format.

        Args:
            traces: List of Zipkin traces (each is a list of spans).

        Returns:
            List of traces in Jaeger-like format.
        """
        return [self._normalize_zipkin_trace(spans) for spans in traces]

    def get_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get a summary of tracing statistics.

        Args:
            start_time: Start of time range (default: last hour).
            end_time: End of time range (default: now).
            limit: Maximum traces to analyze.

        Returns:
            Summary dict with counts and statistics.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        summary: dict[str, Any] = {
            "backend": self.backend,
            "service_name": self.service_name,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        }

        # Get traces
        traces = self.find_traces(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        summary["trace_count"] = len(traces)

        # Calculate duration statistics
        durations = []
        for trace in traces:
            spans = trace.get("spans", [])
            if spans:
                # Get max duration from spans
                max_duration = max(s.get("duration", 0) for s in spans)
                durations.append(max_duration)

        if durations:
            durations_sorted = sorted(durations)
            summary["duration_stats"] = {
                "min_us": min(durations),
                "max_us": max(durations),
                "avg_us": sum(durations) / len(durations),
                "p50_us": durations_sorted[len(durations) // 2],
                "p90_us": durations_sorted[int(len(durations) * 0.9)],
                "p99_us": durations_sorted[int(len(durations) * 0.99)],
            }
        else:
            summary["duration_stats"] = {}

        # Get error traces
        error_traces = self.get_error_traces(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        summary["error_trace_count"] = len(error_traces)

        # Get services
        summary["services"] = self.get_services()

        return summary
