"""Unit tests for Konnect API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import SecretStr

from system_operations_manager.integrations.konnect.client import KonnectClient
from system_operations_manager.integrations.konnect.config import (
    KonnectConfig,
    KonnectRegion,
)
from system_operations_manager.integrations.konnect.exceptions import (
    KonnectAuthError,
    KonnectConnectionError,
    KonnectNotFoundError,
)
from system_operations_manager.integrations.konnect.models import (
    ControlPlane,
    DataPlaneCertificate,
)


@pytest.fixture
def konnect_config() -> KonnectConfig:
    """Create a test Konnect config."""
    return KonnectConfig(
        token=SecretStr("test-token"),
        region=KonnectRegion.US,
    )


@pytest.fixture
def mock_httpx_client(mocker: Any) -> MagicMock:
    """Create a mock httpx client."""
    mock_client = MagicMock(spec=httpx.Client)
    mocker.patch("httpx.Client", return_value=mock_client)
    return mock_client


class TestKonnectClientInit:
    """Tests for KonnectClient initialization."""

    @pytest.mark.unit
    def test_client_initialization(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Client should initialize with config."""
        client = KonnectClient(konnect_config)
        assert client is not None
        assert client.config == konnect_config

    @pytest.mark.unit
    def test_client_context_manager(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Client should support context manager."""
        with KonnectClient(konnect_config) as client:
            assert client is not None
        mock_httpx_client.close.assert_called_once()


class TestKonnectClientRequests:
    """Tests for KonnectClient HTTP requests."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        """Create a client with mocked httpx."""
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_successful_request(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Successful request should return JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.request.return_value = mock_response

        result = client._request("GET", "/v2/control-planes")
        assert result == {"data": []}

    @pytest.mark.unit
    def test_401_raises_auth_error(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """401 response should raise KonnectAuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(KonnectAuthError) as exc_info:
            client._request("GET", "/v2/control-planes")
        assert "Invalid Konnect API token" in str(exc_info.value)

    @pytest.mark.unit
    def test_403_raises_auth_error(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """403 response should raise KonnectAuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(KonnectAuthError) as exc_info:
            client._request("GET", "/v2/control-planes")
        assert "Access denied" in str(exc_info.value)

    @pytest.mark.unit
    def test_404_raises_not_found_error(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """404 response should raise KonnectNotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(KonnectNotFoundError):
            client._request("GET", "/v2/control-planes/invalid")

    @pytest.mark.unit
    def test_connection_error_raises_konnect_error(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Connection error should raise KonnectConnectionError."""
        mock_httpx_client.request.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(KonnectConnectionError):
            client._request("GET", "/v2/control-planes")

    @pytest.mark.unit
    def test_timeout_raises_connection_error(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Timeout should raise KonnectConnectionError."""
        mock_httpx_client.request.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(KonnectConnectionError):
            client._request("GET", "/v2/control-planes")

    @pytest.mark.unit
    def test_204_returns_empty_dict(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """204 response should return empty dict."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_httpx_client.request.return_value = mock_response

        result = client._request("DELETE", "/v2/control-planes/123")
        assert result == {}


class TestKonnectClientControlPlanes:
    """Tests for control plane methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        """Create a client with mocked httpx."""
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_control_planes(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_control_planes should return list of ControlPlane."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "cp-1",
                    "name": "test-cp",
                    "config": {
                        "control_plane_endpoint": "https://test.cp0.konghq.com",
                        "telemetry_endpoint": "https://test.tp0.konghq.com",
                    },
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.list_control_planes()

        assert len(result) == 1
        assert isinstance(result[0], ControlPlane)
        assert result[0].id == "cp-1"
        assert result[0].name == "test-cp"

    @pytest.mark.unit
    def test_get_control_plane(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_control_plane should return ControlPlane."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "cp-1",
            "name": "test-cp",
            "config": {},
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.get_control_plane("cp-1")

        assert isinstance(result, ControlPlane)
        assert result.id == "cp-1"

    @pytest.mark.unit
    def test_find_control_plane_by_id(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """find_control_plane should find by UUID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345678-1234-1234-1234-123456789abc",
            "name": "test-cp",
            "config": {},
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.find_control_plane("12345678-1234-1234-1234-123456789abc")

        assert result.id == "12345678-1234-1234-1234-123456789abc"

    @pytest.mark.unit
    def test_find_control_plane_by_name(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """find_control_plane should find by name when not UUID."""
        # First call to list_control_planes
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "cp-1", "name": "test-cp", "config": {}},
                {"id": "cp-2", "name": "other-cp", "config": {}},
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.find_control_plane("test-cp")

        assert result.name == "test-cp"

    @pytest.mark.unit
    def test_find_control_plane_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """find_control_plane should raise NotFoundError when not found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(KonnectNotFoundError):
            client.find_control_plane("nonexistent")


class TestKonnectClientCertificates:
    """Tests for certificate methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        """Create a client with mocked httpx."""
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_dp_certificates(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_dp_certificates should return list of certificates."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "cert-1",
                    "cert": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
                },
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.list_dp_certificates("cp-1")

        assert len(result) == 1
        assert isinstance(result[0], DataPlaneCertificate)
        assert result[0].id == "cert-1"

    @pytest.mark.unit
    def test_create_dp_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_dp_certificate should generate and register certificate."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "item": {
                "id": "cert-1",
                "cert": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            }
        }
        mock_httpx_client.request.return_value = mock_response

        result = client.create_dp_certificate("cp-1")

        assert isinstance(result, DataPlaneCertificate)
        assert result.id == "cert-1"
        assert result.key is not None  # Private key should be set
        assert "PRIVATE KEY" in result.key


class TestKonnectClientHelpers:
    """Tests for helper methods."""

    @pytest.mark.unit
    def test_is_uuid_valid(self) -> None:
        """_is_uuid should return True for valid UUIDs."""
        assert KonnectClient._is_uuid("12345678-1234-1234-1234-123456789abc") is True
        assert KonnectClient._is_uuid("ABCDEF12-1234-1234-1234-123456789ABC") is True

    @pytest.mark.unit
    def test_is_uuid_invalid(self) -> None:
        """_is_uuid should return False for invalid UUIDs."""
        assert KonnectClient._is_uuid("not-a-uuid") is False
        assert KonnectClient._is_uuid("test-control-plane") is False
        assert KonnectClient._is_uuid("") is False

    @pytest.mark.unit
    def test_generate_certificate(self) -> None:
        """_generate_certificate should return valid PEM cert and key."""
        cert_pem, key_pem = KonnectClient._generate_certificate()

        assert "-----BEGIN CERTIFICATE-----" in cert_pem
        assert "-----END CERTIFICATE-----" in cert_pem
        assert "PRIVATE KEY" in key_pem


class TestKonnectClientServices:
    """Tests for service management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        """Create a client with mocked httpx."""
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_services(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_services should return list of services."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "svc-1",
                    "name": "test-service",
                    "host": "test.local",
                    "port": 8080,
                    "protocol": "http",
                }
            ],
            "offset": None,
        }
        mock_httpx_client.request.return_value = mock_response

        services, next_offset = client.list_services("cp-123")

        assert len(services) == 1
        assert services[0].name == "test-service"
        assert services[0].host == "test.local"
        assert next_offset is None
        mock_httpx_client.request.assert_called_once()

    @pytest.mark.unit
    def test_get_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_service should return service details."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "svc-1",
            "name": "test-service",
            "host": "test.local",
            "port": 8080,
            "protocol": "http",
        }
        mock_httpx_client.request.return_value = mock_response

        service = client.get_service("cp-123", "test-service")

        assert service.name == "test-service"
        assert service.host == "test.local"

    @pytest.mark.unit
    def test_get_service_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_service should raise NotFoundError when not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not found"}
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(KonnectNotFoundError):
            client.get_service("cp-123", "nonexistent")

    @pytest.mark.unit
    def test_create_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_service should create and return service."""
        from system_operations_manager.integrations.kong.models.service import Service

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "svc-new",
            "name": "new-service",
            "host": "new.local",
            "port": 80,
            "protocol": "http",
        }
        mock_httpx_client.request.return_value = mock_response

        service = Service(name="new-service", host="new.local")
        result = client.create_service("cp-123", service)

        assert result.id == "svc-new"
        assert result.name == "new-service"

    @pytest.mark.unit
    def test_update_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_service should update and return service."""
        from system_operations_manager.integrations.kong.models.service import Service

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "svc-1",
            "name": "test-service",
            "host": "updated.local",
            "port": 8080,
            "protocol": "http",
        }
        mock_httpx_client.request.return_value = mock_response

        service = Service(name="test-service", host="updated.local")
        result = client.update_service("cp-123", "svc-1", service)

        assert result.host == "updated.local"

    @pytest.mark.unit
    def test_delete_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_service should delete service."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_httpx_client.request.return_value = mock_response

        # Should not raise
        client.delete_service("cp-123", "svc-1")
        mock_httpx_client.request.assert_called_once()


class TestKonnectClientRoutes:
    """Tests for route management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        """Create a client with mocked httpx."""
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_routes(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_routes should return list of routes."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "route-1",
                    "name": "test-route",
                    "paths": ["/api"],
                    "methods": ["GET", "POST"],
                }
            ],
            "offset": None,
        }
        mock_httpx_client.request.return_value = mock_response

        routes, _next_offset = client.list_routes("cp-123")

        assert len(routes) == 1
        assert routes[0].name == "test-route"
        assert routes[0].paths == ["/api"]

    @pytest.mark.unit
    def test_list_routes_by_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_routes should filter by service when specified."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "route-1",
                    "name": "svc-route",
                    "paths": ["/api"],
                    "methods": ["GET"],
                }
            ],
            "offset": None,
        }
        mock_httpx_client.request.return_value = mock_response

        routes, _ = client.list_routes("cp-123", service_name_or_id="test-service")

        assert len(routes) == 1
        # Verify the service-specific endpoint was called
        call_args = mock_httpx_client.request.call_args
        # endpoint is second positional argument
        assert "services/test-service/routes" in call_args[0][1]

    @pytest.mark.unit
    def test_create_route(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_route should create and return route."""
        from system_operations_manager.integrations.kong.models.route import Route

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "route-new",
            "name": "new-route",
            "paths": ["/new"],
            "methods": ["GET"],
        }
        mock_httpx_client.request.return_value = mock_response

        route = Route(name="new-route", paths=["/new"], methods=["GET"])
        result = client.create_route("cp-123", route)

        assert result.id == "route-new"
        assert result.name == "new-route"

    @pytest.mark.unit
    def test_create_route_for_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_route should use service endpoint when service specified."""
        from system_operations_manager.integrations.kong.models.route import Route

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "route-new",
            "name": "new-route",
            "paths": ["/new"],
            "methods": ["GET"],
        }
        mock_httpx_client.request.return_value = mock_response

        route = Route(name="new-route", paths=["/new"], methods=["GET"])
        client.create_route("cp-123", route, service_name_or_id="test-service")

        call_args = mock_httpx_client.request.call_args
        # endpoint is second positional argument
        assert "services/test-service/routes" in call_args[0][1]

    @pytest.mark.unit
    def test_update_route(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_route should update and return route."""
        from system_operations_manager.integrations.kong.models.route import Route

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "route-1",
            "name": "test-route",
            "paths": ["/updated"],
            "methods": ["GET", "POST"],
        }
        mock_httpx_client.request.return_value = mock_response

        route = Route(name="test-route", paths=["/updated"], methods=["GET", "POST"])
        result = client.update_route("cp-123", "route-1", route)

        assert result.paths == ["/updated"]

    @pytest.mark.unit
    def test_delete_route(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_route should delete route."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_httpx_client.request.return_value = mock_response

        # Should not raise
        client.delete_route("cp-123", "route-1")
        mock_httpx_client.request.assert_called_once()
