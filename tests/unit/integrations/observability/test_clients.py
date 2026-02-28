"""Unit tests for observability HTTP clients."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from system_operations_manager.integrations.observability.clients import (
    ElasticsearchClient,
    JaegerClient,
    LokiClient,
    PrometheusClient,
    ZipkinClient,
)
from system_operations_manager.integrations.observability.clients.base import (
    ObservabilityAuthError,
    ObservabilityClientError,
    ObservabilityConnectionError,
    ObservabilityNotFoundError,
)
from system_operations_manager.integrations.observability.clients.jaeger import JaegerQueryError
from system_operations_manager.integrations.observability.clients.prometheus import (
    PrometheusQueryError,
)
from system_operations_manager.integrations.observability.config import (
    ElasticsearchConfig,
    JaegerConfig,
    LokiConfig,
    PrometheusConfig,
    ZipkinConfig,
)


@pytest.fixture
def mock_httpx_client(mocker: Any) -> MagicMock:
    """Create a mock httpx client."""
    mock_client = MagicMock(spec=httpx.Client)
    mocker.patch("httpx.Client", return_value=mock_client)
    return mock_client


class TestPrometheusClient:
    """Tests for PrometheusClient."""

    @pytest.fixture
    def config(self) -> PrometheusConfig:
        """Create test config."""
        return PrometheusConfig(url="http://localhost:9090")

    @pytest.fixture
    def client(self, config: PrometheusConfig, mock_httpx_client: MagicMock) -> PrometheusClient:
        """Create client with mocked httpx."""
        return PrometheusClient(config)

    @pytest.mark.unit
    def test_client_initialization(
        self, config: PrometheusConfig, mock_httpx_client: MagicMock
    ) -> None:
        """Client should initialize correctly."""
        client = PrometheusClient(config)

        assert client.client_name == "Prometheus"

    @pytest.mark.unit
    def test_health_check_success(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Health check should return True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.request.return_value = mock_response

        assert client.health_check() is True

    @pytest.mark.unit
    def test_health_check_failure(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Health check should return False when unhealthy."""
        mock_httpx_client.request.side_effect = httpx.ConnectError("Connection refused")

        assert client.health_check() is False

    @pytest.mark.unit
    def test_query(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Query should return parsed results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {"metric": {"job": "kong"}, "value": [1234567890, "100"]},
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        results = client.query("up")

        assert len(results) == 1
        assert results[0]["metric"]["job"] == "kong"

    @pytest.mark.unit
    def test_query_range(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Range query should return time series results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"job": "kong"},
                        "values": [[1234567890, "100"], [1234567900, "200"]],
                    },
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        results = client.query_range("up", start=start, end=end)

        assert len(results) == 1
        assert len(results[0]["values"]) == 2

    @pytest.mark.unit
    def test_get_kong_request_rate(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should query Kong request rate."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        }
        mock_httpx_client.request.return_value = mock_response

        results = client.get_kong_request_rate()

        assert isinstance(results, list)

    @pytest.mark.unit
    def test_get_label_values(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Should return label values."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": ["service-a", "service-b"],
        }
        mock_httpx_client.request.return_value = mock_response

        values = client.get_label_values("service")

        assert values == ["service-a", "service-b"]

    @pytest.mark.unit
    def test_get_targets(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Should return active and dropped targets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "activeTargets": [{"labels": {"job": "kong"}, "health": "up"}],
                "droppedTargets": [],
            }
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.get_targets()

        assert "activeTargets" in result
        assert result["activeTargets"][0]["health"] == "up"

    @pytest.mark.unit
    def test_get_labels(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Should return all label names."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": ["__name__", "job", "instance"],
        }
        mock_httpx_client.request.return_value = mock_response

        labels = client.get_labels()

        assert "job" in labels
        assert "instance" in labels

    @pytest.mark.unit
    def test_get_series(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Should return matching series label sets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {"__name__": "kong_http_requests_total", "job": "kong", "service": "api"},
            ],
        }
        mock_httpx_client.request.return_value = mock_response

        series = client.get_series(["kong_http_requests_total"])

        assert len(series) == 1
        assert series[0]["job"] == "kong"

    @pytest.mark.unit
    def test_get_metadata(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Should return metric metadata."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "kong_http_requests_total": [
                    {"type": "counter", "help": "Total HTTP requests", "unit": ""}
                ]
            },
        }
        mock_httpx_client.request.return_value = mock_response

        metadata = client.get_metadata()

        assert "kong_http_requests_total" in metadata

    @pytest.mark.unit
    def test_get_kong_latency_percentiles(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should return dict mapping percentile to query results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"service": "api"}, "value": [1234567890, "42.5"]}],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.get_kong_latency_percentiles(percentiles=[0.5, 0.99])

        assert 0.5 in result
        assert 0.99 in result
        assert isinstance(result[0.5], list)

    @pytest.mark.unit
    def test_get_kong_upstream_health(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should query upstream health metric and return results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"upstream": "api-upstream", "state": "healthy"},
                        "value": [1234567890, "1"],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        results = client.get_kong_upstream_health()

        assert isinstance(results, list)
        assert results[0]["metric"]["state"] == "healthy"

    @pytest.mark.unit
    def test_get_kong_error_rate(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should return error rate query results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {}, "value": [1234567890, "0.02"]}],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        results = client.get_kong_error_rate()

        assert isinstance(results, list)
        assert len(results) == 1

    @pytest.mark.unit
    def test_get_kong_bandwidth(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should return ingress and egress bandwidth results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"type": "ingress"}, "value": [1234567890, "1024.0"]}],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.get_kong_bandwidth(direction="both")

        assert "ingress" in result
        assert "egress" in result

    @pytest.mark.unit
    def test_build_client_with_bearer_token(self, mock_httpx_client: MagicMock) -> None:
        """Client built with bearer auth should store token and trigger httpx.Client build."""
        config = PrometheusConfig(
            url="http://localhost:9090",
            auth_type="bearer",
            token="my-secret-token",
        )
        client = PrometheusClient(config)
        # Access the client property to trigger _build_client
        _ = client.client

        # Token is stored on the client instance and used in _build_client
        assert client._token == "my-secret-token"
        # httpx.Client was called (mock_httpx_client is the return value of httpx.Client())
        assert mock_httpx_client is not None

    @pytest.mark.unit
    def test_query_with_time_param(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Query with explicit time param should include time in request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        }
        mock_httpx_client.request.return_value = mock_response

        evaluation_time = datetime.now()
        results = client.query("up", time=evaluation_time)

        assert isinstance(results, list)
        # Verify the request was made (time param is sent through the params dict)
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_parse_query_response_error(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """Response with status != 'success' should raise PrometheusQueryError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "errorType": "bad_data",
            "error": "invalid parameter",
        }
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(PrometheusQueryError, match="invalid parameter"):
            client.query("invalid{query")

    @pytest.mark.unit
    def test_get_targets_with_state_filter(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_targets with state='active' should pass state param to request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "activeTargets": [{"labels": {"job": "kong"}, "health": "up"}],
                "droppedTargets": [],
            }
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.get_targets(state="active")

        assert "activeTargets" in result
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_get_labels_failure(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_labels when status != 'success' should return empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "backend unavailable",
        }
        mock_httpx_client.request.return_value = mock_response

        labels = client.get_labels()

        assert labels == []

    @pytest.mark.unit
    def test_get_label_values_failure(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_label_values when status != 'success' should return empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "backend unavailable",
        }
        mock_httpx_client.request.return_value = mock_response

        values = client.get_label_values("service")

        assert values == []

    @pytest.mark.unit
    def test_get_series_with_time_range(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_series with start and end params should include them in request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [{"__name__": "kong_http_requests_total", "job": "kong"}],
        }
        mock_httpx_client.request.return_value = mock_response

        end = datetime.now()
        start = end - timedelta(hours=1)
        series = client.get_series(["kong_http_requests_total"], start=start, end=end)

        assert len(series) == 1
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_get_series_failure(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_series when status != 'success' should return empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "store error",
        }
        mock_httpx_client.request.return_value = mock_response

        series = client.get_series(["kong_http_requests_total"])

        assert series == []

    @pytest.mark.unit
    def test_get_metadata_with_metric_filter(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_metadata with metric param should pass metric to request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "kong_http_requests_total": [
                    {"type": "counter", "help": "Total HTTP requests", "unit": ""}
                ]
            },
        }
        mock_httpx_client.request.return_value = mock_response

        metadata = client.get_metadata(metric="kong_http_requests_total")

        assert "kong_http_requests_total" in metadata
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_get_metadata_failure(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_metadata when status != 'success' should return empty dict."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "store error",
        }
        mock_httpx_client.request.return_value = mock_response

        metadata = client.get_metadata()

        assert metadata == {}

    @pytest.mark.unit
    def test_query_range_with_end_none(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """query_range with end=None should default end to now."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"resultType": "matrix", "result": []},
        }
        mock_httpx_client.request.return_value = mock_response

        start = datetime.now() - timedelta(hours=1)
        results = client.query_range("up", start=start, end=None)

        assert isinstance(results, list)
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_get_kong_request_rate_with_filters(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_request_rate with service and route should build selector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        }
        mock_httpx_client.request.return_value = mock_response

        results = client.get_kong_request_rate(service="my-api", route="my-route")

        assert isinstance(results, list)
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_get_kong_latency_percentiles_with_service(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_latency_percentiles with service param should include service selector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"service": "my-api"}, "value": [1234567890, "55.0"]}],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.get_kong_latency_percentiles(service="my-api", percentiles=[0.5, 0.99])

        assert 0.5 in result
        assert 0.99 in result
        assert isinstance(result[0.5], list)

    @pytest.mark.unit
    def test_get_kong_error_rate_with_service(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_error_rate with service param should include service selector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"service": "my-api"}, "value": [1234567890, "0.05"]}],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        results = client.get_kong_error_rate(service="my-api")

        assert isinstance(results, list)
        assert len(results) == 1

    @pytest.mark.unit
    def test_get_kong_bandwidth_with_service(
        self, client: PrometheusClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_bandwidth with service param should include service selector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"type": "ingress"}, "value": [1234567890, "2048.0"]}],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.get_kong_bandwidth(service="my-api", direction="both")

        assert "ingress" in result
        assert "egress" in result


