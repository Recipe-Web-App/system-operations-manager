"""Unit tests for NamespaceClusterManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.namespace_manager import (
    NamespaceClusterManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def namespace_manager(mock_k8s_client: MagicMock) -> NamespaceClusterManager:
    """Create a NamespaceClusterManager instance with mocked client."""
    return NamespaceClusterManager(mock_k8s_client)


class TestNamespaceOperations:
    """Tests for Namespace operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_namespaces_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list namespaces successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespace.return_value = mock_response

        result = namespace_manager.list_namespaces()

        assert result == []
        mock_k8s_client.core_v1.list_namespace.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_namespaces_empty(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no namespaces exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespace.return_value = mock_response

        result = namespace_manager.list_namespaces()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_namespaces_with_selector(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list namespaces with label selector."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespace.return_value = mock_response

        namespace_manager.list_namespaces(label_selector="env=prod")

        mock_k8s_client.core_v1.list_namespace.assert_called_once_with(label_selector="env=prod")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_namespaces_error(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing namespaces."""
        mock_k8s_client.core_v1.list_namespace.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            namespace_manager.list_namespaces()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_namespace_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get namespace successfully."""
        mock_namespace = MagicMock()
        mock_k8s_client.core_v1.read_namespace.return_value = mock_namespace

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = namespace_manager.get_namespace("test-ns")

            assert result == mock_summary
            mock_k8s_client.core_v1.read_namespace.assert_called_once_with(name="test-ns")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_namespace_error(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting namespace."""
        mock_k8s_client.core_v1.read_namespace.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            namespace_manager.get_namespace("test-ns")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_namespace_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create namespace successfully."""
        mock_namespace = MagicMock()
        mock_k8s_client.core_v1.create_namespace.return_value = mock_namespace

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = namespace_manager.create_namespace("test-ns", labels={"env": "test"})

            assert result == mock_summary
            mock_k8s_client.core_v1.create_namespace.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_namespace_error(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating namespace."""
        mock_k8s_client.core_v1.create_namespace.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            namespace_manager.create_namespace("test-ns")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_namespace_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete namespace successfully."""
        namespace_manager.delete_namespace("test-ns")

        mock_k8s_client.core_v1.delete_namespace.assert_called_once_with(name="test-ns")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_namespace_error(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting namespace."""
        mock_k8s_client.core_v1.delete_namespace.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            namespace_manager.delete_namespace("test-ns")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_namespace_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update namespace successfully."""
        mock_namespace = MagicMock()
        mock_k8s_client.core_v1.patch_namespace.return_value = mock_namespace

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = namespace_manager.update_namespace("test-ns", labels={"env": "production"})

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_namespace_error(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating namespace."""
        mock_k8s_client.core_v1.patch_namespace.side_effect = Exception("Update error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            namespace_manager.update_namespace("test-ns")


class TestNodeOperations:
    """Tests for Node operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_nodes_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list nodes successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_node.return_value = mock_response

        result = namespace_manager.list_nodes()

        assert result == []
        mock_k8s_client.core_v1.list_node.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_nodes_empty(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no nodes exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_node.return_value = mock_response

        result = namespace_manager.list_nodes()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_nodes_error(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing nodes."""
        mock_k8s_client.core_v1.list_node.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            namespace_manager.list_nodes()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_node_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get node successfully."""
        mock_node = MagicMock()
        mock_k8s_client.core_v1.read_node.return_value = mock_node

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NodeSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = namespace_manager.get_node("test-node")

            assert result == mock_summary
            mock_k8s_client.core_v1.read_node.assert_called_once_with(name="test-node")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_node_error(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting node."""
        mock_k8s_client.core_v1.read_node.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            namespace_manager.get_node("test-node")


class TestEventOperations:
    """Tests for Event operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_events_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list events successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_event.return_value = mock_response

        result = namespace_manager.list_events()

        assert result == []
        mock_k8s_client.core_v1.list_namespaced_event.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_events_empty(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no events exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_event.return_value = mock_response

        result = namespace_manager.list_events()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_events_all_namespaces(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list events across all namespaces."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_event_for_all_namespaces.return_value = mock_response

        result = namespace_manager.list_events(all_namespaces=True)

        assert result == []
        mock_k8s_client.core_v1.list_event_for_all_namespaces.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_events_with_selectors(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list events with field selector."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_event.return_value = mock_response

        namespace_manager.list_events(field_selector="type=Warning", involved_object="test-pod")

        mock_k8s_client.core_v1.list_namespaced_event.assert_called_once()
        call_kwargs = mock_k8s_client.core_v1.list_namespaced_event.call_args[1]
        assert "field_selector" in call_kwargs
        assert "type=Warning" in call_kwargs["field_selector"]
        assert "involvedObject.name=test-pod" in call_kwargs["field_selector"]

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_events_error(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing events."""
        mock_k8s_client.core_v1.list_namespaced_event.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            namespace_manager.list_events()


class TestClusterInfo:
    """Tests for cluster info operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_cluster_info_success(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get cluster info successfully."""
        mock_k8s_client.get_cluster_version.return_value = "v1.28.0"
        mock_k8s_client.get_current_context.return_value = "test-context"

        mock_nodes = MagicMock()
        mock_nodes.items = [MagicMock(), MagicMock()]
        mock_k8s_client.core_v1.list_node.return_value = mock_nodes

        mock_namespaces = MagicMock()
        mock_namespaces.items = [MagicMock(), MagicMock(), MagicMock()]
        mock_k8s_client.core_v1.list_namespace.return_value = mock_namespaces

        result = namespace_manager.get_cluster_info()

        assert result["version"] == "v1.28.0"
        assert result["node_count"] == 2
        assert result["namespace_count"] == 3
        assert result["context"] == "test-context"
        assert result["default_namespace"] == "default"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_cluster_info_with_errors(
        self, namespace_manager: NamespaceClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle partial errors when getting cluster info."""
        mock_k8s_client.get_cluster_version.side_effect = Exception("Version error")
        mock_k8s_client.get_current_context.return_value = "test-context"
        mock_k8s_client.core_v1.list_node.side_effect = Exception("Node error")
        mock_k8s_client.core_v1.list_namespace.side_effect = Exception("Namespace error")

        result = namespace_manager.get_cluster_info()

        assert result["version"] == "unknown"
        assert result["node_count"] == "unknown"
        assert result["namespace_count"] == "unknown"
        assert result["context"] == "test-context"
