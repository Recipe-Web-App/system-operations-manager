"""Unit tests for Kubernetes TUI delete helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.tui.apps.kubernetes.delete_helpers import (
    RESOURCE_DELETE_MAP,
    delete_resource,
)
from system_operations_manager.tui.apps.kubernetes.types import (
    DELETABLE_TYPES,
    ResourceType,
)


@pytest.fixture
def mock_client() -> MagicMock:
    mock = MagicMock()
    mock.default_namespace = "default"
    return mock


class TestDeleteHelpers:
    @pytest.mark.unit
    def test_all_deletable_types_in_map(self) -> None:
        """Every DELETABLE_TYPE should have an entry in RESOURCE_DELETE_MAP."""
        for rt in DELETABLE_TYPES:
            assert rt in RESOURCE_DELETE_MAP, f"{rt} missing from RESOURCE_DELETE_MAP"

    @pytest.mark.unit
    def test_delete_namespaced_resource(self, mock_client: MagicMock) -> None:
        """Should call the correct namespaced delete method."""
        delete_resource(mock_client, ResourceType.PODS, "my-pod", "test-ns")
        mock_client.core_v1.delete_namespaced_pod.assert_called_once_with(
            name="my-pod", namespace="test-ns"
        )

    @pytest.mark.unit
    def test_delete_cluster_scoped_resource(self, mock_client: MagicMock) -> None:
        """Should call the correct cluster-scoped delete method."""
        delete_resource(mock_client, ResourceType.NAMESPACES, "my-ns", None)
        mock_client.core_v1.delete_namespace.assert_called_once_with(name="my-ns")

    @pytest.mark.unit
    def test_delete_deployment(self, mock_client: MagicMock) -> None:
        """Should call apps_v1 for deployment deletion."""
        delete_resource(mock_client, ResourceType.DEPLOYMENTS, "my-deploy", "default")
        mock_client.apps_v1.delete_namespaced_deployment.assert_called_once_with(
            name="my-deploy", namespace="default"
        )

    @pytest.mark.unit
    def test_delete_uses_default_namespace_when_none(self, mock_client: MagicMock) -> None:
        """Should fall back to client's default namespace."""
        delete_resource(mock_client, ResourceType.CONFIGMAPS, "my-cm", None)
        mock_client.core_v1.delete_namespaced_config_map.assert_called_once_with(
            name="my-cm", namespace="default"
        )

    @pytest.mark.unit
    def test_delete_unsupported_type_raises(self, mock_client: MagicMock) -> None:
        """Should raise KeyError for types not in the map."""
        with pytest.raises(KeyError):
            delete_resource(mock_client, ResourceType.NODES, "my-node", None)
