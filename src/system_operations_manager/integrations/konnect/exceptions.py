"""Konnect API exceptions."""

from __future__ import annotations


class KonnectError(Exception):
    """Base exception for Konnect errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        """Initialize exception.

        Args:
            message: Error message.
            details: Additional details.
        """
        super().__init__(message)
        self.message = message
        self.details = details


class KonnectConnectionError(KonnectError):
    """Raised when connection to Konnect API fails."""


class KonnectAuthError(KonnectError):
    """Raised when authentication fails."""


class KonnectAPIError(KonnectError):
    """Raised when Konnect API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize exception.

        Args:
            message: Error message.
            status_code: HTTP status code.
            details: Additional details.
        """
        super().__init__(message, details)
        self.status_code = status_code


class KonnectNotFoundError(KonnectAPIError):
    """Raised when a resource is not found."""


class KonnectConfigError(KonnectError):
    """Raised when configuration is invalid or missing."""
