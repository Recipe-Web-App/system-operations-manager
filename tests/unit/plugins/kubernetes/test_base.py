"""Unit tests for Kubernetes base command utilities."""

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
class TestHandleK8sError:
    """Tests for handle_k8s_error function."""

    def test_handle_connection_error(self) -> None:
        """handle_k8s_error should handle KubernetesConnectionError."""
        error = KubernetesConnectionError("Cannot connect to cluster")

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_handle_connection_error_with_original_error(self) -> None:
        """handle_k8s_error should display original error if present."""
        original = ValueError("Network timeout")
        error = KubernetesConnectionError("Cannot connect", original_error=original)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_handle_auth_error(self) -> None:
        """handle_k8s_error should handle KubernetesAuthError."""
        error = KubernetesAuthError("Authentication failed", status_code=401)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_handle_not_found_error(self) -> None:
        """handle_k8s_error should handle KubernetesNotFoundError."""
        error = KubernetesNotFoundError(
            resource_type="Pod", resource_name="my-pod", namespace="default"
        )

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_handle_validation_error(self) -> None:
        """handle_k8s_error should handle KubernetesValidationError."""
        error = KubernetesValidationError(
            "Validation failed",
            validation_errors={"spec.replicas": "must be positive"},
        )

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_handle_conflict_error(self) -> None:
        """handle_k8s_error should handle KubernetesConflictError."""
        error = KubernetesConflictError(
            resource_type="Deployment", resource_name="my-app", namespace="production"
        )

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_handle_timeout_error(self) -> None:
        """handle_k8s_error should handle KubernetesTimeoutError."""
        error = KubernetesTimeoutError("Operation timed out", timeout_seconds=30)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1

    def test_handle_generic_kubernetes_error(self) -> None:
        """handle_k8s_error should handle base KubernetesError."""
        error = KubernetesError("Generic error", status_code=500)

        with pytest.raises(typer.Exit) as exc_info:
            handle_k8s_error(error)

        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestConfirmDelete:
    """Tests for confirm_delete function."""

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_delete_with_namespace(self, mock_confirm: MagicMock) -> None:
        """confirm_delete should prompt with namespace in message."""
        mock_confirm.return_value = True

        result = confirm_delete("pod", "my-pod", namespace="production")

        assert result is True
        mock_confirm.assert_called_once()
        call_args = mock_confirm.call_args[0][0]
        assert "pod" in call_args
        assert "my-pod" in call_args
        assert "production" in call_args

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_delete_without_namespace(self, mock_confirm: MagicMock) -> None:
        """confirm_delete should prompt without namespace when not provided."""
        mock_confirm.return_value = False

        result = confirm_delete("deployment", "my-app")

        assert result is False
        mock_confirm.assert_called_once()
        call_args = mock_confirm.call_args[0][0]
        assert "deployment" in call_args
        assert "my-app" in call_args

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_delete_returns_user_choice(self, mock_confirm: MagicMock) -> None:
        """confirm_delete should return user's confirmation choice."""
        mock_confirm.return_value = True
        assert confirm_delete("service", "svc") is True

        mock_confirm.return_value = False
        assert confirm_delete("service", "svc") is False


@pytest.mark.unit
@pytest.mark.kubernetes
class TestConfirmAction:
    """Tests for confirm_action function."""

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_action_with_default_false(self, mock_confirm: MagicMock) -> None:
        """confirm_action should use default=False."""
        mock_confirm.return_value = True

        result = confirm_action("Proceed with action?", default=False)

        assert result is True
        mock_confirm.assert_called_once_with("Proceed with action?", default=False)

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_action_with_default_true(self, mock_confirm: MagicMock) -> None:
        """confirm_action should use default=True."""
        mock_confirm.return_value = False

        result = confirm_action("Continue?", default=True)

        assert result is False
        mock_confirm.assert_called_once_with("Continue?", default=True)

    @patch("system_operations_manager.plugins.kubernetes.commands.base.typer.confirm")
    def test_confirm_action_returns_user_choice(self, mock_confirm: MagicMock) -> None:
        """confirm_action should return user's confirmation choice."""
        mock_confirm.return_value = True
        assert confirm_action("Test?") is True

        mock_confirm.return_value = False
        assert confirm_action("Test?") is False
