"""Unit tests for K8sBaseManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.services.kubernetes.base import K8sBaseManager


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


class TestK8sBaseManager:
    """Tests for K8sBaseManager base class."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_init(self, mock_k8s_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = K8sBaseManager(mock_k8s_client)

        assert manager._client == mock_k8s_client
        assert manager._log is not None

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_resolve_namespace_with_explicit_namespace(self, mock_k8s_client: MagicMock) -> None:
        """Should return explicit namespace when provided."""
        manager = K8sBaseManager(mock_k8s_client)

        result = manager._resolve_namespace("test-namespace")

        assert result == "test-namespace"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_resolve_namespace_with_none(self, mock_k8s_client: MagicMock) -> None:
        """Should return default namespace when None provided."""
        manager = K8sBaseManager(mock_k8s_client)

        result = manager._resolve_namespace(None)

        assert result == "default"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_handle_api_error(self, mock_k8s_client: MagicMock) -> None:
        """Should translate API exception through client."""
        manager = K8sBaseManager(mock_k8s_client)
        test_exception = Exception("Test error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            manager._handle_api_error(
                test_exception,
                resource_type="Pod",
                resource_name="test-pod",
                namespace="test-ns",
            )

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            test_exception,
            resource_type="Pod",
            resource_name="test-pod",
            namespace="test-ns",
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_entity_name_default(self, mock_k8s_client: MagicMock) -> None:
        """Base manager should have empty entity name."""
        manager = K8sBaseManager(mock_k8s_client)

        assert manager._entity_name == ""
