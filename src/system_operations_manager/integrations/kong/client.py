"""Kong Admin API HTTP client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongAuthError,
    KongConnectionError,
    KongDBLessWriteError,
    KongNotFoundError,
    KongValidationError,
)

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.config import (
        KongAuthConfig,
        KongConnectionConfig,
    )

logger = structlog.get_logger()


class KongAdminClient:
    """HTTP client for Kong Admin API.

    This client provides methods to interact with the Kong Admin API,
    supporting various authentication methods and automatic retry logic.

    Example:
        ```python
        from system_operations_manager.integrations.kong import KongAdminClient
        from system_operations_manager.integrations.kong.config import (
            KongConnectionConfig,
            KongAuthConfig,
        )

        connection = KongConnectionConfig(base_url="http://localhost:8001")
        auth = KongAuthConfig(type="api_key", api_key="my-api-key")

        with KongAdminClient(connection, auth) as client:
            status = client.get("status")
            print(status)
        ```
    """

    def __init__(
        self,
        connection_config: KongConnectionConfig,
        auth_config: KongAuthConfig | None = None,
    ) -> None:
        """Initialize Kong Admin API client.

        Args:
            connection_config: Connection settings (URL, timeout, SSL, retries).
            auth_config: Authentication settings (type, credentials).
        """
        self.connection_config = connection_config
        self.auth_config = auth_config
        self._retries = connection_config.retries

        # Build client configuration
        client_kwargs: dict[str, Any] = {
            "base_url": connection_config.base_url,
            "timeout": httpx.Timeout(connection_config.timeout),
            "verify": connection_config.verify_ssl,
        }

        # Configure authentication
        headers: dict[str, str] = {}
        if auth_config:
            if auth_config.type == "api_key" and auth_config.api_key:
                headers[auth_config.header_name] = auth_config.api_key
                logger.debug("Kong client configured with API key auth")
            elif auth_config.type == "mtls" and auth_config.cert_path and auth_config.key_path:
                client_kwargs["cert"] = (auth_config.cert_path, auth_config.key_path)
                if auth_config.ca_path:
                    client_kwargs["verify"] = auth_config.ca_path
                logger.debug("Kong client configured with mTLS auth")

        if headers:
            client_kwargs["headers"] = headers

        self._client = httpx.Client(**client_kwargs)

        logger.info(
            "Kong Admin API client initialized",
            base_url=connection_config.base_url,
            auth_type=auth_config.type if auth_config else "none",
        )

    def _make_retry_decorator(self) -> Any:
        """Create a retry decorator based on configuration."""
        return retry(
            retry=retry_if_exception_type(KongConnectionError),
            stop=stop_after_attempt(self._retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )

    def _handle_response(self, response: httpx.Response, endpoint: str) -> dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions.

        Args:
            response: The HTTP response from Kong API.
            endpoint: The endpoint that was called.

        Returns:
            Parsed JSON response body.

        Raises:
            KongAuthError: If authentication failed (401/403).
            KongNotFoundError: If resource not found (404).
            KongDBLessWriteError: If write attempted in DB-less mode (405).
            KongValidationError: If request validation failed (400).
            KongAPIError: For other API errors.
        """
        try:
            body = response.json() if response.content else {}
        except Exception:
            body = {"raw": response.text}

        if response.is_success:
            return body

        # Handle specific error codes
        status = response.status_code

        if status in (401, 403):
            message = body.get("message", "Authentication failed")
            raise KongAuthError(
                message=message,
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )

        if status == 404:
            message = body.get("message", "Resource not found")
            raise KongNotFoundError(
                message=message,
                response_body=body,
                endpoint=endpoint,
            )

        if status == 405:
            message = body.get("message", "Method not allowed")
            # Check if this is a DB-less mode write error
            if "read-only" in message.lower() or "db-less" in message.lower():
                raise KongDBLessWriteError(endpoint=endpoint)
            raise KongAPIError(
                message=message,
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )

        if status == 400:
            message = body.get("message", "Validation failed")
            validation_errors = body.get("fields", {})
            raise KongValidationError(
                message=message,
                validation_errors=validation_errors,
                response_body=body,
                endpoint=endpoint,
            )

        # Generic error for other status codes
        message = body.get("message", f"Kong API error: {status}")
        raise KongAPIError(
            message=message,
            status_code=status,
            response_body=body,
            endpoint=endpoint,
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an HTTP request to Kong Admin API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            endpoint: API endpoint (will be prefixed with base URL).
            **kwargs: Additional arguments to pass to httpx.

        Returns:
            Parsed JSON response body.

        Raises:
            KongConnectionError: If connection to Kong fails.
            KongAPIError: If Kong returns an error response.
        """
        url = f"/{endpoint.lstrip('/')}"
        log = logger.bind(method=method, endpoint=url)

        try:
            log.debug("Kong API request")
            response = self._client.request(method, url, **kwargs)
            log.debug("Kong API response", status=response.status_code)
            return self._handle_response(response, url)
        except httpx.ConnectError as e:
            log.error("Kong connection error", error=str(e))
            raise KongConnectionError(
                message=f"Failed to connect to Kong: {e}",
                endpoint=url,
                original_error=e,
            ) from e
        except httpx.TimeoutException as e:
            log.error("Kong request timeout", error=str(e))
            raise KongConnectionError(
                message=f"Kong request timed out: {e}",
                endpoint=url,
                original_error=e,
            ) from e

    def get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """GET request to Kong Admin API.

        Args:
            endpoint: API endpoint (e.g., "services", "routes/my-route").
            **kwargs: Additional query parameters.

        Returns:
            Parsed JSON response body.
        """
        retry_decorator = self._make_retry_decorator()
        result = retry_decorator(self._request)("GET", endpoint, **kwargs)
        return cast(dict[str, Any], result)

    def post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """POST request to Kong Admin API.

        Args:
            endpoint: API endpoint.
            json: Request body as dictionary.
            **kwargs: Additional request parameters.

        Returns:
            Parsed JSON response body (created resource).
        """
        retry_decorator = self._make_retry_decorator()
        result = retry_decorator(self._request)("POST", endpoint, json=json, **kwargs)
        return cast(dict[str, Any], result)

    def put(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """PUT request to Kong Admin API.

        Args:
            endpoint: API endpoint.
            json: Request body as dictionary.
            **kwargs: Additional request parameters.

        Returns:
            Parsed JSON response body (updated resource).
        """
        retry_decorator = self._make_retry_decorator()
        result = retry_decorator(self._request)("PUT", endpoint, json=json, **kwargs)
        return cast(dict[str, Any], result)

    def patch(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """PATCH request to Kong Admin API.

        Args:
            endpoint: API endpoint.
            json: Request body as dictionary (partial update).
            **kwargs: Additional request parameters.

        Returns:
            Parsed JSON response body (updated resource).
        """
        retry_decorator = self._make_retry_decorator()
        result = retry_decorator(self._request)("PATCH", endpoint, json=json, **kwargs)
        return cast(dict[str, Any], result)

    def delete(self, endpoint: str, **kwargs: Any) -> None:
        """DELETE request to Kong Admin API.

        Args:
            endpoint: API endpoint.
            **kwargs: Additional request parameters.
        """
        retry_decorator = self._make_retry_decorator()
        retry_decorator(self._request)("DELETE", endpoint, **kwargs)

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        self._client.close()
        logger.debug("Kong client closed")

    def __enter__(self) -> KongAdminClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    # Convenience methods for common operations

    def get_status(self) -> dict[str, Any]:
        """Get Kong node status.

        Returns:
            Kong status information including database connectivity.
        """
        return self.get("status")

    def get_info(self) -> dict[str, Any]:
        """Get Kong node information.

        Returns:
            Kong node details including version, hostname, plugins.
        """
        return self.get("")

    def check_connection(self) -> bool:
        """Check if connection to Kong Admin API is working.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            self.get_status()
            return True
        except KongAPIError:
            return False
