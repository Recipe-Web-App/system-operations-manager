"""Unit tests for Konnect API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import SecretStr

from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
)
from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.kong.models.enterprise import Vault
from system_operations_manager.integrations.kong.models.key import Key, KeySet
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.upstream import Target, Upstream
from system_operations_manager.integrations.konnect.client import KonnectClient
from system_operations_manager.integrations.konnect.config import (
    KonnectConfig,
    KonnectRegion,
)
from system_operations_manager.integrations.konnect.exceptions import (
    KonnectAPIError,
    KonnectAuthError,
    KonnectConnectionError,
    KonnectNotFoundError,
)
from system_operations_manager.integrations.konnect.models import (
    ControlPlane,
    DataPlaneCertificate,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

CP_ID = "cp-123"


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


def _make_response(status_code: int, json_data: Any = None, text: str = "") -> Any:
    """Helper: build a mock httpx Response."""
    resp: Any = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# TestKonnectClientInit
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TestKonnectClientRequests
# ---------------------------------------------------------------------------


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
        mock_httpx_client.request.return_value = _make_response(200, {"data": []})

        result = client._request("GET", "/v2/control-planes")
        assert result == {"data": []}

    @pytest.mark.unit
    def test_401_raises_auth_error(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """401 response should raise KonnectAuthError."""
        mock_httpx_client.request.return_value = _make_response(401)

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
        mock_httpx_client.request.return_value = _make_response(403)

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
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client._request("GET", "/v2/control-planes/invalid")

    @pytest.mark.unit
    def test_400_raises_api_error_with_json_message(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """4xx (not 401/403/404) should raise KonnectAPIError using JSON message."""
        mock_httpx_client.request.return_value = _make_response(
            400,
            {"message": "bad request"},
            text="bad request",
        )

        with pytest.raises(KonnectAPIError) as exc_info:
            client._request("POST", "/v2/control-planes")
        assert "bad request" in str(exc_info.value)

    @pytest.mark.unit
    def test_400_raises_api_error_with_text_fallback(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """4xx with non-JSON body falls back to response.text."""
        resp: Any = MagicMock()
        resp.status_code = 422
        resp.json.side_effect = ValueError("not json")
        resp.text = "unprocessable entity"
        mock_httpx_client.request.return_value = resp

        with pytest.raises(KonnectAPIError) as exc_info:
            client._request("POST", "/v2/control-planes")
        assert "unprocessable entity" in str(exc_info.value)

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
        mock_httpx_client.request.return_value = _make_response(204)

        result = client._request("DELETE", "/v2/control-planes/123")
        assert result == {}


# ---------------------------------------------------------------------------
# TestKonnectClientValidateToken
# ---------------------------------------------------------------------------


class TestKonnectClientValidateToken:
    """Tests for validate_token method."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_validate_token_success(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """validate_token returns True on successful request."""
        mock_httpx_client.request.return_value = _make_response(200, {"data": []})

        assert client.validate_token() is True

    @pytest.mark.unit
    def test_validate_token_re_raises_auth_error(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """validate_token re-raises KonnectAuthError."""
        mock_httpx_client.request.return_value = _make_response(401)

        with pytest.raises(KonnectAuthError):
            client.validate_token()

    @pytest.mark.unit
    def test_validate_token_returns_true_on_other_api_error(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """validate_token returns True even for non-auth API errors."""
        mock_httpx_client.request.return_value = _make_response(
            500,
            {"message": "server error"},
            text="server error",
        )

        # KonnectAPIError (not auth) => return True
        assert client.validate_token() is True


# ---------------------------------------------------------------------------
# TestKonnectClientControlPlanes
# ---------------------------------------------------------------------------


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
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
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
            },
        )

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
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "cp-1", "name": "test-cp", "config": {}},
        )

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
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "12345678-1234-1234-1234-123456789abc",
                "name": "test-cp",
                "config": {},
            },
        )

        result = client.find_control_plane("12345678-1234-1234-1234-123456789abc")

        assert result.id == "12345678-1234-1234-1234-123456789abc"

    @pytest.mark.unit
    def test_find_control_plane_by_uuid_falls_back_to_name_search(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """find_control_plane falls back to name search when UUID lookup returns 404."""
        uuid_val = "12345678-1234-1234-1234-123456789abc"
        not_found_resp = _make_response(404)
        # The name in the list must match the original name_or_id argument
        list_resp = _make_response(
            200,
            {
                "data": [
                    {"id": "cp-9", "name": uuid_val, "config": {}},
                ]
            },
        )
        mock_httpx_client.request.side_effect = [not_found_resp, list_resp]

        result = client.find_control_plane(uuid_val)

        assert result.name == uuid_val

    @pytest.mark.unit
    def test_find_control_plane_by_name(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """find_control_plane should find by name when not UUID."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [
                    {"id": "cp-1", "name": "test-cp", "config": {}},
                    {"id": "cp-2", "name": "other-cp", "config": {}},
                ]
            },
        )

        result = client.find_control_plane("test-cp")

        assert result.name == "test-cp"

    @pytest.mark.unit
    def test_get_control_plane_by_name_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_control_plane_by_name returns ControlPlane when match exists."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [{"id": "cp-7", "name": "my-cp", "config": {}}]},
        )

        result = client.get_control_plane_by_name("my-cp")

        assert result is not None
        assert result.id == "cp-7"

    @pytest.mark.unit
    def test_get_control_plane_by_name_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_control_plane_by_name returns None when no match."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [{"id": "cp-1", "name": "other-cp", "config": {}}]},
        )

        result = client.get_control_plane_by_name("nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_find_control_plane_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """find_control_plane should raise NotFoundError when not found."""
        mock_httpx_client.request.return_value = _make_response(200, {"data": []})

        with pytest.raises(KonnectNotFoundError):
            client.find_control_plane("nonexistent")


# ---------------------------------------------------------------------------
# TestKonnectClientDPCertificates
# ---------------------------------------------------------------------------


class TestKonnectClientCertificates:
    """Tests for data-plane certificate methods."""

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
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [
                    {
                        "id": "cert-1",
                        "cert": "test-cert-pem-data",
                    },
                ]
            },
        )

        result = client.list_dp_certificates("cp-1")

        assert len(result) == 1
        assert isinstance(result[0], DataPlaneCertificate)
        assert result[0].id == "cert-1"

    @pytest.mark.unit
    def test_get_dp_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_dp_certificate should return a DataPlaneCertificate."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "cert-42",
                "cert": "test-cert-pem-data",
            },
        )

        result = client.get_dp_certificate("cp-1", "cert-42")

        assert isinstance(result, DataPlaneCertificate)
        assert result.id == "cert-42"

    @pytest.mark.unit
    def test_create_dp_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_dp_certificate should generate and register certificate."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "item": {
                    "id": "cert-1",
                    "cert": "test-cert-pem-data",
                }
            },
        )

        result = client.create_dp_certificate("cp-1")

        assert isinstance(result, DataPlaneCertificate)
        assert result.id == "cert-1"
        assert result.key is not None  # Private key should be set
        assert "PRIVATE KEY" in result.key


# ---------------------------------------------------------------------------
# TestKonnectClientHelpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TestKonnectClientServices
# ---------------------------------------------------------------------------


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
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
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
            },
        )

        services, next_offset = client.list_services(CP_ID)

        assert len(services) == 1
        assert services[0].name == "test-service"
        assert services[0].host == "test.local"
        assert next_offset is None
        mock_httpx_client.request.assert_called_once()

    @pytest.mark.unit
    def test_list_services_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_services should forward tags, limit, and offset params."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "next-token"},
        )

        services, next_offset = client.list_services(
            CP_ID,
            tags=["env:prod"],
            limit=10,
            offset="some-token",
        )

        assert services == []
        assert next_offset == "next-token"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "env:prod"
        assert params["size"] == 10
        assert params["offset"] == "some-token"

    @pytest.mark.unit
    def test_get_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_service should return service details."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "svc-1",
                "name": "test-service",
                "host": "test.local",
                "port": 8080,
                "protocol": "http",
            },
        )

        service = client.get_service(CP_ID, "test-service")

        assert service.name == "test-service"
        assert service.host == "test.local"

    @pytest.mark.unit
    def test_get_service_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_service should raise NotFoundError when not found."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_service(CP_ID, "nonexistent")

    @pytest.mark.unit
    def test_create_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_service should create and return service."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {
                "id": "svc-new",
                "name": "new-service",
                "host": "new.local",
                "port": 80,
                "protocol": "http",
            },
        )

        service = Service(name="new-service", host="new.local")
        result = client.create_service(CP_ID, service)

        assert result.id == "svc-new"
        assert result.name == "new-service"

    @pytest.mark.unit
    def test_update_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_service should update and return service."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "svc-1",
                "name": "test-service",
                "host": "updated.local",
                "port": 8080,
                "protocol": "http",
            },
        )

        service = Service(name="test-service", host="updated.local")
        result = client.update_service(CP_ID, "svc-1", service)

        assert result.host == "updated.local"

    @pytest.mark.unit
    def test_delete_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_service should delete service."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_service(CP_ID, "svc-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientRoutes
# ---------------------------------------------------------------------------


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
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [
                    {
                        "id": "route-1",
                        "name": "test-route",
                        "paths": ["/api"],
                        "methods": ["GET", "POST"],
                    }
                ],
                "offset": None,
            },
        )

        routes, _next_offset = client.list_routes(CP_ID)

        assert len(routes) == 1
        assert routes[0].name == "test-route"
        assert routes[0].paths == ["/api"]

    @pytest.mark.unit
    def test_list_routes_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_routes passes tags, limit, and offset correctly."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "tok"},
        )

        routes, next_offset = client.list_routes(
            CP_ID,
            tags=["v1"],
            limit=5,
            offset="prev",
        )

        assert routes == []
        assert next_offset == "tok"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "v1"
        assert params["size"] == 5
        assert params["offset"] == "prev"

    @pytest.mark.unit
    def test_list_routes_by_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_routes should filter by service when specified."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [
                    {
                        "id": "route-1",
                        "name": "svc-route",
                        "paths": ["/api"],
                        "methods": ["GET"],
                    }
                ],
                "offset": None,
            },
        )

        routes, _ = client.list_routes(CP_ID, service_name_or_id="test-service")

        assert len(routes) == 1
        call_args = mock_httpx_client.request.call_args
        assert "services/test-service/routes" in call_args[0][1]

    @pytest.mark.unit
    def test_get_route(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_route should return a Route."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "route-7",
                "name": "my-route",
                "paths": ["/v1"],
                "methods": ["GET"],
            },
        )

        route = client.get_route(CP_ID, "route-7")

        assert route.id == "route-7"
        assert route.name == "my-route"

    @pytest.mark.unit
    def test_get_route_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_route should raise NotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_route(CP_ID, "missing")

    @pytest.mark.unit
    def test_create_route(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_route should create and return route."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {
                "id": "route-new",
                "name": "new-route",
                "paths": ["/new"],
                "methods": ["GET"],
            },
        )

        route = Route(name="new-route", paths=["/new"], methods=["GET"])
        result = client.create_route(CP_ID, route)

        assert result.id == "route-new"
        assert result.name == "new-route"

    @pytest.mark.unit
    def test_create_route_for_service(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_route should use service endpoint when service specified."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {
                "id": "route-new",
                "name": "new-route",
                "paths": ["/new"],
                "methods": ["GET"],
            },
        )

        route = Route(name="new-route", paths=["/new"], methods=["GET"])
        client.create_route(CP_ID, route, service_name_or_id="test-service")

        call_args = mock_httpx_client.request.call_args
        assert "services/test-service/routes" in call_args[0][1]

    @pytest.mark.unit
    def test_update_route(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_route should update and return route."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "route-1",
                "name": "test-route",
                "paths": ["/updated"],
                "methods": ["GET", "POST"],
            },
        )

        route = Route(name="test-route", paths=["/updated"], methods=["GET", "POST"])
        result = client.update_route(CP_ID, "route-1", route)

        assert result.paths == ["/updated"]

    @pytest.mark.unit
    def test_delete_route(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_route should delete route."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_route(CP_ID, "route-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientConsumers
# ---------------------------------------------------------------------------


class TestKonnectClientConsumers:
    """Tests for consumer management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_consumers(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_consumers returns list of Consumer objects."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [
                    {"id": "con-1", "username": "alice"},
                    {"id": "con-2", "username": "bob"},
                ],
                "offset": None,
            },
        )

        consumers, next_offset = client.list_consumers(CP_ID)

        assert len(consumers) == 2
        assert consumers[0].username == "alice"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_consumers_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_consumers forwards tags, limit, offset params."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "page2"},
        )

        _, next_offset = client.list_consumers(CP_ID, tags=["team:a"], limit=20, offset="page1")

        assert next_offset == "page2"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "team:a"
        assert params["size"] == 20
        assert params["offset"] == "page1"

    @pytest.mark.unit
    def test_get_consumer(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_consumer returns a Consumer."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "con-5", "username": "charlie"},
        )

        result = client.get_consumer(CP_ID, "charlie")

        assert result.username == "charlie"

    @pytest.mark.unit
    def test_get_consumer_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_consumer raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_consumer(CP_ID, "ghost")

    @pytest.mark.unit
    def test_create_consumer(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_consumer creates and returns a Consumer."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {"id": "con-new", "username": "dave"},
        )

        consumer = Consumer(username="dave")
        result = client.create_consumer(CP_ID, consumer)

        assert result.id == "con-new"
        assert result.username == "dave"

    @pytest.mark.unit
    def test_update_consumer(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_consumer updates and returns a Consumer."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "con-1", "username": "dave-updated"},
        )

        consumer = Consumer(username="dave-updated")
        result = client.update_consumer(CP_ID, "con-1", consumer)

        assert result.username == "dave-updated"

    @pytest.mark.unit
    def test_delete_consumer(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_consumer deletes the consumer."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_consumer(CP_ID, "con-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientPlugins
# ---------------------------------------------------------------------------


class TestKonnectClientPlugins:
    """Tests for plugin management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "scope_kwarg,expected_path_fragment",
        [
            ({}, "core-entities/plugins"),
            ({"service_name_or_id": "my-svc"}, "services/my-svc/plugins"),
            ({"route_name_or_id": "my-route"}, "routes/my-route/plugins"),
            ({"consumer_name_or_id": "my-consumer"}, "consumers/my-consumer/plugins"),
        ],
    )
    def test_list_plugins_endpoint_routing(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
        scope_kwarg: dict[str, str],
        expected_path_fragment: str,
    ) -> None:
        """list_plugins routes to the correct scoped endpoint."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": None},
        )

        client.list_plugins(CP_ID, **scope_kwarg)

        call_args = mock_httpx_client.request.call_args
        assert expected_path_fragment in call_args[0][1]

    @pytest.mark.unit
    def test_list_plugins_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_plugins forwards tags, limit, and offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "tok"},
        )

        _, next_offset = client.list_plugins(CP_ID, tags=["auth"], limit=3, offset="prev")

        assert next_offset == "tok"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "auth"
        assert params["size"] == 3
        assert params["offset"] == "prev"

    @pytest.mark.unit
    def test_get_plugin(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_plugin returns a KongPluginEntity."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "plg-1", "name": "rate-limiting", "config": {}, "enabled": True},
        )

        result = client.get_plugin(CP_ID, "plg-1")

        assert result.id == "plg-1"
        assert result.name == "rate-limiting"

    @pytest.mark.unit
    def test_get_plugin_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_plugin raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_plugin(CP_ID, "ghost")

    @pytest.mark.unit
    def test_create_plugin(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_plugin creates and returns a KongPluginEntity."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {
                "id": "plg-new",
                "name": "key-auth",
                "config": {},
                "enabled": True,
            },
        )

        plugin = KongPluginEntity(name="key-auth")
        result = client.create_plugin(CP_ID, plugin)

        assert result.id == "plg-new"
        assert result.name == "key-auth"

    @pytest.mark.unit
    def test_update_plugin(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_plugin updates and returns a KongPluginEntity."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "plg-1",
                "name": "rate-limiting",
                "config": {"minute": 100},
                "enabled": True,
            },
        )

        plugin = KongPluginEntity(name="rate-limiting", config={"minute": 100})
        result = client.update_plugin(CP_ID, "plg-1", plugin)

        assert result.config == {"minute": 100}

    @pytest.mark.unit
    def test_delete_plugin(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_plugin deletes the plugin."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_plugin(CP_ID, "plg-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientUpstreams
# ---------------------------------------------------------------------------


class TestKonnectClientUpstreams:
    """Tests for upstream management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_upstreams(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_upstreams returns Upstream objects."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [{"id": "up-1", "name": "backend.internal"}],
                "offset": None,
            },
        )

        upstreams, next_offset = client.list_upstreams(CP_ID)

        assert len(upstreams) == 1
        assert upstreams[0].name == "backend.internal"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_upstreams_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_upstreams forwards tags, limit, offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "nxt"},
        )

        _, next_offset = client.list_upstreams(CP_ID, tags=["lb"], limit=2, offset="cur")

        assert next_offset == "nxt"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "lb"
        assert params["size"] == 2
        assert params["offset"] == "cur"

    @pytest.mark.unit
    def test_get_upstream(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_upstream returns an Upstream."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "up-5", "name": "api.backend"},
        )

        result = client.get_upstream(CP_ID, "api.backend")

        assert result.id == "up-5"

    @pytest.mark.unit
    def test_get_upstream_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_upstream raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_upstream(CP_ID, "ghost")

    @pytest.mark.unit
    def test_create_upstream(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_upstream creates and returns an Upstream."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {"id": "up-new", "name": "new.upstream"},
        )

        upstream = Upstream(name="new.upstream")
        result = client.create_upstream(CP_ID, upstream)

        assert result.id == "up-new"
        assert result.name == "new.upstream"

    @pytest.mark.unit
    def test_update_upstream(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_upstream updates and returns an Upstream."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "up-1", "name": "up.updated", "algorithm": "least-connections"},
        )

        upstream = Upstream(name="up.updated", algorithm="least-connections")
        result = client.update_upstream(CP_ID, "up-1", upstream)

        assert result.algorithm == "least-connections"

    @pytest.mark.unit
    def test_delete_upstream(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_upstream deletes the upstream."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_upstream(CP_ID, "up-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientTargets
# ---------------------------------------------------------------------------


class TestKonnectClientTargets:
    """Tests for target management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_targets(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_targets returns Target objects for an upstream."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [{"id": "tgt-1", "target": "10.0.0.1:8080", "weight": 100}],
                "offset": None,
            },
        )

        targets, next_offset = client.list_targets(CP_ID, "my-upstream")

        assert len(targets) == 1
        assert targets[0].target == "10.0.0.1:8080"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_targets_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_targets forwards tags, limit, offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "t2"},
        )

        _, next_offset = client.list_targets(
            CP_ID,
            "up-1",
            tags=["dc:us"],
            limit=50,
            offset="t1",
        )

        assert next_offset == "t2"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "dc:us"
        assert params["size"] == 50
        assert params["offset"] == "t1"

    @pytest.mark.unit
    def test_create_target(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_target creates and returns a Target."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {"id": "tgt-new", "target": "10.0.0.2:8080", "weight": 100},
        )

        target = Target(target="10.0.0.2:8080")
        result = client.create_target(CP_ID, "my-upstream", target)

        assert result.id == "tgt-new"
        assert result.target == "10.0.0.2:8080"

    @pytest.mark.unit
    def test_delete_target(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_target deletes the target."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_target(CP_ID, "my-upstream", "tgt-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientKongCertificates
# ---------------------------------------------------------------------------


class TestKonnectClientKongCertificates:
    """Tests for Kong Certificate management methods (core-entities)."""

    CERT_PEM = "test-cert-data"
    KEY_PEM = "test-key-data"

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_certificates(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_certificates returns Certificate objects."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [
                    {
                        "id": "crt-1",
                        "cert": self.CERT_PEM,
                        "key": self.KEY_PEM,
                    }
                ],
                "offset": None,
            },
        )

        certs, next_offset = client.list_certificates(CP_ID)

        assert len(certs) == 1
        assert certs[0].id == "crt-1"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_certificates_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_certificates forwards tags, limit, offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "c2"},
        )

        _, next_offset = client.list_certificates(CP_ID, tags=["tls"], limit=10, offset="c1")

        assert next_offset == "c2"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "tls"
        assert params["size"] == 10
        assert params["offset"] == "c1"

    @pytest.mark.unit
    def test_get_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_certificate returns a Certificate."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "crt-7", "cert": self.CERT_PEM, "key": self.KEY_PEM},
        )

        result = client.get_certificate(CP_ID, "crt-7")

        assert result.id == "crt-7"

    @pytest.mark.unit
    def test_get_certificate_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_certificate raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_certificate(CP_ID, "missing")

    @pytest.mark.unit
    def test_create_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_certificate creates and returns a Certificate."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {"id": "crt-new", "cert": self.CERT_PEM, "key": self.KEY_PEM},
        )

        cert = Certificate(cert=self.CERT_PEM, key=self.KEY_PEM)
        result = client.create_certificate(CP_ID, cert)

        assert result.id == "crt-new"

    @pytest.mark.unit
    def test_update_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_certificate updates and returns a Certificate."""
        new_cert_pem = "updated-cert-data"
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "crt-1", "cert": new_cert_pem, "key": self.KEY_PEM},
        )

        cert = Certificate(cert=new_cert_pem, key=self.KEY_PEM)
        result = client.update_certificate(CP_ID, "crt-1", cert)

        assert result.cert == "updated-cert-data"

    @pytest.mark.unit
    def test_delete_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_certificate deletes the certificate."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_certificate(CP_ID, "crt-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientSNIs
# ---------------------------------------------------------------------------


class TestKonnectClientSNIs:
    """Tests for SNI management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_snis(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_snis returns SNI objects."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [
                    {
                        "id": "sni-1",
                        "name": "api.example.com",
                        "certificate": {"id": "crt-1"},
                    }
                ],
                "offset": None,
            },
        )

        snis, next_offset = client.list_snis(CP_ID)

        assert len(snis) == 1
        assert snis[0].name == "api.example.com"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_snis_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_snis forwards tags, limit, offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "s2"},
        )

        _, next_offset = client.list_snis(CP_ID, tags=["ssl"], limit=5, offset="s1")

        assert next_offset == "s2"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "ssl"
        assert params["size"] == 5
        assert params["offset"] == "s1"

    @pytest.mark.unit
    def test_get_sni(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_sni returns an SNI."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "sni-9",
                "name": "secure.example.com",
                "certificate": {"id": "crt-1"},
            },
        )

        result = client.get_sni(CP_ID, "secure.example.com")

        assert result.id == "sni-9"
        assert result.name == "secure.example.com"

    @pytest.mark.unit
    def test_get_sni_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_sni raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_sni(CP_ID, "missing.example.com")

    @pytest.mark.unit
    def test_create_sni(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_sni creates and returns an SNI."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {
                "id": "sni-new",
                "name": "new.example.com",
                "certificate": {"id": "crt-1"},
            },
        )

        from system_operations_manager.integrations.kong.models.base import (
            KongEntityReference,
        )

        sni = SNI(name="new.example.com", certificate=KongEntityReference(id="crt-1"))
        result = client.create_sni(CP_ID, sni)

        assert result.id == "sni-new"

    @pytest.mark.unit
    def test_update_sni(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_sni updates and returns an SNI."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "id": "sni-1",
                "name": "updated.example.com",
                "certificate": {"id": "crt-2"},
            },
        )

        from system_operations_manager.integrations.kong.models.base import (
            KongEntityReference,
        )

        sni = SNI(name="updated.example.com", certificate=KongEntityReference(id="crt-2"))
        result = client.update_sni(CP_ID, "sni-1", sni)

        assert result.name == "updated.example.com"

    @pytest.mark.unit
    def test_delete_sni(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_sni deletes the SNI."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_sni(CP_ID, "sni-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientCACertificates
# ---------------------------------------------------------------------------


class TestKonnectClientCACertificates:
    """Tests for CA certificate management methods."""

    CA_PEM = "test-ca-cert-data"

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_ca_certificates(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_ca_certificates returns CACertificate objects."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [{"id": "ca-1", "cert": self.CA_PEM}],
                "offset": None,
            },
        )

        ca_certs, next_offset = client.list_ca_certificates(CP_ID)

        assert len(ca_certs) == 1
        assert ca_certs[0].id == "ca-1"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_ca_certificates_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_ca_certificates forwards tags, limit, offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "ca2"},
        )

        _, next_offset = client.list_ca_certificates(CP_ID, tags=["ca"], limit=7, offset="ca1")

        assert next_offset == "ca2"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "ca"
        assert params["size"] == 7
        assert params["offset"] == "ca1"

    @pytest.mark.unit
    def test_get_ca_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_ca_certificate returns a CACertificate."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "ca-5", "cert": self.CA_PEM},
        )

        result = client.get_ca_certificate(CP_ID, "ca-5")

        assert result.id == "ca-5"

    @pytest.mark.unit
    def test_get_ca_certificate_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_ca_certificate raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_ca_certificate(CP_ID, "ghost")

    @pytest.mark.unit
    def test_create_ca_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_ca_certificate creates and returns a CACertificate."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {"id": "ca-new", "cert": self.CA_PEM},
        )

        ca_cert = CACertificate(cert=self.CA_PEM)
        result = client.create_ca_certificate(CP_ID, ca_cert)

        assert result.id == "ca-new"

    @pytest.mark.unit
    def test_update_ca_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_ca_certificate updates and returns a CACertificate."""
        new_pem = "updated-ca-cert-data"
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "ca-1", "cert": new_pem},
        )

        ca_cert = CACertificate(cert=new_pem)
        result = client.update_ca_certificate(CP_ID, "ca-1", ca_cert)

        assert result.cert == "updated-ca-cert-data"

    @pytest.mark.unit
    def test_delete_ca_certificate(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_ca_certificate deletes the CA certificate."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_ca_certificate(CP_ID, "ca-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientKeySets
# ---------------------------------------------------------------------------


class TestKonnectClientKeySets:
    """Tests for key set management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_key_sets(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_key_sets returns KeySet objects."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [{"id": "ks-1", "name": "jwt-keys"}],
                "offset": None,
            },
        )

        key_sets, next_offset = client.list_key_sets(CP_ID)

        assert len(key_sets) == 1
        assert key_sets[0].name == "jwt-keys"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_key_sets_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_key_sets forwards tags, limit, offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "ks2"},
        )

        _, next_offset = client.list_key_sets(CP_ID, tags=["keys"], limit=4, offset="ks1")

        assert next_offset == "ks2"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "keys"
        assert params["size"] == 4
        assert params["offset"] == "ks1"

    @pytest.mark.unit
    def test_get_key_set(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_key_set returns a KeySet."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "ks-3", "name": "signing-keys"},
        )

        result = client.get_key_set(CP_ID, "signing-keys")

        assert result.id == "ks-3"
        assert result.name == "signing-keys"

    @pytest.mark.unit
    def test_get_key_set_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_key_set raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_key_set(CP_ID, "missing-ks")

    @pytest.mark.unit
    def test_create_key_set(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_key_set creates and returns a KeySet."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {"id": "ks-new", "name": "new-keys"},
        )

        key_set = KeySet(name="new-keys")
        result = client.create_key_set(CP_ID, key_set)

        assert result.id == "ks-new"
        assert result.name == "new-keys"

    @pytest.mark.unit
    def test_update_key_set(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_key_set updates and returns a KeySet."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "ks-1", "name": "renamed-keys"},
        )

        key_set = KeySet(name="renamed-keys")
        result = client.update_key_set(CP_ID, "ks-1", key_set)

        assert result.name == "renamed-keys"

    @pytest.mark.unit
    def test_delete_key_set(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_key_set deletes the key set."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_key_set(CP_ID, "ks-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientKeys
# ---------------------------------------------------------------------------


class TestKonnectClientKeys:
    """Tests for key management methods."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_keys(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_keys returns Key objects."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [{"id": "key-1", "kid": "my-key-id"}],
                "offset": None,
            },
        )

        keys, next_offset = client.list_keys(CP_ID)

        assert len(keys) == 1
        assert keys[0].kid == "my-key-id"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_keys_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_keys forwards tags, limit, offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "k2"},
        )

        _, next_offset = client.list_keys(CP_ID, tags=["jwk"], limit=6, offset="k1")

        assert next_offset == "k2"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "jwk"
        assert params["size"] == 6
        assert params["offset"] == "k1"

    @pytest.mark.unit
    def test_get_key(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_key returns a Key."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "key-8", "kid": "k-abc"},
        )

        result = client.get_key(CP_ID, "k-abc")

        assert result.id == "key-8"
        assert result.kid == "k-abc"

    @pytest.mark.unit
    def test_get_key_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_key raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_key(CP_ID, "ghost-kid")

    @pytest.mark.unit
    def test_create_key(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_key creates and returns a Key."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {"id": "key-new", "kid": "new-kid"},
        )

        key = Key(kid="new-kid")
        result = client.create_key(CP_ID, key)

        assert result.id == "key-new"
        assert result.kid == "new-kid"

    @pytest.mark.unit
    def test_update_key(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_key updates and returns a Key."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "key-1", "kid": "updated-kid"},
        )

        key = Key(kid="updated-kid")
        result = client.update_key(CP_ID, "key-1", key)

        assert result.kid == "updated-kid"

    @pytest.mark.unit
    def test_delete_key(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_key deletes the key."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_key(CP_ID, "key-1")
        mock_httpx_client.request.assert_called_once()


# ---------------------------------------------------------------------------
# TestKonnectClientVaults
# ---------------------------------------------------------------------------


class TestKonnectClientVaults:
    """Tests for vault management methods (Enterprise)."""

    @pytest.fixture
    def client(
        self,
        konnect_config: KonnectConfig,
        mock_httpx_client: MagicMock,
    ) -> KonnectClient:
        return KonnectClient(konnect_config)

    @pytest.mark.unit
    def test_list_vaults(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_vaults returns Vault objects."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {
                "data": [{"id": "vault-1", "name": "hashi-vault", "prefix": "hv"}],
                "offset": None,
            },
        )

        vaults, next_offset = client.list_vaults(CP_ID)

        assert len(vaults) == 1
        assert vaults[0].name == "hashi-vault"
        assert next_offset is None

    @pytest.mark.unit
    def test_list_vaults_with_params(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """list_vaults forwards tags, limit, offset."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"data": [], "offset": "v2"},
        )

        _, next_offset = client.list_vaults(CP_ID, tags=["secrets"], limit=8, offset="v1")

        assert next_offset == "v2"
        call_kwargs: Any = mock_httpx_client.request.call_args
        params = call_kwargs[1]["params"]
        assert params["tags"] == "secrets"
        assert params["size"] == 8
        assert params["offset"] == "v1"

    @pytest.mark.unit
    def test_get_vault(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_vault returns a Vault."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "vault-4", "name": "aws-secrets", "prefix": "aws"},
        )

        result = client.get_vault(CP_ID, "aws")

        assert result.id == "vault-4"
        assert result.prefix == "aws"

    @pytest.mark.unit
    def test_get_vault_not_found(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_vault raises KonnectNotFoundError."""
        mock_httpx_client.request.return_value = _make_response(404)

        with pytest.raises(KonnectNotFoundError):
            client.get_vault(CP_ID, "ghost-prefix")

    @pytest.mark.unit
    def test_create_vault(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """create_vault creates and returns a Vault."""
        mock_httpx_client.request.return_value = _make_response(
            201,
            {"id": "vault-new", "name": "new-vault", "prefix": "nv"},
        )

        vault = Vault(name="new-vault", prefix="nv")
        result = client.create_vault(CP_ID, vault)

        assert result.id == "vault-new"
        assert result.prefix == "nv"

    @pytest.mark.unit
    def test_update_vault(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """update_vault updates and returns a Vault."""
        mock_httpx_client.request.return_value = _make_response(
            200,
            {"id": "vault-1", "name": "updated-vault", "prefix": "uv"},
        )

        vault = Vault(name="updated-vault", prefix="uv")
        result = client.update_vault(CP_ID, "vault-1", vault)

        assert result.name == "updated-vault"
        assert result.prefix == "uv"

    @pytest.mark.unit
    def test_delete_vault(
        self,
        client: KonnectClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """delete_vault deletes the vault."""
        mock_httpx_client.request.return_value = _make_response(204)

        client.delete_vault(CP_ID, "vault-1")
        mock_httpx_client.request.assert_called_once()
