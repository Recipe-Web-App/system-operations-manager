"""Kong Gateway custom exceptions."""

from __future__ import annotations

from typing import Any


class KongAPIError(Exception):
    """Base exception for Kong Admin API errors.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code from Kong API (if applicable).
        response_body: Raw response body from Kong API (if available).
        endpoint: The API endpoint that was called.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize KongAPIError.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code from Kong API.
            response_body: Raw response body from Kong API.
            endpoint: The API endpoint that was called.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.endpoint = endpoint

    def __str__(self) -> str:
        """Return string representation of the error."""
        parts = [self.message]
        if self.status_code:
            parts.append(f"(status: {self.status_code})")
        if self.endpoint:
            parts.append(f"[endpoint: {self.endpoint}]")
        return " ".join(parts)


class KongConnectionError(KongAPIError):
    """Exception raised when connection to Kong Admin API fails.

    This includes network errors, timeouts, and DNS resolution failures.
    """

    def __init__(
        self,
        message: str = "Failed to connect to Kong Admin API",
        endpoint: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize KongConnectionError.

        Args:
            message: Human-readable error message.
            endpoint: The API endpoint that was attempted.
            original_error: The original exception that caused this error.
        """
        super().__init__(message=message, endpoint=endpoint)
        self.original_error = original_error


class KongAuthError(KongAPIError):
    """Exception raised when authentication to Kong Admin API fails.

    This includes invalid API keys, expired tokens, and certificate issues.
    """

    def __init__(
        self,
        message: str = "Authentication to Kong Admin API failed",
        status_code: int | None = 401,
        response_body: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize KongAuthError.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code (usually 401 or 403).
            response_body: Raw response body from Kong API.
            endpoint: The API endpoint that was called.
        """
        super().__init__(
            message=message,
            status_code=status_code,
            response_body=response_body,
            endpoint=endpoint,
        )


class KongNotFoundError(KongAPIError):
    """Exception raised when a requested Kong resource is not found.

    This is typically a 404 response from the Kong Admin API.
    """

    def __init__(
        self,
        message: str = "Kong resource not found",
        resource_type: str | None = None,
        resource_id: str | None = None,
        response_body: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize KongNotFoundError.

        Args:
            message: Human-readable error message.
            resource_type: Type of resource (e.g., "service", "route", "consumer").
            resource_id: ID or name of the resource.
            response_body: Raw response body from Kong API.
            endpoint: The API endpoint that was called.
        """
        if resource_type and resource_id:
            message = f"{resource_type} '{resource_id}' not found"
        super().__init__(
            message=message,
            status_code=404,
            response_body=response_body,
            endpoint=endpoint,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class KongValidationError(KongAPIError):
    """Exception raised when Kong API rejects invalid request data.

    This is typically a 400 response indicating schema validation failure.
    """

    def __init__(
        self,
        message: str = "Invalid request data",
        validation_errors: dict[str, Any] | None = None,
        response_body: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize KongValidationError.

        Args:
            message: Human-readable error message.
            validation_errors: Specific field validation errors from Kong.
            response_body: Raw response body from Kong API.
            endpoint: The API endpoint that was called.
        """
        super().__init__(
            message=message,
            status_code=400,
            response_body=response_body,
            endpoint=endpoint,
        )
        self.validation_errors = validation_errors or {}


class KongDBLessWriteError(KongAPIError):
    """Exception raised when attempting a write operation in DB-less mode.

    In DB-less mode, Kong's Admin API is read-only and configuration must
    be applied via declarative config files.
    """

    def __init__(
        self,
        message: str = "Write operations are not allowed in DB-less mode",
        endpoint: str | None = None,
    ) -> None:
        """Initialize KongDBLessWriteError.

        Args:
            message: Human-readable error message.
            endpoint: The API endpoint that was called.
        """
        super().__init__(
            message=message,
            status_code=405,
            endpoint=endpoint,
        )