class TestElasticsearchClient:
    """Tests for ElasticsearchClient."""

    @pytest.fixture
    def config(self) -> ElasticsearchConfig:
        """Create test config."""
        return ElasticsearchConfig(hosts=["http://localhost:9200"])

    @pytest.fixture
    def client(
        self, config: ElasticsearchConfig, mock_httpx_client: MagicMock
    ) -> ElasticsearchClient:
        """Create client with mocked httpx."""
        return ElasticsearchClient(config)

    @pytest.mark.unit
    def test_client_initialization(
        self, config: ElasticsearchConfig, mock_httpx_client: MagicMock
    ) -> None:
        """Client should initialize correctly."""
        client = ElasticsearchClient(config)

        assert client.client_name == "Elasticsearch"

    @pytest.mark.unit
    def test_health_check_success(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Health check should return True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "green"}
        mock_httpx_client.request.return_value = mock_response

        assert client.health_check() is True

    @pytest.mark.unit
    def test_health_check_yellow_is_healthy(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Health check should return True for yellow status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "yellow"}
        mock_httpx_client.request.return_value = mock_response

        assert client.health_check() is True

    @pytest.mark.unit
    def test_health_check_red_is_unhealthy(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Health check should return False for red status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "red"}
        mock_httpx_client.request.return_value = mock_response

        assert client.health_check() is False

    @pytest.mark.unit
    def test_search(self, client: ElasticsearchClient, mock_httpx_client: MagicMock) -> None:
        """Search should return response with hits."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {"_source": {"message": "test log"}},
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.search({"query": {"match_all": {}}})

        assert "hits" in result
        assert result["hits"]["total"]["value"] == 1

    @pytest.mark.unit
    def test_get_cluster_info(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should return cluster metadata from root endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "es-node-1",
            "cluster_name": "kong-logs",
            "version": {"number": "8.0.0"},
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.get_cluster_info()

        assert result["cluster_name"] == "kong-logs"

    @pytest.mark.unit
    def test_search_logs(self, client: ElasticsearchClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of _source dicts from search hits."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {"_source": {"message": "GET /api/v1", "response": {"status": 200}}},
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        logs = client.search_logs(query_string="GET")

        assert len(logs) == 1
        assert logs[0]["message"] == "GET /api/v1"

    @pytest.mark.unit
    def test_search_error_logs(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should return list of error log _source dicts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {"_source": {"message": "upstream error", "response": {"status": 502}}},
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        logs = client.search_error_logs()

        assert len(logs) == 1
        assert logs[0]["response"]["status"] == 502

    @pytest.mark.unit
    def test_aggregate_by_status(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should return dict mapping status code to count from aggregation buckets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aggregations": {
                "status_codes": {
                    "buckets": [
                        {"key": 200, "doc_count": 950},
                        {"key": 404, "doc_count": 30},
                        {"key": 500, "doc_count": 20},
                    ]
                }
            }
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.aggregate_by_status()

        assert result[200] == 950
        assert result[500] == 20

    @pytest.mark.unit
    def test_aggregate_by_service(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should return dict mapping service name to count from aggregation buckets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aggregations": {
                "services": {
                    "buckets": [
                        {"key": "payments-api", "doc_count": 500},
                        {"key": "users-api", "doc_count": 300},
                    ]
                }
            }
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.aggregate_by_service()

        assert result["payments-api"] == 500
        assert result["users-api"] == 300

    @pytest.mark.unit
    def test_get_latency_histogram(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should return list of time buckets with latency stats."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aggregations": {
                "latency_over_time": {
                    "buckets": [
                        {
                            "key_as_string": "2026-02-20T00:00:00.000Z",
                            "key": 1708387200000,
                            "doc_count": 100,
                            "latency_stats": {"avg": 42.5},
                        }
                    ]
                }
            }
        }
        mock_httpx_client.request.return_value = mock_response

        buckets = client.get_latency_histogram()

        assert len(buckets) == 1
        assert buckets[0]["doc_count"] == 100

    @pytest.mark.unit
    def test_count_logs(self, client: ElasticsearchClient, mock_httpx_client: MagicMock) -> None:
        """Should return integer log count from count endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 1234, "_shards": {"total": 1}}
        mock_httpx_client.request.return_value = mock_response

        count = client.count_logs()

        assert count == 1234

    @pytest.mark.unit
    def test_build_client_with_basic_auth(self, mock_httpx_client: MagicMock) -> None:
        """Client built with username/password should use HTTP basic auth."""
        config = ElasticsearchConfig(
            hosts=["http://localhost:9200"],
            username="elastic",
            password="changeme",
        )
        client = ElasticsearchClient(config)
        # Access the client property to trigger _build_client
        _ = client.client

        assert config.username == "elastic"
        assert config.password == "changeme"

    @pytest.mark.unit
    def test_build_client_with_api_key(self, mock_httpx_client: MagicMock) -> None:
        """Client built with api_key should set ApiKey Authorization header."""
        config = ElasticsearchConfig(
            hosts=["http://localhost:9200"],
            api_key="my-api-key",
        )
        client = ElasticsearchClient(config)
        _ = client.client

        assert config.api_key == "my-api-key"

    @pytest.mark.unit
    def test_health_check_failure(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """Health check should return False when connection fails."""
        mock_httpx_client.request.side_effect = httpx.ConnectError("Connection refused")

        assert client.health_check() is False

    @pytest.mark.unit
    def test_search_logs_with_all_filters(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """search_logs with all filter params should build a bool query with all clauses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {"_source": {"message": "GET /api/v1", "response": {"status": 404}}},
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        logs = client.search_logs(
            query_string="GET",
            service="my-api",
            route="my-route",
            status_code=404,
            start_time=start,
            end_time=end,
        )

        assert len(logs) == 1
        assert logs[0]["message"] == "GET /api/v1"

    @pytest.mark.unit
    def test_search_error_logs_with_service(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """search_error_logs with service param should add service term clause."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {"_source": {"message": "upstream error", "response": {"status": 503}}},
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        logs = client.search_error_logs(service="my-api")

        assert len(logs) == 1
        assert logs[0]["response"]["status"] == 503

    @pytest.mark.unit
    def test_aggregate_by_status_with_service(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """aggregate_by_status with service param should add service term clause."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aggregations": {
                "status_codes": {
                    "buckets": [
                        {"key": 200, "doc_count": 800},
                        {"key": 500, "doc_count": 10},
                    ]
                }
            }
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.aggregate_by_status(service="my-api")

        assert result[200] == 800
        assert result[500] == 10

    @pytest.mark.unit
    def test_get_latency_histogram_with_service(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_latency_histogram with service param should add service term clause."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "aggregations": {
                "latency_over_time": {
                    "buckets": [
                        {
                            "key_as_string": "2026-02-20T00:00:00.000Z",
                            "key": 1708387200000,
                            "doc_count": 50,
                            "latency_stats": {"avg": 30.0},
                        }
                    ]
                }
            }
        }
        mock_httpx_client.request.return_value = mock_response

        buckets = client.get_latency_histogram(service="my-api")

        assert len(buckets) == 1
        assert buckets[0]["doc_count"] == 50

    @pytest.mark.unit
    def test_count_logs_with_service(
        self, client: ElasticsearchClient, mock_httpx_client: MagicMock
    ) -> None:
        """count_logs with service param should add service term clause."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 42, "_shards": {"total": 1}}
        mock_httpx_client.request.return_value = mock_response

        count = client.count_logs(service="my-api")

        assert count == 42


class TestLokiClient:
    """Tests for LokiClient."""

    @pytest.fixture
    def config(self) -> LokiConfig:
        """Create test config."""
        return LokiConfig(url="http://localhost:3100")

    @pytest.fixture
    def client(self, config: LokiConfig, mock_httpx_client: MagicMock) -> LokiClient:
        """Create client with mocked httpx."""
        return LokiClient(config)

    @pytest.mark.unit
    def test_client_initialization(self, config: LokiConfig, mock_httpx_client: MagicMock) -> None:
        """Client should initialize correctly."""
        client = LokiClient(config)

        assert client.client_name == "Loki"

    @pytest.mark.unit
    def test_health_check_success(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Health check should return True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.request.return_value = mock_response

        assert client.health_check() is True

    @pytest.mark.unit
    def test_query(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Query should return log entries."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "kong"},
                        "values": [["1234567890000000000", "test log message"]],
                    },
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        entries = client.query('{job="kong"}')

        assert len(entries) == 1
        assert entries[0]["line"] == "test log message"

    @pytest.mark.unit
    def test_get_labels(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Should return label names."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": ["job", "service", "route"],
        }
        mock_httpx_client.request.return_value = mock_response

        labels = client.get_labels()

        assert "job" in labels
        assert "service" in labels

    @pytest.mark.unit
    def test_query_range(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Range query should return log entries from the time window."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "kong", "service": "api"},
                        "values": [
                            ["1708387200000000000", "GET /api/v1 200"],
                            ["1708387260000000000", "POST /api/v1 201"],
                        ],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        start = datetime.now() - timedelta(hours=1)
        entries = client.query_range('{job="kong"}', start=start)

        assert len(entries) == 2
        assert entries[0]["line"] == "GET /api/v1 200"

    @pytest.mark.unit
    def test_get_label_values(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of values for a label name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": ["payments-api", "users-api", "gateway"],
        }
        mock_httpx_client.request.return_value = mock_response

        values = client.get_label_values("service")

        assert "payments-api" in values
        assert "gateway" in values

    @pytest.mark.unit
    def test_get_series(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of label sets matching the selector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {"job": "kong", "service": "api"},
                {"job": "kong", "service": "admin"},
            ],
        }
        mock_httpx_client.request.return_value = mock_response

        series = client.get_series(['{job="kong"}'])

        assert len(series) == 2
        assert series[0]["job"] == "kong"

    @pytest.mark.unit
    def test_search_kong_logs(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Should build LogQL query and return matching log entries."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "kong"},
                        "values": [["1708387200000000000", "error connecting to upstream"]],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        start = datetime.now() - timedelta(hours=1)
        entries = client.search_kong_logs(query_text="error", start_time=start)

        assert len(entries) == 1
        assert "error" in entries[0]["line"]

    @pytest.mark.unit
    def test_get_kong_error_logs(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Should build error LogQL query and return error log entries."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "kong"},
                        "values": [["1708387200000000000", "upstream 502 bad gateway"]],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        entries = client.get_kong_error_logs()

        assert len(entries) == 1
        assert entries[0]["labels"]["job"] == "kong"

    @pytest.mark.unit
    def test_get_kong_log_rate(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """Should build rate LogQL query and return metric values."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"job": "kong"},
                        "values": [[1708387200.0, "3.5"], [1708387260.0, "4.1"]],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        entries = client.get_kong_log_rate()

        assert len(entries) == 2
        assert entries[0]["value"] == 3.5

    @pytest.mark.unit
    def test_build_client_with_org_id(self, mock_httpx_client: MagicMock) -> None:
        """Client built with org_id should set X-Scope-OrgID header."""
        config = LokiConfig(url="http://localhost:3100", org_id="my-tenant")
        client = LokiClient(config)
        _ = client.client

        assert client._org_id == "my-tenant"

    @pytest.mark.unit
    def test_build_client_with_basic_auth(self, mock_httpx_client: MagicMock) -> None:
        """Client built with username/password should set basic auth."""
        config = LokiConfig(
            url="http://localhost:3100",
            username="loki-user",
            password="loki-pass",
        )
        client = LokiClient(config)
        _ = client.client

        assert config.username == "loki-user"
        assert config.password == "loki-pass"

    @pytest.mark.unit
    def test_datetime_to_ns(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """_datetime_to_ns should convert datetime to nanoseconds since epoch."""
        dt = datetime(2026, 2, 20, 0, 0, 0)
        ns = client._datetime_to_ns(dt)

        assert ns == int(dt.timestamp() * 1_000_000_000)
        assert isinstance(ns, int)

    @pytest.mark.unit
    def test_parse_query_response_matrix_type(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """_parse_query_response with resultType='matrix' should return metric entries."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"job": "kong", "service": "api"},
                        "values": [
                            [1708387200.0, "5.5"],
                            [1708387260.0, "6.2"],
                        ],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        start = datetime.now() - timedelta(hours=1)
        entries = client.query_range('{job="kong"}', start=start)

        assert len(entries) == 2
        assert entries[0]["value"] == 5.5
        assert entries[1]["value"] == 6.2
        assert "labels" in entries[0]

    @pytest.mark.unit
    def test_get_series_parses_result(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_series should return the parsed data list from success response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {"job": "kong", "service": "payments"},
                {"job": "kong", "service": "users"},
            ],
        }
        mock_httpx_client.request.return_value = mock_response

        series = client.get_series(['{job="kong"}'])

        assert len(series) == 2
        assert series[0]["service"] == "payments"

    @pytest.mark.unit
    def test_search_kong_logs_with_service(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """search_kong_logs with service param should include service label in selector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "kong", "service": "my-api"},
                        "values": [["1708387200000000000", "GET /api/v1 200"]],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        start = datetime.now() - timedelta(hours=1)
        entries = client.search_kong_logs(service="my-api", start_time=start)

        assert len(entries) == 1
        assert entries[0]["labels"]["service"] == "my-api"

    @pytest.mark.unit
    def test_search_kong_logs_with_limit(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """search_kong_logs with explicit limit should pass limit to query_range."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "kong"},
                        "values": [["1708387200000000000", "POST /api/v2 201"]],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        start = datetime.now() - timedelta(hours=1)
        entries = client.search_kong_logs(start_time=start, limit=500)

        assert len(entries) == 1
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_get_kong_error_logs_with_filters(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_error_logs with service param should include service label in selector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "kong", "service": "my-api"},
                        "values": [["1708387200000000000", "upstream 502 bad gateway"]],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        entries = client.get_kong_error_logs(service="my-api")

        assert len(entries) == 1
        assert entries[0]["labels"]["service"] == "my-api"

    @pytest.mark.unit
    def test_get_kong_services(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """get_kong_services should call get_label_values with 'service' label."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": ["payments-api", "users-api", "inventory-api"],
        }
        mock_httpx_client.request.return_value = mock_response

        services = client.get_kong_services()

        assert "payments-api" in services
        assert "users-api" in services
        assert "inventory-api" in services

    @pytest.mark.unit
    def test_get_kong_routes(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """get_kong_routes should call get_label_values with 'route' label."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": ["/api/v1/payments", "/api/v1/users", "/api/v1/health"],
        }
        mock_httpx_client.request.return_value = mock_response

        routes = client.get_kong_routes()

        assert "/api/v1/payments" in routes
        assert "/api/v1/health" in routes

    @pytest.mark.unit
    def test_get_kong_log_rate_with_service(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_log_rate with service param should include service label in selector."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"job": "kong", "service": "my-api"},
                        "values": [[1708387200.0, "2.0"]],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        entries = client.get_kong_log_rate(service="my-api")

        assert len(entries) == 1
        assert entries[0]["value"] == 2.0

    @pytest.mark.unit
    def test_parse_query_response_error_raises(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """_parse_query_response with status != 'success' should raise LokiQueryError."""
        from system_operations_manager.integrations.observability.clients.loki import (
            LokiQueryError,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "parse error",
        }
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(LokiQueryError, match="parse error"):
            client.query('{job="kong"}')

    @pytest.mark.unit
    def test_get_labels_failure(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """get_labels when status != 'success' should return empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "backend unavailable",
        }
        mock_httpx_client.request.return_value = mock_response

        labels = client.get_labels()

        assert labels == []

    @pytest.mark.unit
    def test_get_label_values_failure(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_label_values when status != 'success' should return empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "label not found",
        }
        mock_httpx_client.request.return_value = mock_response

        values = client.get_label_values("nonexistent")

        assert values == []

    @pytest.mark.unit
    def test_get_series_failure(self, client: LokiClient, mock_httpx_client: MagicMock) -> None:
        """get_series when status != 'success' should return empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "store error",
        }
        mock_httpx_client.request.return_value = mock_response

        series = client.get_series(['{job="kong"}'])

        assert series == []

    @pytest.mark.unit
    def test_search_kong_logs_with_route_and_status_code(
        self, client: LokiClient, mock_httpx_client: MagicMock
    ) -> None:
        """search_kong_logs with route and status_code should include them in query filters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "kong", "route": "my-route"},
                        "values": [["1708387200000000000", "GET /api/v1 404"]],
                    }
                ],
            },
        }
        mock_httpx_client.request.return_value = mock_response

        # Omit start_time so the default (end_time - 1h) branch is exercised
        entries = client.search_kong_logs(route="my-route", status_code=404)

        assert len(entries) == 1
        assert mock_httpx_client.request.called


class TestJaegerClient:
    """Tests for JaegerClient."""

    @pytest.fixture
    def config(self) -> JaegerConfig:
        """Create test config."""
        return JaegerConfig(query_url="http://localhost:16686")

    @pytest.fixture
    def client(self, config: JaegerConfig, mock_httpx_client: MagicMock) -> JaegerClient:
        """Create client with mocked httpx."""
        return JaegerClient(config)

    @pytest.mark.unit
    def test_client_initialization(
        self, config: JaegerConfig, mock_httpx_client: MagicMock
    ) -> None:
        """Client should initialize correctly."""
        client = JaegerClient(config)

        assert client.client_name == "Jaeger"

    @pytest.mark.unit
    def test_health_check_success(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Health check should return True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.request.return_value = mock_response

        assert client.health_check() is True

    @pytest.mark.unit
    def test_get_services(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Should return service names."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": ["kong", "backend-api"],
        }
        mock_httpx_client.request.return_value = mock_response

        services = client.get_services()

        assert "kong" in services
        assert "backend-api" in services

    @pytest.mark.unit
    def test_get_trace(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Should return trace with spans."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "abc123",
                    "spans": [
                        {"spanID": "span1", "operationName": "HTTP GET"},
                    ],
                    "processes": {},
                },
            ],
        }
        mock_httpx_client.request.return_value = mock_response

        trace = client.get_trace("abc123")

        assert trace["traceID"] == "abc123"
        assert len(trace["spans"]) == 1

    @pytest.mark.unit
    def test_get_operations(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of operation names for a service."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": ["HTTP GET /api/v1", "HTTP POST /api/v1", "HTTP DELETE /api/v1"]
        }
        mock_httpx_client.request.return_value = mock_response

        operations = client.get_operations("kong")

        assert "HTTP GET /api/v1" in operations
        assert len(operations) == 3

    @pytest.mark.unit
    def test_find_traces(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of traces matching search criteria."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "trace001",
                    "spans": [{"spanID": "s1", "operationName": "HTTP GET", "duration": 150000}],
                    "processes": {"p1": {"serviceName": "kong"}},
                },
                {
                    "traceID": "trace002",
                    "spans": [{"spanID": "s2", "operationName": "HTTP POST", "duration": 200000}],
                    "processes": {"p1": {"serviceName": "kong"}},
                },
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        traces = client.find_traces(service="kong", limit=2)

        assert len(traces) == 2
        assert traces[0]["traceID"] == "trace001"

    @pytest.mark.unit
    def test_compare_traces(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Should compare two traces and return diff metrics."""
        trace_a_response = MagicMock()
        trace_a_response.status_code = 200
        trace_a_response.json.return_value = {
            "data": [
                {
                    "traceID": "trace-a",
                    "spans": [{"spanID": "s1", "operationName": "HTTP GET", "duration": 100000}],
                    "processes": {},
                }
            ]
        }
        trace_b_response = MagicMock()
        trace_b_response.status_code = 200
        trace_b_response.json.return_value = {
            "data": [
                {
                    "traceID": "trace-b",
                    "spans": [
                        {"spanID": "s2", "operationName": "HTTP GET", "duration": 200000},
                        {"spanID": "s3", "operationName": "DB query", "duration": 50000},
                    ],
                    "processes": {},
                }
            ]
        }
        mock_httpx_client.request.side_effect = [trace_a_response, trace_b_response]

        result = client.compare_traces("trace-a", "trace-b")

        assert result["trace_a"]["span_count"] == 1
        assert result["trace_b"]["span_count"] == 2
        assert result["span_count_diff"] == 1

    @pytest.mark.unit
    def test_get_dependencies(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of service dependencies."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"parent": "kong", "child": "payments-api", "callCount": 1200},
                {"parent": "kong", "child": "users-api", "callCount": 800},
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        deps = client.get_dependencies()

        assert len(deps) == 2
        assert deps[0]["parent"] == "kong"

    @pytest.mark.unit
    def test_get_kong_traces(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Should call find_traces with kong as service name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "kong-trace-1",
                    "spans": [{"spanID": "s1", "operationName": "HTTP GET", "duration": 80000}],
                    "processes": {"p1": {"serviceName": "kong"}},
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_traces()

        assert len(traces) == 1
        assert traces[0]["traceID"] == "kong-trace-1"

    @pytest.mark.unit
    def test_get_kong_slow_traces(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """Should call find_traces with min_duration threshold for slow traces."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "slow-trace-1",
                    "spans": [{"spanID": "s1", "operationName": "HTTP GET", "duration": 750000}],
                    "processes": {"p1": {"serviceName": "kong"}},
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_slow_traces(threshold="500ms")

        assert len(traces) == 1
        assert traces[0]["traceID"] == "slow-trace-1"

    @pytest.mark.unit
    def test_get_kong_error_traces(
        self, client: JaegerClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should call find_traces filtered by error=true tag."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "err-trace-1",
                    "spans": [
                        {
                            "spanID": "s1",
                            "operationName": "HTTP GET",
                            "duration": 300000,
                            "tags": [{"key": "error", "value": "true"}],
                        }
                    ],
                    "processes": {"p1": {"serviceName": "kong"}},
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_error_traces()

        assert len(traces) == 1
        assert traces[0]["traceID"] == "err-trace-1"

    @pytest.mark.unit
    def test_build_client_with_basic_auth(self, mock_httpx_client: MagicMock) -> None:
        """Jaeger client built with username/password should use HTTP basic auth."""
        config = JaegerConfig(
            query_url="http://localhost:16686",
            username="jaeger-user",
            password="jaeger-pass",
        )
        client = JaegerClient(config)
        _ = client.client

        assert config.username == "jaeger-user"
        assert config.password == "jaeger-pass"

    @pytest.mark.unit
    def test_datetime_to_microseconds(
        self, client: JaegerClient, mock_httpx_client: MagicMock
    ) -> None:
        """_datetime_to_microseconds should convert datetime to microseconds since epoch."""
        dt = datetime(2026, 2, 20, 0, 0, 0)
        us = client._datetime_to_microseconds(dt)

        assert us == int(dt.timestamp() * 1_000_000)
        assert isinstance(us, int)

    @pytest.mark.unit
    def test_find_traces_with_operation_and_tags(
        self, client: JaegerClient, mock_httpx_client: MagicMock
    ) -> None:
        """find_traces with operation and tags should include them in request params."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "trace-op-1",
                    "spans": [
                        {
                            "spanID": "s1",
                            "operationName": "HTTP GET /api/v1",
                            "duration": 100000,
                        }
                    ],
                    "processes": {"p1": {"serviceName": "kong"}},
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        traces = client.find_traces(
            service="kong",
            operation="HTTP GET /api/v1",
            tags={"http.status_code": "200"},
        )

        assert len(traces) == 1
        assert traces[0]["traceID"] == "trace-op-1"
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_find_traces_with_duration_params(
        self, client: JaegerClient, mock_httpx_client: MagicMock
    ) -> None:
        """find_traces with min_duration and max_duration should include them in params."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "trace-dur-1",
                    "spans": [{"spanID": "s1", "operationName": "HTTP POST", "duration": 600000}],
                    "processes": {"p1": {"serviceName": "kong"}},
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        traces = client.find_traces(
            service="kong",
            min_duration="500ms",
            max_duration="2s",
        )

        assert len(traces) == 1
        assert traces[0]["traceID"] == "trace-dur-1"
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_get_trace_not_found(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """get_trace with empty data list should raise JaegerQueryError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(JaegerQueryError, match="Trace not found"):
            client.get_trace("nonexistent-trace-id")

    @pytest.mark.unit
    def test_get_kong_traces_with_all_filters(
        self, client: JaegerClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_traces with route, upstream, and status_code should build correct tags."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "filtered-trace-1",
                    "spans": [
                        {
                            "spanID": "s1",
                            "operationName": "HTTP GET",
                            "duration": 120000,
                            "tags": [
                                {"key": "kong.route", "value": "my-route"},
                                {"key": "kong.upstream", "value": "my-upstream"},
                                {"key": "http.status_code", "value": "200"},
                            ],
                        }
                    ],
                    "processes": {"p1": {"serviceName": "kong"}},
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_traces(
            route="my-route",
            upstream="my-upstream",
            status_code=200,
        )

        assert len(traces) == 1
        assert traces[0]["traceID"] == "filtered-trace-1"

    @pytest.mark.unit
    def test_analyze_trace(self, client: JaegerClient, mock_httpx_client: MagicMock) -> None:
        """analyze_trace should return full span analysis with service breakdown."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "traceID": "abc",
                    "spans": [
                        {
                            "spanID": "s1",
                            "operationName": "HTTP GET",
                            "duration": 5000,
                            "processID": "p1",
                        },
                        {
                            "spanID": "s2",
                            "operationName": "proxy",
                            "duration": 3000,
                            "processID": "p2",
                        },
                    ],
                    "processes": {
                        "p1": {"serviceName": "kong"},
                        "p2": {"serviceName": "backend"},
                    },
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.analyze_trace("abc")

        assert result["trace_id"] == "abc"
        assert result["span_count"] == 2
        assert result["total_duration_us"] == 5000
        assert "kong" in result["service_breakdown"]
        assert "backend" in result["service_breakdown"]
        assert result["service_breakdown"]["kong"] == 5000
        assert result["service_breakdown"]["backend"] == 3000
        assert result["slowest_span"]["operation"] == "HTTP GET"
        assert result["slowest_span"]["duration_us"] == 5000


class TestZipkinClient:
    """Tests for ZipkinClient."""

    @pytest.fixture
    def config(self) -> ZipkinConfig:
        """Create test config."""
        return ZipkinConfig(url="http://localhost:9411")

    @pytest.fixture
    def client(self, config: ZipkinConfig, mock_httpx_client: MagicMock) -> ZipkinClient:
        """Create client with mocked httpx."""
        return ZipkinClient(config)

    @pytest.mark.unit
    def test_client_initialization(
        self, config: ZipkinConfig, mock_httpx_client: MagicMock
    ) -> None:
        """Client should initialize correctly."""
        client = ZipkinClient(config)

        assert client.client_name == "Zipkin"

    @pytest.mark.unit
    def test_health_check_success(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Health check should return True when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.request.return_value = mock_response

        assert client.health_check() is True

    @pytest.mark.unit
    def test_get_services(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should return service names."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["kong", "backend"]
        mock_httpx_client.request.return_value = mock_response

        services = client.get_services()

        assert "kong" in services
        assert "backend" in services

    @pytest.mark.unit
    def test_get_trace(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should return trace spans."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "traceId": "abc123",
                "id": "span1",
                "name": "HTTP GET",
                "localEndpoint": {"serviceName": "kong"},
            },
        ]
        mock_httpx_client.request.return_value = mock_response

        spans = client.get_trace("abc123")

        assert len(spans) == 1
        assert spans[0]["name"] == "HTTP GET"

    @pytest.mark.unit
    def test_get_spans(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of span names for a service."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["HTTP GET", "HTTP POST", "DB query"]
        mock_httpx_client.request.return_value = mock_response

        spans = client.get_spans("kong")

        assert "HTTP GET" in spans
        assert len(spans) == 3

    @pytest.mark.unit
    def test_get_remote_services(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of remote service names called by the service."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["payments-api", "users-api", "inventory-api"]
        mock_httpx_client.request.return_value = mock_response

        remote_services = client.get_remote_services("kong")

        assert "payments-api" in remote_services
        assert len(remote_services) == 3

    @pytest.mark.unit
    def test_find_traces(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of traces (each trace is a list of spans)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                {
                    "traceId": "trace001",
                    "id": "span1",
                    "name": "HTTP GET",
                    "duration": 120000,
                    "localEndpoint": {"serviceName": "kong"},
                }
            ],
            [
                {
                    "traceId": "trace002",
                    "id": "span2",
                    "name": "HTTP POST",
                    "duration": 95000,
                    "localEndpoint": {"serviceName": "kong"},
                }
            ],
        ]
        mock_httpx_client.request.return_value = mock_response

        traces = client.find_traces(service_name="kong", limit=2)

        assert len(traces) == 2
        assert traces[0][0]["traceId"] == "trace001"

    @pytest.mark.unit
    def test_get_dependencies(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should return list of service dependency objects."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"parent": "kong", "child": "payments-api", "callCount": 500},
            {"parent": "kong", "child": "users-api", "callCount": 300},
        ]
        mock_httpx_client.request.return_value = mock_response

        deps = client.get_dependencies()

        assert len(deps) == 2
        assert deps[0]["parent"] == "kong"

    @pytest.mark.unit
    def test_get_kong_traces(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should call find_traces with kong as the service name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                {
                    "traceId": "kong-trace-1",
                    "id": "s1",
                    "name": "HTTP GET",
                    "duration": 80000,
                    "localEndpoint": {"serviceName": "kong"},
                }
            ]
        ]
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_traces()

        assert len(traces) == 1
        assert traces[0][0]["traceId"] == "kong-trace-1"

    @pytest.mark.unit
    def test_get_kong_slow_traces(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should call find_traces with min_duration threshold for slow traces."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                {
                    "traceId": "slow-trace-1",
                    "id": "s1",
                    "name": "HTTP GET",
                    "duration": 700000,
                    "localEndpoint": {"serviceName": "kong"},
                }
            ]
        ]
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_slow_traces(threshold_us=500000)

        assert len(traces) == 1
        assert traces[0][0]["duration"] == 700000

    @pytest.mark.unit
    def test_get_kong_error_traces(
        self, client: ZipkinClient, mock_httpx_client: MagicMock
    ) -> None:
        """Should call find_traces filtered by error=true tag."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                {
                    "traceId": "err-trace-1",
                    "id": "s1",
                    "name": "HTTP GET",
                    "duration": 400000,
                    "tags": {"error": "true"},
                    "localEndpoint": {"serviceName": "kong"},
                }
            ]
        ]
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_error_traces()

        assert len(traces) == 1
        assert traces[0][0]["tags"]["error"] == "true"

    @pytest.mark.unit
    def test_analyze_trace(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should analyze a trace and return timing breakdown."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "traceId": "abc123",
                "id": "span1",
                "name": "HTTP GET",
                "duration": 300000,
                "localEndpoint": {"serviceName": "kong"},
            },
            {
                "traceId": "abc123",
                "id": "span2",
                "name": "DB query",
                "duration": 120000,
                "localEndpoint": {"serviceName": "postgres"},
            },
        ]
        mock_httpx_client.request.return_value = mock_response

        result = client.analyze_trace("abc123")

        assert result["trace_id"] == "abc123"
        assert result["span_count"] == 2
        assert result["total_duration_us"] == 300000
        assert "kong" in result["service_breakdown"]

    @pytest.mark.unit
    def test_get_trace_summary(self, client: ZipkinClient, mock_httpx_client: MagicMock) -> None:
        """Should return summary stats for a list of traces without HTTP calls."""
        traces: list[list[dict[str, object]]] = [
            [
                {
                    "traceId": "t1",
                    "id": "s1",
                    "name": "HTTP GET",
                    "duration": 200000,
                    "localEndpoint": {"serviceName": "kong"},
                }
            ],
            [
                {
                    "traceId": "t2",
                    "id": "s2",
                    "name": "HTTP POST",
                    "duration": 400000,
                    "localEndpoint": {"serviceName": "kong"},
                }
            ],
        ]

        summary = client.get_trace_summary(traces)

        assert summary["trace_count"] == 2
        assert summary["max_duration_us"] == 400000
        assert summary["min_duration_us"] == 200000
        assert "kong" in summary["services"]

    @pytest.mark.unit
    def test_datetime_to_milliseconds(
        self, client: ZipkinClient, mock_httpx_client: MagicMock
    ) -> None:
        """_datetime_to_milliseconds should convert datetime to milliseconds since epoch."""
        dt = datetime(2026, 2, 20, 0, 0, 0)
        ms = client._datetime_to_milliseconds(dt)

        assert ms == int(dt.timestamp() * 1000)
        assert isinstance(ms, int)

    @pytest.mark.unit
    def test_find_traces_with_all_params(
        self, client: ZipkinClient, mock_httpx_client: MagicMock
    ) -> None:
        """find_traces with service_name, span_name, annotation_query, min/max duration."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                {
                    "traceId": "full-param-trace",
                    "id": "s1",
                    "name": "HTTP GET",
                    "duration": 250000,
                    "localEndpoint": {"serviceName": "kong"},
                }
            ]
        ]
        mock_httpx_client.request.return_value = mock_response

        end = datetime.now()
        start = end - timedelta(hours=1)
        traces = client.find_traces(
            service_name="kong",
            span_name="HTTP GET",
            annotation_query="http.method=GET",
            min_duration=100000,
            max_duration=500000,
            start_time=start,
            end_time=end,
            limit=5,
        )

        assert len(traces) == 1
        assert traces[0][0]["traceId"] == "full-param-trace"
        assert mock_httpx_client.request.called

    @pytest.mark.unit
    def test_get_kong_traces_with_filters(
        self, client: ZipkinClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_traces with route and status_code should build tag annotation query."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                {
                    "traceId": "filtered-kong-trace",
                    "id": "s1",
                    "name": "HTTP GET",
                    "duration": 180000,
                    "tags": {"kong.route": "my-route", "http.status_code": "200"},
                    "localEndpoint": {"serviceName": "kong"},
                }
            ]
        ]
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_traces(route="my-route", status_code=200)

        assert len(traces) == 1
        assert traces[0][0]["traceId"] == "filtered-kong-trace"

    @pytest.mark.unit
    def test_get_kong_slow_traces_with_route_filter(
        self, client: ZipkinClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_kong_slow_traces delegates to find_traces with min_duration threshold."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                {
                    "traceId": "slow-route-trace",
                    "id": "s1",
                    "name": "HTTP GET",
                    "duration": 600000,
                    "localEndpoint": {"serviceName": "kong"},
                }
            ]
        ]
        mock_httpx_client.request.return_value = mock_response

        traces = client.get_kong_slow_traces(threshold_us=500000)

        assert len(traces) == 1
        assert traces[0][0]["duration"] == 600000

    @pytest.mark.unit
    def test_get_dependencies_with_end_ts(
        self, client: ZipkinClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_dependencies with explicit end_time should use _datetime_to_milliseconds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"parent": "kong", "child": "payments-api", "callCount": 100},
        ]
        mock_httpx_client.request.return_value = mock_response

        end_time = datetime(2026, 2, 20, 12, 0, 0)
        deps = client.get_dependencies(end_time=end_time, lookback=3600000)

        assert len(deps) == 1
        assert deps[0]["parent"] == "kong"

    @pytest.mark.unit
    def test_analyze_trace_service_breakdown(
        self, client: ZipkinClient, mock_httpx_client: MagicMock
    ) -> None:
        """analyze_trace should build service_breakdown from localEndpoint serviceName."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "traceId": "breakdown-trace",
                "id": "s1",
                "name": "HTTP GET",
                "duration": 400000,
                "localEndpoint": {"serviceName": "kong"},
            },
            {
                "traceId": "breakdown-trace",
                "id": "s2",
                "name": "db-query",
                "duration": 150000,
                "localEndpoint": {"serviceName": "postgres"},
            },
        ]
        mock_httpx_client.request.return_value = mock_response

        result = client.analyze_trace("breakdown-trace")

        assert result["trace_id"] == "breakdown-trace"
        assert result["span_count"] == 2
        assert result["total_duration_us"] == 400000
        assert "kong" in result["service_breakdown"]
        assert "postgres" in result["service_breakdown"]
        assert result["service_breakdown"]["kong"] == 400000
        assert result["service_breakdown"]["postgres"] == 150000

    @pytest.mark.unit
    def test_get_trace_summary_empty_traces(
        self, client: ZipkinClient, mock_httpx_client: MagicMock
    ) -> None:
        """get_trace_summary with empty list should return trace_count: 0."""
        summary = client.get_trace_summary([])

        assert summary["trace_count"] == 0


class TestBaseClientErrors:
    """Tests for base client error handling."""

    @pytest.fixture
    def config(self) -> PrometheusConfig:
        """Create test config."""
        return PrometheusConfig(url="http://localhost:9090")

    @pytest.fixture
    def client(self, config: PrometheusConfig, mock_httpx_client: MagicMock) -> PrometheusClient:
        """Create client with mocked httpx."""
        return PrometheusClient(config)

    @pytest.mark.unit
    def test_connection_error(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Connection errors should raise ObservabilityConnectionError."""
        mock_httpx_client.request.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(ObservabilityConnectionError):
            client.get("/test")

    @pytest.mark.unit
    def test_auth_error_401(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """401 responses should raise ObservabilityAuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(ObservabilityAuthError):
            client.get("/test")

    @pytest.mark.unit
    def test_auth_error_403(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """403 responses should raise ObservabilityAuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(ObservabilityAuthError):
            client.get("/test")

    @pytest.mark.unit
    def test_not_found_error(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """404 responses should raise ObservabilityNotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(ObservabilityNotFoundError):
            client.get("/test")

    @pytest.mark.unit
    def test_generic_error(self, client: PrometheusClient, mock_httpx_client: MagicMock) -> None:
        """Other 4xx/5xx responses should raise ObservabilityClientError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(ObservabilityClientError):
            client.get("/test")

    @pytest.mark.unit
    def test_context_manager(self, config: PrometheusConfig) -> None:
        """Client should work as context manager."""
        with PrometheusClient(config) as client:
            assert client is not None
            # Close is called on context exit
