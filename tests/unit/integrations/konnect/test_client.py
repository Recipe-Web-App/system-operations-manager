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
