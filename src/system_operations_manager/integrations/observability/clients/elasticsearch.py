"""Elasticsearch client for log search.

Provides methods to search Kong logs in Elasticsearch.
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
from system_operations_manager.integrations.observability.config import ElasticsearchConfig

logger = structlog.get_logger()


class ElasticsearchQueryError(ObservabilityClientError):
    """Raised when an Elasticsearch query fails."""


class ElasticsearchClient(BaseObservabilityClient):
    """Client for Elasticsearch log search.

    Provides methods to search and aggregate Kong logs stored in Elasticsearch.

    Example:
        ```python
        from system_operations_manager.integrations.observability.config import ElasticsearchConfig
        from system_operations_manager.integrations.observability.clients import ElasticsearchClient

        config = ElasticsearchConfig(hosts=["http://localhost:9200"])
        with ElasticsearchClient(config) as client:
            logs = client.search_logs("error", limit=100)
            print(logs)
        ```
    """

    def __init__(self, config: ElasticsearchConfig) -> None:
        """Initialize Elasticsearch client.

        Args:
            config: Elasticsearch configuration.
        """
        # Use first host as base URL
        base_url = config.hosts[0] if config.hosts else "http://localhost:9200"
        super().__init__(
            base_url=base_url,
            timeout=config.timeout,
        )
        self.config = config
        self.index_pattern = config.index_pattern

    @property
    def client_name(self) -> str:
        """Return the client name for logging."""
        return "Elasticsearch"

    def _build_client(self, **kwargs: Any) -> httpx.Client:
        """Build httpx client with Elasticsearch-specific configuration."""
        headers = {"Content-Type": "application/json"}

        auth = None
        if self.config.username and self.config.password:
            auth = (self.config.username, self.config.password)
        elif self.config.api_key:
            headers["Authorization"] = f"ApiKey {self.config.api_key}"

        return httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            auth=auth,
            headers=headers,
            verify=self.config.verify_certs,
            **kwargs,
        )

    def health_check(self) -> bool:
        """Check if Elasticsearch is healthy.

        Returns:
            True if Elasticsearch cluster is healthy.
        """
        try:
            data = self.get("/_cluster/health")
            status = data.get("status", "red")
            return status in ("green", "yellow")
        except ObservabilityClientError:
            return False

    def get_cluster_info(self) -> dict[str, Any]:
        """Get cluster information.

        Returns:
            Cluster name, version, and other metadata.
        """
        return self.get("/")

    def search(
        self,
        query: dict[str, Any],
        index: str | None = None,
        size: int = 100,
        from_: int = 0,
        sort: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute a search query.

        Args:
            query: Elasticsearch query DSL.
            index: Index pattern (default: configured pattern).
            size: Maximum number of results.
            from_: Starting offset for pagination.
            sort: Sort specification.

        Returns:
            Search response with hits.
        """
        if index is None:
            index = self.index_pattern

        body: dict[str, Any] = {
            "query": query,
            "size": size,
            "from": from_,
        }

        if sort:
            body["sort"] = sort

        logger.debug("Elasticsearch search", index=index, query=query)
        return self.post(f"/{index}/_search", json=body)

    def search_logs(
        self,
        query_string: str | None = None,
        service: str | None = None,
        route: str | None = None,
        status_code: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> list[dict[str, Any]]:
        """Search Kong access logs.

        Args:
            query_string: Full-text search query.
            service: Filter by service name.
            route: Filter by route name.
            status_code: Filter by HTTP status code.
            start_time: Start of time range.
            end_time: End of time range.
            limit: Maximum results to return.
            offset: Pagination offset.
            sort_order: Sort order by timestamp.

        Returns:
            List of log entries.
        """
        must_clauses: list[dict[str, Any]] = []

        if query_string:
            must_clauses.append(
                {
                    "query_string": {
                        "query": query_string,
                        "default_operator": "AND",
                    }
                }
            )

        if service:
            must_clauses.append({"term": {"service.name.keyword": service}})

        if route:
            must_clauses.append({"term": {"route.name.keyword": route}})

        if status_code:
            must_clauses.append({"term": {"response.status": status_code}})

        # Time range filter
        if start_time or end_time:
            time_range: dict[str, Any] = {}
            if start_time:
                time_range["gte"] = start_time.isoformat()
            if end_time:
                time_range["lte"] = end_time.isoformat()
            must_clauses.append({"range": {"@timestamp": time_range}})

        query: dict[str, Any] = (
            {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
        )

        sort = [{"@timestamp": {"order": sort_order}}]

        result = self.search(query, size=limit, from_=offset, sort=sort)

        hits = result.get("hits", {}).get("hits", [])
        return [hit.get("_source", {}) for hit in hits]

    def search_error_logs(
        self,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search Kong error logs (4xx and 5xx status codes).

        Args:
            service: Filter by service name.
            start_time: Start of time range.
            end_time: End of time range (default: now).
            limit: Maximum results to return.

        Returns:
            List of error log entries.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        must_clauses: list[dict[str, Any]] = [
            {"range": {"response.status": {"gte": 400}}},
            {"range": {"@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}},
        ]

        if service:
            must_clauses.append({"term": {"service.name.keyword": service}})

        query = {"bool": {"must": must_clauses}}
        sort = [{"@timestamp": {"order": "desc"}}]

        result = self.search(query, size=limit, sort=sort)

        hits = result.get("hits", {}).get("hits", [])
        return [hit.get("_source", {}) for hit in hits]

    def aggregate_by_status(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        service: str | None = None,
    ) -> dict[int, int]:
        """Aggregate request counts by HTTP status code.

        Args:
            start_time: Start of time range.
            end_time: End of time range.
            service: Filter by service name.

        Returns:
            Dict mapping status code to request count.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        must_clauses: list[dict[str, Any]] = [
            {"range": {"@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}}
        ]

        if service:
            must_clauses.append({"term": {"service.name.keyword": service}})

        body = {
            "query": {"bool": {"must": must_clauses}},
            "size": 0,
            "aggs": {
                "status_codes": {
                    "terms": {
                        "field": "response.status",
                        "size": 100,
                    }
                }
            },
        }

        result = self.post(f"/{self.index_pattern}/_search", json=body)

        buckets = result.get("aggregations", {}).get("status_codes", {}).get("buckets", [])
        return {bucket["key"]: bucket["doc_count"] for bucket in buckets}

    def aggregate_by_service(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, int]:
        """Aggregate request counts by service.

        Args:
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            Dict mapping service name to request count.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        body = {
            "query": {
                "range": {
                    "@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}
                }
            },
            "size": 0,
            "aggs": {
                "services": {
                    "terms": {
                        "field": "service.name.keyword",
                        "size": 100,
                    }
                }
            },
        }

        result = self.post(f"/{self.index_pattern}/_search", json=body)

        buckets = result.get("aggregations", {}).get("services", {}).get("buckets", [])
        return {bucket["key"]: bucket["doc_count"] for bucket in buckets}

    def get_latency_histogram(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        service: str | None = None,
        interval: str = "1m",
    ) -> list[dict[str, Any]]:
        """Get latency histogram over time.

        Args:
            start_time: Start of time range.
            end_time: End of time range.
            service: Filter by service name.
            interval: Time bucket interval.

        Returns:
            List of time buckets with latency stats.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        must_clauses: list[dict[str, Any]] = [
            {"range": {"@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}}
        ]

        if service:
            must_clauses.append({"term": {"service.name.keyword": service}})

        body = {
            "query": {"bool": {"must": must_clauses}},
            "size": 0,
            "aggs": {
                "latency_over_time": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "fixed_interval": interval,
                    },
                    "aggs": {
                        "latency_stats": {
                            "extended_stats": {
                                "field": "latencies.request",
                            }
                        },
                        "percentiles": {
                            "percentiles": {
                                "field": "latencies.request",
                                "percents": [50, 90, 95, 99],
                            }
                        },
                    },
                }
            },
        }

        result = self.post(f"/{self.index_pattern}/_search", json=body)

        aggs = result.get("aggregations", {})
        latency = aggs.get("latency_over_time", {}) if isinstance(aggs, dict) else {}
        buckets = latency.get("buckets", []) if isinstance(latency, dict) else []
        return cast(list[dict[str, Any]], buckets)

    def count_logs(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        service: str | None = None,
    ) -> int:
        """Count total log entries.

        Args:
            start_time: Start of time range.
            end_time: End of time range.
            service: Filter by service name.

        Returns:
            Total log count.
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=24)

        must_clauses: list[dict[str, Any]] = [
            {"range": {"@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}}
        ]

        if service:
            must_clauses.append({"term": {"service.name.keyword": service}})

        body = {"query": {"bool": {"must": must_clauses}}}

        result = self.post(f"/{self.index_pattern}/_count", json=body)
        count = result.get("count", 0)
        return int(count) if isinstance(count, (int, float)) else 0
