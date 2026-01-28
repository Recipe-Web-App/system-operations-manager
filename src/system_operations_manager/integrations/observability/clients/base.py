"""Base HTTP client for observability backends.

Provides common HTTP client functionality for all observability system clients.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()


class ObservabilityClientError(Exception):
    """Base exception for observability client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ObservabilityConnectionError(ObservabilityClientError):
    """Raised when connection to backend fails."""


class ObservabilityAuthError(ObservabilityClientError):
    """Raised when authentication fails."""


class ObservabilityNotFoundError(ObservabilityClientError):
    """Raised when requested resource is not found."""


class BaseObservabilityClient(ABC):
    """Abstract base class for observability HTTP clients.

    Provides common HTTP request functionality with authentication,
    retry logic, and error handling.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        retries: int = 3,
    ) -> None:
        """Initialize the base client.

        Args:
            base_url: Base URL for the API.
            timeout: Request timeout in seconds.
            retries: Number of retry attempts.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._retries = retries
        self._client: httpx.Client | None = None

    def _build_client(self, **kwargs: Any) -> httpx.Client:
        """Build an httpx client with provided configuration.

        Args:
            **kwargs: Additional arguments passed to httpx.Client.

        Returns:
            Configured httpx.Client instance.
        """
        return httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            **kwargs,
        )

    @property
    @abstractmethod
    def client_name(self) -> str:
        """Return the client name for logging."""

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def __enter__(self) -> BaseObservabilityClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - close client."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.debug(f"{self.client_name} client closed")

    def _make_retry_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: URL path relative to base_url.
            **kwargs: Additional arguments for the request.

        Returns:
            httpx.Response object.

        Raises:
            ObservabilityConnectionError: If connection fails.
            ObservabilityAuthError: If authentication fails.
            ObservabilityClientError: For other HTTP errors.
        """

        @retry(
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            stop=stop_after_attempt(self._retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        def _request() -> httpx.Response:
            return self.client.request(method, path, **kwargs)

        try:
            response = _request()
            return response
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.error(
                f"{self.client_name} connection failed",
                error=str(e),
                url=f"{self.base_url}/{path}",
            )
            raise ObservabilityConnectionError(
                f"Failed to connect to {self.client_name}: {e}"
            ) from e

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle HTTP response and return JSON data.

        Args:
            response: The HTTP response.

        Returns:
            Parsed JSON response as dict.

        Raises:
            ObservabilityAuthError: If authentication fails.
            ObservabilityNotFoundError: If resource not found.
            ObservabilityClientError: For other HTTP errors.
        """
        if response.status_code == 401:
            raise ObservabilityAuthError(
                f"{self.client_name} authentication failed",
                status_code=401,
            )

        if response.status_code == 403:
            raise ObservabilityAuthError(
                f"{self.client_name} access forbidden",
                status_code=403,
            )

        if response.status_code == 404:
            raise ObservabilityNotFoundError(
                f"{self.client_name} resource not found",
                status_code=404,
            )

        if response.status_code >= 400:
            raise ObservabilityClientError(
                f"{self.client_name} request failed: {response.text}",
                status_code=response.status_code,
            )

        return cast(dict[str, Any], response.json())

    def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make a GET request.

        Args:
            path: URL path relative to base_url.
            **kwargs: Additional arguments for the request.

        Returns:
            Parsed JSON response.
        """
        response = self._make_retry_request("GET", path, **kwargs)
        return self._handle_response(response)

    def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make a POST request.

        Args:
            path: URL path relative to base_url.
            **kwargs: Additional arguments for the request.

        Returns:
            Parsed JSON response.
        """
        response = self._make_retry_request("POST", path, **kwargs)
        return self._handle_response(response)

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the backend is healthy.

        Returns:
            True if backend is healthy, False otherwise.
        """
