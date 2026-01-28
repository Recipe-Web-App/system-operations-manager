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


class TestKongAdminClientContextManager:
    """Tests for context manager protocol."""

    @pytest.mark.unit
    def test_context_manager_enter(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Context manager should return client on enter."""
        client = KongAdminClient(connection_config, auth_config)

        with client as ctx:
            assert ctx is client

    @pytest.mark.unit
    def test_context_manager_exit(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Context manager should close client on exit."""
        client = KongAdminClient(connection_config, auth_config)

        with client:
            pass

        mock_httpx_client.close.assert_called_once()


class TestKongAdminClientMTLSAuth:
    """Tests for mTLS authentication."""

    @pytest.mark.unit
    def test_client_with_mtls_auth(
        self,
        connection_config: KongConnectionConfig,
        mocker: Any,
    ) -> None:
        """Client should support mTLS authentication."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_httpx = mocker.patch("httpx.Client", return_value=mock_client)

        auth_config = KongAuthConfig(
            type="mtls",
            cert_path="/path/to/cert.pem",
            key_path="/path/to/key.pem",
        )
        KongAdminClient(connection_config, auth_config)

        # Verify cert tuple was passed
        call_kwargs = mock_httpx.call_args[1]
        assert call_kwargs["cert"] == ("/path/to/cert.pem", "/path/to/key.pem")

    @pytest.mark.unit
    def test_client_with_mtls_and_ca(
        self,
        connection_config: KongConnectionConfig,
        mocker: Any,
    ) -> None:
        """Client should support mTLS with custom CA."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_httpx = mocker.patch("httpx.Client", return_value=mock_client)

        auth_config = KongAuthConfig(
            type="mtls",
            cert_path="/path/to/cert.pem",
            key_path="/path/to/key.pem",
            ca_path="/path/to/ca.pem",
        )
        KongAdminClient(connection_config, auth_config)

        # Verify CA path was used for verify
        call_kwargs = mock_httpx.call_args[1]
        assert call_kwargs["verify"] == "/path/to/ca.pem"


class TestKongAdminClientResponseErrors:
    """Tests for HTTP response error handling."""

    @pytest.fixture
    def client(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig,
        mock_httpx_client: MagicMock,
    ) -> KongAdminClient:
        """Create a client with mocked httpx."""
        return KongAdminClient(connection_config, auth_config)

    def _mock_response(
        self, mock_httpx_client: MagicMock, status_code: int, body: dict[str, Any]
    ) -> None:
        """Helper to create mock response."""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.is_success = 200 <= status_code < 300
        mock_response.json.return_value = body
        mock_response.content = True
        mock_httpx_client.request.return_value = mock_response

    @pytest.mark.unit
    def test_handle_response_401_raises_auth_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """401 response should raise KongAuthError."""
        self._mock_response(mock_httpx_client, 401, {"message": "Unauthorized"})

        with pytest.raises(KongAuthError) as exc_info:
            client.get("services")

        assert exc_info.value.status_code == 401

    @pytest.mark.unit
    def test_handle_response_403_raises_auth_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """403 response should raise KongAuthError."""
        self._mock_response(mock_httpx_client, 403, {"message": "Forbidden"})

        with pytest.raises(KongAuthError) as exc_info:
            client.get("services")

        assert exc_info.value.status_code == 403

    @pytest.mark.unit
    def test_handle_response_404_raises_not_found_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """404 response should raise KongNotFoundError."""
        self._mock_response(mock_httpx_client, 404, {"message": "Not found"})

        with pytest.raises(KongNotFoundError) as exc_info:
            client.get("services/missing")

        assert exc_info.value.status_code == 404

    @pytest.mark.unit
    def test_handle_response_400_raises_validation_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """400 response should raise KongValidationError."""
        self._mock_response(
            mock_httpx_client,
            400,
            {"message": "Validation failed", "fields": {"name": "is required"}},
        )

        with pytest.raises(KongValidationError) as exc_info:
            client.post("services", json={})

        assert exc_info.value.status_code == 400
        assert exc_info.value.validation_errors == {"name": "is required"}

    @pytest.mark.unit
    def test_handle_response_405_dbless_raises_dbless_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """405 with read-only message should raise KongDBLessWriteError."""
        from system_operations_manager.integrations.kong.exceptions import (
            KongDBLessWriteError,
        )

        self._mock_response(mock_httpx_client, 405, {"message": "This is a read-only node"})

        with pytest.raises(KongDBLessWriteError) as exc_info:
            client.post("services", json={"name": "test"})

        assert exc_info.value.status_code == 405

    @pytest.mark.unit
    def test_handle_response_405_generic_raises_api_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """405 without db-less indicator should raise KongAPIError."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        self._mock_response(mock_httpx_client, 405, {"message": "Method not allowed"})

        with pytest.raises(KongAPIError) as exc_info:
            client.post("status", json={})

        assert exc_info.value.status_code == 405

    @pytest.mark.unit
    def test_handle_response_500_raises_api_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """500 response should raise KongAPIError."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        self._mock_response(mock_httpx_client, 500, {"message": "Internal error"})

        with pytest.raises(KongAPIError) as exc_info:
            client.get("services")

        assert exc_info.value.status_code == 500

    @pytest.mark.unit
    def test_handle_response_non_json_body(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Non-JSON response should be handled gracefully."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.is_success = False
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = "Internal Server Error"
        mock_response.content = True
        mock_httpx_client.request.return_value = mock_response

        with pytest.raises(KongAPIError) as exc_info:
            client.get("services")

        assert exc_info.value.response_body == {"raw": "Internal Server Error"}


class TestKongAdminClientConnectionErrors:
    """Tests for connection error handling."""

    @pytest.fixture
    def client(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig,
        mock_httpx_client: MagicMock,
    ) -> KongAdminClient:
        """Create a client with mocked httpx."""
        # Override retries to 1 for faster tests
        connection_config.retries = 1
        return KongAdminClient(connection_config, auth_config)

    @pytest.mark.unit
    def test_connect_error_raises_connection_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Connection refused should raise KongConnectionError."""
        mock_httpx_client.request.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(KongConnectionError) as exc_info:
            client.get("services")

        assert "Connection refused" in str(exc_info.value)
        assert exc_info.value.original_error is not None

    @pytest.mark.unit
    def test_timeout_raises_connection_error(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Timeout should raise KongConnectionError."""
        mock_httpx_client.request.side_effect = httpx.TimeoutException("Timed out")

        with pytest.raises(KongConnectionError) as exc_info:
            client.get("services")

        assert "timed out" in str(exc_info.value).lower()
        assert exc_info.value.original_error is not None


class TestKongAdminClientCheckConnection:
    """Tests for check_connection method."""

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
    def test_check_connection_success(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """check_connection should return True on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {"database": {"reachable": True}}
        mock_response.content = True
        mock_httpx_client.request.return_value = mock_response

        result = client.check_connection()

        assert result is True

    @pytest.mark.unit
    def test_check_connection_failure(
        self,
        client: KongAdminClient,
        mock_httpx_client: MagicMock,
    ) -> None:
        """check_connection should return False on error."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_httpx_client.request.side_effect = KongAPIError("Error")

        result = client.check_connection()

        assert result is False


class TestKongAdminClientApiKeyHeaders:
    """Tests for API key header configuration."""

    @pytest.mark.unit
    def test_client_headers_with_api_key(
        self,
        connection_config: KongConnectionConfig,
        mocker: Any,
    ) -> None:
        """Client should set API key header."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_httpx = mocker.patch("httpx.Client", return_value=mock_client)

        auth_config = KongAuthConfig(
            type="api_key",
            api_key="my-secret-key",
            header_name="Kong-Admin-Token",
        )
        KongAdminClient(connection_config, auth_config)

        call_kwargs = mock_httpx.call_args[1]
        assert call_kwargs["headers"] == {"Kong-Admin-Token": "my-secret-key"}

    @pytest.mark.unit
    def test_client_headers_with_custom_header_name(
        self,
        connection_config: KongConnectionConfig,
        mocker: Any,
    ) -> None:
        """Client should use custom header name."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_httpx = mocker.patch("httpx.Client", return_value=mock_client)

        auth_config = KongAuthConfig(
            type="api_key",
            api_key="my-key",
            header_name="X-Custom-Auth",
        )
        KongAdminClient(connection_config, auth_config)

        call_kwargs = mock_httpx.call_args[1]
        assert call_kwargs["headers"] == {"X-Custom-Auth": "my-key"}
