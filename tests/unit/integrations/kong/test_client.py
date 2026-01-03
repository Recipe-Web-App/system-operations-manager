"""Unit tests for Kong Admin API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from system_operations_manager.integrations.kong.client import KongAdminClient
from system_operations_manager.integrations.kong.config import (
    KongAuthConfig,
    KongConnectionConfig,
)
from system_operations_manager.integrations.kong.exceptions import (
    KongAuthError,
    KongConnectionError,
    KongNotFoundError,
    KongValidationError,
)


@pytest.fixture
def connection_config() -> KongConnectionConfig:
    """Create a test connection config."""
    return KongConnectionConfig(
        base_url="http://localhost:8001",
        timeout=30,
        verify_ssl=False,
    )


@pytest.fixture
def auth_config() -> KongAuthConfig:
    """Create a test auth config."""
    return KongAuthConfig(type="none")


@pytest.fixture
def mock_httpx_client(mocker: Any) -> MagicMock:
    """Create a mock httpx client."""
    mock_client = MagicMock(spec=httpx.Client)
    mocker.patch("httpx.Client", return_value=mock_client)
    return mock_client


class TestKongAdminClientInit:
    """Tests for KongAdminClient initialization."""

    @pytest.mark.unit
    def test_client_initialization(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Client should initialize with config."""
        client = KongAdminClient(connection_config, auth_config)

        assert client is not None

    @pytest.mark.unit
    def test_client_with_api_key_auth(
        self,
        connection_config: KongConnectionConfig,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Client should support API key authentication."""
        auth_config = KongAuthConfig(type="api_key", api_key="test-key")
        client = KongAdminClient(connection_config, auth_config)

        assert client is not None


class TestKongAdminClientRequests:
    """Tests for KongAdminClient HTTP requests."""

    @pytest.fixture
    def client(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig,
        mock_httpx_client: MagicMock,
    ) -> KongAdminClient:
        """Create a client with mocked httpx."""
        return KongAdminClient(connection_config, auth_config)

    @pytest.mark.unit
    def test_get_request(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """GET request should return JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.request.return_value = mock_response

        result = client.get("services")

        assert result == {"data": []}
        mock_httpx_client.request.assert_called_once()

    @pytest.mark.unit
    def test_post_request(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """POST request should send JSON payload."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-id", "name": "test"}
        mock_httpx_client.request.return_value = mock_response

        result = client.post("services", json={"name": "test"})

        assert result["id"] == "new-id"

    @pytest.mark.unit
    def test_patch_request(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """PATCH request should update resource."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "id", "name": "updated"}
        mock_httpx_client.request.return_value = mock_response

        result = client.patch("services/id", json={"name": "updated"})

        assert result["name"] == "updated"

    @pytest.mark.unit
    def test_put_request(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """PUT request should upsert resource."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "id", "name": "upserted"}
        mock_httpx_client.request.return_value = mock_response

        result = client.put("services/id", json={"name": "upserted"})

        assert result["name"] == "upserted"

    @pytest.mark.unit
    def test_delete_request(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """DELETE request should remove resource."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_httpx_client.request.return_value = mock_response

        # Should not raise
        client.delete("services/id")


class TestKongAdminClientErrors:
    """Tests for KongAdminClient error handling."""

    @pytest.mark.unit
    def test_connection_error_type(self) -> None:
        """KongConnectionError should be a subclass of KongAPIError."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        assert issubclass(KongConnectionError, KongAPIError)

    @pytest.mark.unit
    def test_auth_error_type(self) -> None:
        """KongAuthError should be a subclass of KongAPIError."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        assert issubclass(KongAuthError, KongAPIError)

    @pytest.mark.unit
    def test_not_found_error_type(self) -> None:
        """KongNotFoundError should be a subclass of KongAPIError."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        assert issubclass(KongNotFoundError, KongAPIError)

    @pytest.mark.unit
    def test_validation_error_type(self) -> None:
        """KongValidationError should be a subclass of KongAPIError."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        assert issubclass(KongValidationError, KongAPIError)

    @pytest.mark.unit
    def test_connection_error_message(self) -> None:
        """KongConnectionError should include error details."""
        error = KongConnectionError("Connection refused", "http://localhost:8001")
        assert "Connection refused" in str(error)

    @pytest.mark.unit
    def test_not_found_error_message(self) -> None:
        """KongNotFoundError should include endpoint."""
        error = KongNotFoundError("Not found", "/services/test")
        assert "Not found" in str(error)


class TestKongAdminClientInfoEndpoints:
    """Tests for Kong info/status endpoints."""

    @pytest.fixture
    def client(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig,
        mock_httpx_client: MagicMock,
    ) -> KongAdminClient:
        """Create a client with mocked httpx."""
        return KongAdminClient(connection_config, auth_config)

    @pytest.mark.unit
    def test_get_info(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_info should return Kong node information."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "version": "3.0.0",
            "hostname": "kong-node",
            "plugins": {"available_on_server": {}},
        }
        mock_httpx_client.request.return_value = mock_response

        info = client.get_info()

        assert info["version"] == "3.0.0"
        assert info["hostname"] == "kong-node"

    @pytest.mark.unit
    def test_get_status(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """get_status should return Kong status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "database": {"reachable": True},
            "memory": {"workers_lua_vms": []},
        }
        mock_httpx_client.request.return_value = mock_response

        status = client.get_status()

        assert status["database"]["reachable"] is True


class TestKongAdminClientClose:
    """Tests for client cleanup."""

    @pytest.mark.unit
    def test_close_client(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig,
        mock_httpx_client: MagicMock,
    ) -> None:
        """close should cleanup resources."""
        client = KongAdminClient(connection_config, auth_config)
        client.close()

        mock_httpx_client.close.assert_called_once()
