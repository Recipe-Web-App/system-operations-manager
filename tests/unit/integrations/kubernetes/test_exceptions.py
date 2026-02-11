"""Unit tests for Kubernetes exceptions."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConflictError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesTimeoutError,
    KubernetesValidationError,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesError:
    """Test KubernetesError base exception."""

    def test_init_minimal(self) -> None:
        """Test initialization with minimal arguments."""
        error = KubernetesError("Something went wrong")
        assert error.message == "Something went wrong"
        assert error.status_code is None
        assert error.resource_type is None
        assert error.resource_name is None
        assert error.namespace is None

    def test_init_with_status_code(self) -> None:
        """Test initialization with status code."""
        error = KubernetesError("API error", status_code=500)
        assert error.message == "API error"
        assert error.status_code == 500

    def test_init_with_resource_info(self) -> None:
        """Test initialization with resource information."""
        error = KubernetesError(
            "Resource error",
            status_code=400,
            resource_type="Pod",
            resource_name="test-pod",
            namespace="default",
        )
        assert error.resource_type == "Pod"
        assert error.resource_name == "test-pod"
        assert error.namespace == "default"

    def test_str_message_only(self) -> None:
        """Test string representation with message only."""
        error = KubernetesError("Test error")
        assert str(error) == "Test error"

    def test_str_with_status_code(self) -> None:
        """Test string representation with status code."""
        error = KubernetesError("Test error", status_code=404)
        assert str(error) == "Test error (status: 404)"

    def test_str_with_resource_info(self) -> None:
        """Test string representation with resource info."""
        error = KubernetesError(
            "Test error",
            resource_type="Deployment",
            resource_name="nginx",
        )
        assert str(error) == "Test error [Deployment/nginx]"

    def test_str_with_namespace(self) -> None:
        """Test string representation with namespace."""
        error = KubernetesError(
            "Test error",
            resource_type="Pod",
            resource_name="test-pod",
            namespace="production",
        )
        assert str(error) == "Test error [Pod/test-pod in production]"

    def test_str_complete(self) -> None:
        """Test string representation with all fields."""
        error = KubernetesError(
            "Operation failed",
            status_code=500,
            resource_type="Service",
            resource_name="api",
            namespace="backend",
        )
        assert str(error) == "Operation failed (status: 500) [Service/api in backend]"

    def test_inheritance(self) -> None:
        """Test that KubernetesError is an Exception."""
        error = KubernetesError("Test")
        assert isinstance(error, Exception)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesConnectionError:
    """Test KubernetesConnectionError exception."""

    def test_init_default(self) -> None:
        """Test initialization with default message."""
        error = KubernetesConnectionError()
        assert error.message == "Failed to connect to Kubernetes cluster"
        assert error.original_error is None

    def test_init_custom_message(self) -> None:
        """Test initialization with custom message."""
        error = KubernetesConnectionError("Custom connection error")
        assert error.message == "Custom connection error"

    def test_init_with_original_error(self) -> None:
        """Test initialization with original error."""
        original = ValueError("Network unreachable")
        error = KubernetesConnectionError(original_error=original)
        assert error.original_error is original

    def test_inheritance(self) -> None:
        """Test that KubernetesConnectionError inherits from KubernetesError."""
        error = KubernetesConnectionError()
        assert isinstance(error, KubernetesError)
        assert isinstance(error, Exception)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesAuthError:
    """Test KubernetesAuthError exception."""

    def test_init_default(self) -> None:
        """Test initialization with defaults."""
        error = KubernetesAuthError()
        assert error.message == "Kubernetes authentication/authorization failed"
        assert error.status_code == 401
        assert error.reason is None

    def test_init_custom_message(self) -> None:
        """Test initialization with custom message."""
        error = KubernetesAuthError("Invalid token")
        assert error.message == "Invalid token"

    def test_init_with_status_code(self) -> None:
        """Test initialization with custom status code."""
        error = KubernetesAuthError(status_code=403)
        assert error.status_code == 403

    def test_init_with_reason(self) -> None:
        """Test initialization with reason."""
        error = KubernetesAuthError(reason="Forbidden")
        assert error.reason == "Forbidden"

    def test_str_representation(self) -> None:
        """Test string representation."""
        error = KubernetesAuthError("Access denied", status_code=403, reason="RBAC")
        assert "Access denied" in str(error)
        assert "(status: 403)" in str(error)

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = KubernetesAuthError()
        assert isinstance(error, KubernetesError)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesNotFoundError:
    """Test KubernetesNotFoundError exception."""

    def test_init_default(self) -> None:
        """Test initialization with default message."""
        error = KubernetesNotFoundError()
        assert error.message == "Kubernetes resource not found"
        assert error.status_code == 404

    def test_init_with_resource_type_and_name(self) -> None:
        """Test initialization with resource type and name."""
        error = KubernetesNotFoundError(resource_type="Pod", resource_name="nginx")
        assert error.message == "Pod 'nginx' not found"
        assert error.resource_type == "Pod"
        assert error.resource_name == "nginx"

    def test_init_with_namespace(self) -> None:
        """Test initialization with namespace."""
        error = KubernetesNotFoundError(
            resource_type="Service",
            resource_name="api",
            namespace="production",
        )
        assert error.message == "Service 'api' not found in namespace 'production'"
        assert error.namespace == "production"

    def test_str_representation(self) -> None:
        """Test string representation."""
        error = KubernetesNotFoundError(
            resource_type="Deployment",
            resource_name="webapp",
            namespace="staging",
        )
        result = str(error)
        assert "Deployment 'webapp' not found in namespace 'staging'" in result
        assert "(status: 404)" in result

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = KubernetesNotFoundError()
        assert isinstance(error, KubernetesError)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesValidationError:
    """Test KubernetesValidationError exception."""

    def test_init_default(self) -> None:
        """Test initialization with defaults."""
        error = KubernetesValidationError()
        assert error.message == "Invalid resource specification"
        assert error.status_code == 422
        assert error.validation_errors == {}

    def test_init_custom_message(self) -> None:
        """Test initialization with custom message."""
        error = KubernetesValidationError("Schema validation failed")
        assert error.message == "Schema validation failed"

    def test_init_with_validation_errors(self) -> None:
        """Test initialization with validation errors."""
        errors = {"spec.replicas": "must be positive", "metadata.name": "required"}
        error = KubernetesValidationError(validation_errors=errors)
        assert error.validation_errors == errors

    def test_init_with_status_code(self) -> None:
        """Test initialization with custom status code."""
        error = KubernetesValidationError(status_code=400)
        assert error.status_code == 400

    def test_empty_validation_errors_dict(self) -> None:
        """Test that validation_errors defaults to empty dict."""
        error = KubernetesValidationError()
        assert isinstance(error.validation_errors, dict)
        assert len(error.validation_errors) == 0

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = KubernetesValidationError()
        assert isinstance(error, KubernetesError)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesConflictError:
    """Test KubernetesConflictError exception."""

    def test_init_default(self) -> None:
        """Test initialization with default message."""
        error = KubernetesConflictError()
        assert error.message == "Resource conflict"
        assert error.status_code == 409

    def test_init_with_resource_type_and_name(self) -> None:
        """Test initialization with resource type and name."""
        error = KubernetesConflictError(resource_type="Pod", resource_name="test")
        assert error.message == "Pod 'test' already exists"

    def test_init_with_namespace(self) -> None:
        """Test initialization with namespace."""
        error = KubernetesConflictError(
            resource_type="ConfigMap",
            resource_name="config",
            namespace="default",
        )
        assert error.message == "ConfigMap 'config' already exists in namespace 'default'"

    def test_str_representation(self) -> None:
        """Test string representation."""
        error = KubernetesConflictError(
            resource_type="Secret",
            resource_name="credentials",
            namespace="prod",
        )
        result = str(error)
        assert "Secret 'credentials' already exists in namespace 'prod'" in result
        assert "(status: 409)" in result

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = KubernetesConflictError()
        assert isinstance(error, KubernetesError)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesTimeoutError:
    """Test KubernetesTimeoutError exception."""

    def test_init_default(self) -> None:
        """Test initialization with default message."""
        error = KubernetesTimeoutError()
        assert error.message == "Kubernetes operation timed out"
        assert error.timeout_seconds is None

    def test_init_custom_message(self) -> None:
        """Test initialization with custom message."""
        error = KubernetesTimeoutError("Watch timed out")
        assert error.message == "Watch timed out"

    def test_init_with_timeout_seconds(self) -> None:
        """Test initialization with timeout seconds."""
        error = KubernetesTimeoutError(timeout_seconds=300)
        assert error.message == "Kubernetes operation timed out (after 300s)"
        assert error.timeout_seconds == 300

    def test_init_custom_message_with_timeout(self) -> None:
        """Test initialization with custom message and timeout."""
        error = KubernetesTimeoutError("Pod ready check timed out", timeout_seconds=60)
        assert error.message == "Pod ready check timed out (after 60s)"
        assert error.timeout_seconds == 60

    def test_str_representation(self) -> None:
        """Test string representation."""
        error = KubernetesTimeoutError(timeout_seconds=120)
        assert str(error) == "Kubernetes operation timed out (after 120s)"

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = KubernetesTimeoutError()
        assert isinstance(error, KubernetesError)
