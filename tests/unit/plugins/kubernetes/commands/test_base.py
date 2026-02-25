"""Unit tests for Kubernetes base command utilities (commands-level)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import typer

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConflictError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesTimeoutError,
    KubernetesValidationError,
)
from system_operations_manager.plugins.kubernetes.commands.base import (
    confirm_action,
    confirm_delete,
    handle_k8s_error,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHandleK8sErrorConnectionError:
    """Tests for handle_k8s_error with KubernetesConnectionError."""

    def test_connection_error_without_original_error(self) -> None:
        """Should handle KubernetesConnectionError with no original_error."""
        error = KubernetesConnectionError("Cannot connect to cluster")

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_connection_error_with_original_error(self) -> None:
        """Should display original error cause when present."""
        original = ConnectionRefusedError("Connection refused")
        error = KubernetesConnectionError("Cannot connect to cluster", original_error=original)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_connection_error_original_error_none(self) -> None:
        """Should not display cause when original_error is None."""
        error = KubernetesConnectionError("Cannot connect")
        error.original_error = None

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHandleK8sErrorAuthError:
    """Tests for handle_k8s_error with KubernetesAuthError."""

    def test_auth_error_401(self) -> None:
        """Should handle KubernetesAuthError with 401 status."""
        error = KubernetesAuthError("Unauthorized", status_code=401)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_auth_error_403(self) -> None:
        """Should handle KubernetesAuthError with 403 status."""
        error = KubernetesAuthError("Forbidden", status_code=403)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_auth_error_default(self) -> None:
        """Should handle KubernetesAuthError with default message."""
        error = KubernetesAuthError()

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHandleK8sErrorNotFound:
    """Tests for handle_k8s_error with KubernetesNotFoundError."""

    def test_not_found_error(self) -> None:
        """Should handle KubernetesNotFoundError."""
        error = KubernetesNotFoundError(
            resource_type="Pod", resource_name="my-pod", namespace="default"
        )

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_not_found_error_no_resource(self) -> None:
        """Should handle KubernetesNotFoundError with only a message."""
        error = KubernetesNotFoundError("Resource not found")

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHandleK8sErrorValidation:
    """Tests for handle_k8s_error with KubernetesValidationError."""

    def test_validation_error_with_field_errors(self) -> None:
        """Should display field errors when validation_errors is populated."""
        error = KubernetesValidationError(
            "Validation failed",
            validation_errors={
                "spec.replicas": "must be positive",
                "spec.image": "must not be empty",
            },
        )

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_validation_error_without_field_errors(self) -> None:
        """Should handle KubernetesValidationError with empty validation_errors."""
        error = KubernetesValidationError("Invalid spec", validation_errors=None)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_validation_error_empty_dict(self) -> None:
        """Should handle KubernetesValidationError with empty dict."""
        error = KubernetesValidationError("Invalid", validation_errors={})

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHandleK8sErrorConflict:
    """Tests for handle_k8s_error with KubernetesConflictError."""

    def test_conflict_error(self) -> None:
        """Should handle KubernetesConflictError."""
        error = KubernetesConflictError(
            resource_type="Deployment", resource_name="my-app", namespace="production"
        )

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_conflict_error_no_resource(self) -> None:
        """Should handle KubernetesConflictError with only a message."""
        error = KubernetesConflictError("Resource conflict")

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHandleK8sErrorTimeout:
    """Tests for handle_k8s_error with KubernetesTimeoutError."""

    def test_timeout_error_with_seconds(self) -> None:
        """Should handle KubernetesTimeoutError with timeout_seconds."""
        error = KubernetesTimeoutError("Operation timed out", timeout_seconds=30)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_timeout_error_no_seconds(self) -> None:
        """Should handle KubernetesTimeoutError without timeout_seconds."""
        error = KubernetesTimeoutError("Operation timed out")

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHandleK8sErrorGeneric:
    """Tests for handle_k8s_error with generic KubernetesError."""

    def test_generic_error_with_status_code(self) -> None:
        """Should display HTTP status for generic KubernetesError with status_code."""
        error = KubernetesError("Unexpected error", status_code=500)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_generic_error_without_status_code(self) -> None:
        """Should handle generic KubernetesError without status_code."""
        error = KubernetesError("Unexpected error")

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestConfirmDelete:
    """Tests for confirm_delete function."""

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_delete_with_namespace(self, mock_confirm: MagicMock) -> None:
        """Should include namespace in confirmation message."""
        mock_confirm.return_value = True

        result = confirm_delete("pod", "my-pod", namespace="production")

        assert result is True
        call_args = mock_confirm.call_args[0][0]
        assert "pod" in call_args
        assert "my-pod" in call_args
        assert "production" in call_args

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_delete_without_namespace(self, mock_confirm: MagicMock) -> None:
        """Should not include namespace when not provided."""
        mock_confirm.return_value = False

        result = confirm_delete("deployment", "my-app")

        assert result is False
        call_args = mock_confirm.call_args[0][0]
        assert "deployment" in call_args
        assert "my-app" in call_args
        assert "namespace" not in call_args.lower()

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_delete_returns_true(self, mock_confirm: MagicMock) -> None:
        """Should return True when user confirms."""
        mock_confirm.return_value = True

        assert confirm_delete("service", "svc") is True

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_delete_returns_false(self, mock_confirm: MagicMock) -> None:
        """Should return False when user declines."""
        mock_confirm.return_value = False

        assert confirm_delete("service", "svc") is False


@pytest.mark.unit
@pytest.mark.kubernetes
class TestConfirmAction:
    """Tests for confirm_action function."""

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_action_default_false(self, mock_confirm: MagicMock) -> None:
        """Should call typer.confirm with default=False."""
        mock_confirm.return_value = True

        result = confirm_action("Proceed?", default=False)

        assert result is True
        mock_confirm.assert_called_once_with("Proceed?", default=False)

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_action_default_true(self, mock_confirm: MagicMock) -> None:
        """Should call typer.confirm with default=True."""
        mock_confirm.return_value = False

        result = confirm_action("Continue?", default=True)

        assert result is False
        mock_confirm.assert_called_once_with("Continue?", default=True)

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_action_no_default(self, mock_confirm: MagicMock) -> None:
        """Should use default=False when no default specified."""
        mock_confirm.return_value = True

        result = confirm_action("Test?")

        assert result is True
        mock_confirm.assert_called_once_with("Test?", default=False)
