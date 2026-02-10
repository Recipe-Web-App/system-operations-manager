"""Kubernetes integration custom exceptions."""

from __future__ import annotations

from typing import Any


class KubernetesError(Exception):
    """Base exception for Kubernetes operations.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code from Kubernetes API (if applicable).
        resource_type: Type of resource involved (e.g., "Pod", "Deployment").
        resource_name: Name of the resource involved.
        namespace: Namespace of the resource (if applicable).
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        resource_type: str | None = None,
        resource_name: str | None = None,
        namespace: str | None = None,
    ) -> None:
        """Initialize KubernetesError.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code from Kubernetes API.
            resource_type: Type of resource involved.
            resource_name: Name of the resource involved.
            namespace: Namespace of the resource.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace

    def __str__(self) -> str:
        """Return string representation of the error."""
        parts = [self.message]
        if self.status_code:
            parts.append(f"(status: {self.status_code})")
        if self.resource_type and self.resource_name:
            loc = f"[{self.resource_type}/{self.resource_name}"
            if self.namespace:
                loc += f" in {self.namespace}"
            loc += "]"
            parts.append(loc)
        return " ".join(parts)


class KubernetesConnectionError(KubernetesError):
    """Exception raised when connection to a Kubernetes cluster fails.

    This includes network errors, kubeconfig issues, and unreachable API servers.
    """

    def __init__(
        self,
        message: str = "Failed to connect to Kubernetes cluster",
        original_error: Exception | None = None,
    ) -> None:
        """Initialize KubernetesConnectionError.

        Args:
            message: Human-readable error message.
            original_error: The original exception that caused this error.
        """
        super().__init__(message=message)
        self.original_error = original_error


class KubernetesAuthError(KubernetesError):
    """Exception raised when authentication or authorization fails.

    This includes invalid tokens, expired certificates, and RBAC denials (401/403).
    """

    def __init__(
        self,
        message: str = "Kubernetes authentication/authorization failed",
        status_code: int | None = 401,
        reason: str | None = None,
    ) -> None:
        """Initialize KubernetesAuthError.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code (usually 401 or 403).
            reason: Kubernetes API reason string.
        """
        super().__init__(message=message, status_code=status_code)
        self.reason = reason


class KubernetesNotFoundError(KubernetesError):
    """Exception raised when a requested Kubernetes resource is not found.

    This is typically a 404 response from the Kubernetes API.
    """

    def __init__(
        self,
        message: str = "Kubernetes resource not found",
        resource_type: str | None = None,
        resource_name: str | None = None,
        namespace: str | None = None,
    ) -> None:
        """Initialize KubernetesNotFoundError.

        Args:
            message: Human-readable error message.
            resource_type: Type of resource (e.g., "Pod", "Deployment").
            resource_name: Name of the resource.
            namespace: Namespace of the resource.
        """
        if resource_type and resource_name:
            message = f"{resource_type} '{resource_name}' not found"
            if namespace:
                message += f" in namespace '{namespace}'"
        super().__init__(
            message=message,
            status_code=404,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )


class KubernetesValidationError(KubernetesError):
    """Exception raised when Kubernetes API rejects invalid resource specs.

    This is typically a 400/422 response indicating schema validation failure.
    """

    def __init__(
        self,
        message: str = "Invalid resource specification",
        validation_errors: dict[str, Any] | None = None,
        status_code: int | None = 422,
    ) -> None:
        """Initialize KubernetesValidationError.

        Args:
            message: Human-readable error message.
            validation_errors: Specific field validation errors.
            status_code: HTTP status code (usually 400 or 422).
        """
        super().__init__(message=message, status_code=status_code)
        self.validation_errors = validation_errors or {}


class KubernetesConflictError(KubernetesError):
    """Exception raised when a resource conflict occurs.

    This is typically a 409 response indicating the resource already exists
    or has been modified by another client.
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        resource_type: str | None = None,
        resource_name: str | None = None,
        namespace: str | None = None,
    ) -> None:
        """Initialize KubernetesConflictError.

        Args:
            message: Human-readable error message.
            resource_type: Type of resource.
            resource_name: Name of the resource.
            namespace: Namespace of the resource.
        """
        if resource_type and resource_name:
            message = f"{resource_type} '{resource_name}' already exists"
            if namespace:
                message += f" in namespace '{namespace}'"
        super().__init__(
            message=message,
            status_code=409,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )


class KubernetesTimeoutError(KubernetesError):
    """Exception raised when a Kubernetes operation times out.

    This includes watch timeouts, long-running operation timeouts,
    and API request timeouts.
    """

    def __init__(
        self,
        message: str = "Kubernetes operation timed out",
        timeout_seconds: int | None = None,
    ) -> None:
        """Initialize KubernetesTimeoutError.

        Args:
            message: Human-readable error message.
            timeout_seconds: The timeout value that was exceeded.
        """
        if timeout_seconds:
            message = f"{message} (after {timeout_seconds}s)"
        super().__init__(message=message)
        self.timeout_seconds = timeout_seconds
