"""Logs manager for Kong observability.

Provides a high-level interface for searching Kong logs from
Elasticsearch or Loki.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

import structlog

if TYPE_CHECKING:
    from system_operations_manager.integrations.observability import (
        ElasticsearchClient,
        ElasticsearchConfig,
        LokiClient,
        LokiConfig,
    )


logger = structlog.get_logger()


class LogsManager:
    """Manager for Kong log queries.

    Provides a unified interface for searching Kong logs from either
    Elasticsearch or Loki backends.

    Example:
        ```python
        from system_operations_manager.integrations.observability import ElasticsearchConfig
        from system_operations_manager.services.observability import LogsManager

        config = ElasticsearchConfig(hosts=["http://localhost:9200"])
        manager = LogsManager.from_elasticsearch(config)

        # Search for error logs
        logs = manager.search_logs(query="error", limit=100)

        # Get error logs for a specific service
        errors = manager.get_error_logs(service="my-api")
        ```
    """

    def __init__(
        self,
        elasticsearch_config: ElasticsearchConfig | None = None,
        loki_config: LokiConfig | None = None,
    ) -> None:
        """Initialize logs manager.

        At least one backend configuration must be provided.

        Args:
            elasticsearch_config: Elasticsearch configuration.
            loki_config: Loki configuration.

        Raises:
            ValueError: If no backend configuration is provided.
        """
        if elasticsearch_config is None and loki_config is None:
            raise ValueError("At least one logs backend must be configured")

        self._es_config = elasticsearch_config
        self._loki_config = loki_config
        self._es_client: ElasticsearchClient | None = None
        self._loki_client: LokiClient | None = None

    @classmethod
    def from_elasticsearch(cls, config: ElasticsearchConfig) -> LogsManager:
        """Create a LogsManager with Elasticsearch backend.

        Args:
            config: Elasticsearch configuration.

        Returns:
            LogsManager instance.
        """
        return cls(elasticsearch_config=config)

    @classmethod
    def from_loki(cls, config: LokiConfig) -> LogsManager:
        """Create a LogsManager with Loki backend.

        Args:
            config: Loki configuration.

        Returns:
            LogsManager instance.
        """
        return cls(loki_config=config)

    @property
    def backend(self) -> Literal["elasticsearch", "loki"]:
        """Get the configured backend type."""
        if self._es_config is not None:
            return "elasticsearch"
        return "loki"

    @property
    def es_client(self) -> ElasticsearchClient:
        """Get or create the Elasticsearch client."""
        if self._es_config is None:
            raise RuntimeError("Elasticsearch is not configured")

        if self._es_client is None:
            from system_operations_manager.integrations.observability import (
                ElasticsearchClient,
            )

            self._es_client = ElasticsearchClient(self._es_config)
        return self._es_client

    @property
    def loki_client(self) -> LokiClient:
        """Get or create the Loki client."""
        if self._loki_config is None:
            raise RuntimeError("Loki is not configured")

        if self._loki_client is None:
            from system_operations_manager.integrations.observability import LokiClient

            self._loki_client = LokiClient(self._loki_config)
        return self._loki_client

    def close(self) -> None:
        """Close all client connections."""
        if self._es_client is not None:
            self._es_client.close()
            self._es_client = None
        if self._loki_client is not None:
            self._loki_client.close()
            self._loki_client = None

    def __enter__(self) -> LogsManager:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def is_available(self) -> bool:
        """Check if the logs backend is available.

        Returns:
            True if backend is healthy and responding.
        """
        try:
            if self.backend == "elasticsearch":
                return self.es_client.health_check()
            return self.loki_client.health_check()
        except Exception:
            return False

    def search_logs(
        self,
        query: str | None = None,
        service: str | None = None,
        route: str | None = None,
        status_code: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search Kong access logs.

        Args:
            query: Full-text search query.
            service: Filter by service name.
            route: Filter by route name.
            status_code: Filter by HTTP status code.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum results to return.

        Returns:
            List of log entries.
        """
        if self.backend == "elasticsearch":
            return self.es_client.search_logs(
                query_string=query,
                service=service,
                route=route,
                status_code=status_code,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        return self.loki_client.search_kong_logs(
            query_text=query,
            service=service,
            route=route,
            status_code=status_code,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_error_logs(
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
        if self.backend == "elasticsearch":
            return self.es_client.search_error_logs(
                service=service,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        return self.loki_client.get_kong_error_logs(
            service=service,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_services(self) -> list[str]:
        """Get list of services with logs.

        Returns:
            List of service names found in logs.
        """
        if self.backend == "elasticsearch":
            # Use aggregation to get unique services
            result = self.es_client.aggregate_by_service()
            return list(result.keys())
        return self.loki_client.get_kong_services()

    def get_routes(self) -> list[str]:
        """Get list of routes with logs.

        Returns:
            List of route names found in logs.
        """
        if self.backend == "loki":
            return self.loki_client.get_kong_routes()
        # Elasticsearch doesn't have a direct method for this
        return []

    def get_status_distribution(
        self,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[int, int]:
        """Get distribution of HTTP status codes.

        Args:
            service: Filter by service name.
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            Dict mapping status code to count.
        """
        if self.backend == "elasticsearch":
            return self.es_client.aggregate_by_status(
                start_time=start_time,
                end_time=end_time,
                service=service,
            )
        # Loki doesn't support aggregations natively
        # Would need to implement a workaround
        logger.warning("Status distribution not supported for Loki backend")
        return {}

    def get_service_distribution(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, int]:
        """Get distribution of requests by service.

        Args:
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            Dict mapping service name to count.
        """
        if self.backend == "elasticsearch":
            return self.es_client.aggregate_by_service(
                start_time=start_time,
                end_time=end_time,
            )
        # Loki doesn't support aggregations natively
        logger.warning("Service distribution not supported for Loki backend")
        return {}

    def count_logs(
        self,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Count total log entries.

        Args:
            service: Filter by service name.
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            Total log count.
        """
        if self.backend == "elasticsearch":
            return self.es_client.count_logs(
                start_time=start_time,
                end_time=end_time,
                service=service,
            )
        # Loki doesn't have a direct count endpoint
        # Could estimate from rate queries
        logger.warning("Log count not directly supported for Loki backend")
        return 0

    def get_summary(
        self,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get a summary of log statistics.

        Args:
            service: Filter by service name.
            start_time: Start of time range (default: last hour).
            end_time: End of time range (default: now).

        Returns:
            Summary dict with counts and distributions.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        summary: dict[str, Any] = {
            "backend": self.backend,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        }

        # Get total count
        summary["total_logs"] = self.count_logs(
            service=service,
            start_time=start_time,
            end_time=end_time,
        )

        # Get status distribution
        status_dist = self.get_status_distribution(
            service=service,
            start_time=start_time,
            end_time=end_time,
        )
        summary["status_distribution"] = status_dist

        # Calculate error counts
        error_count = sum(count for code, count in status_dist.items() if code >= 400)
        summary["error_count"] = error_count

        # Get service distribution if not filtering by service
        if service is None:
            summary["service_distribution"] = self.get_service_distribution(
                start_time=start_time,
                end_time=end_time,
            )

        return summary
