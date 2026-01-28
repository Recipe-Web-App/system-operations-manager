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
