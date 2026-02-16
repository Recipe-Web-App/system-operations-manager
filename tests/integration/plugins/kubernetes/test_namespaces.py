"""Integration tests for NamespaceClusterManager."""

from __future__ import annotations

import contextlib

import pytest

from system_operations_manager.integrations.kubernetes.client import KubernetesClient
from system_operations_manager.services.kubernetes import NamespaceClusterManager


@pytest.mark.integration
@pytest.mark.kubernetes
class TestNamespaceCRUD:
    """Test namespace CRUD operations."""

    def test_list_namespaces(
        self,
        namespace_manager: NamespaceClusterManager,
    ) -> None:
        """list_namespaces should return default Kubernetes namespaces."""
        namespaces = namespace_manager.list_namespaces()

        assert len(namespaces) >= 2
        namespace_names = [ns.name for ns in namespaces]
        assert "default" in namespace_names
        assert "kube-system" in namespace_names

    def test_create_namespace(
        self,
        namespace_manager: NamespaceClusterManager,
        unique_name: str,
        k8s_client: KubernetesClient,
    ) -> None:
        """create_namespace should create a new namespace."""
        ns_name = f"test-ns-{unique_name}"

        try:
            result = namespace_manager.create_namespace(ns_name)

            assert result.name == ns_name
            assert result.status == "Active"

            # Verify it exists
            retrieved = namespace_manager.get_namespace(ns_name)
            assert retrieved.name == ns_name
        finally:
            # Cleanup
            with contextlib.suppress(Exception):
                k8s_client.core_v1.delete_namespace(name=ns_name)

    def test_get_namespace(
        self,
        namespace_manager: NamespaceClusterManager,
    ) -> None:
        """get_namespace should retrieve an existing namespace."""
        result = namespace_manager.get_namespace("default")

        assert result.name == "default"
        assert result.status == "Active"

    def test_delete_namespace(
        self,
        namespace_manager: NamespaceClusterManager,
        unique_name: str,
        k8s_client: KubernetesClient,
    ) -> None:
        """delete_namespace should delete a namespace."""
        ns_name = f"test-ns-{unique_name}"

        # Create namespace first
        k8s_client.core_v1.create_namespace(
            body={
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": ns_name},
            }
        )

        # Wait for it to be active
        import time

        for _ in range(30):
            ns = k8s_client.core_v1.read_namespace(name=ns_name)
            if ns.status.phase == "Active":
                break
            time.sleep(0.5)

        # Delete it
        namespace_manager.delete_namespace(ns_name)

        # Verify deletion in progress (status will be Terminating)
        try:
            ns = k8s_client.core_v1.read_namespace(name=ns_name)
            assert ns.status.phase == "Terminating"
        except Exception:
            # Already deleted
            pass

    def test_create_namespace_with_labels(
        self,
        namespace_manager: NamespaceClusterManager,
        unique_name: str,
        k8s_client: KubernetesClient,
    ) -> None:
        """create_namespace should support labels."""
        ns_name = f"test-ns-{unique_name}"
        labels = {"environment": "test", "team": "platform"}

        try:
            result = namespace_manager.create_namespace(ns_name, labels=labels)

            assert result.name == ns_name
            assert result.labels is not None
            assert result.labels["environment"] == "test"
            assert result.labels["team"] == "platform"
        finally:
            # Cleanup
            with contextlib.suppress(Exception):
                k8s_client.core_v1.delete_namespace(name=ns_name)

    def test_update_namespace(
        self,
        namespace_manager: NamespaceClusterManager,
        unique_name: str,
        k8s_client: KubernetesClient,
    ) -> None:
        """update_namespace should update namespace metadata."""
        ns_name = f"test-ns-{unique_name}"

        # Create namespace
        k8s_client.core_v1.create_namespace(
            body={
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": ns_name},
            }
        )

        try:
            # Wait for it to be active
            import time

            for _ in range(30):
                ns = k8s_client.core_v1.read_namespace(name=ns_name)
                if ns.status.phase == "Active":
                    break
                time.sleep(0.5)

            # Update labels
            new_labels = {"updated": "true", "version": "v2"}
            result = namespace_manager.update_namespace(ns_name, labels=new_labels)

            assert result.name == ns_name
            assert result.labels is not None
            assert result.labels["updated"] == "true"
            assert result.labels["version"] == "v2"
        finally:
            # Cleanup
            with contextlib.suppress(Exception):
                k8s_client.core_v1.delete_namespace(name=ns_name)

    def test_list_namespaces_with_label_selector(
        self,
        namespace_manager: NamespaceClusterManager,
        unique_name: str,
        k8s_client: KubernetesClient,
    ) -> None:
        """list_namespaces should filter by label selector."""
        ns_name = f"test-ns-{unique_name}"
        labels = {"test-filter": "active"}

        try:
            # Create namespace with labels
            namespace_manager.create_namespace(ns_name, labels=labels)

            # List with label selector
            namespaces = namespace_manager.list_namespaces(label_selector="test-filter=active")

            assert len(namespaces) >= 1
            assert any(ns.name == ns_name for ns in namespaces)
        finally:
            # Cleanup
            with contextlib.suppress(Exception):
                k8s_client.core_v1.delete_namespace(name=ns_name)


@pytest.mark.integration
@pytest.mark.kubernetes
class TestNodeOperations:
    """Test node operations."""

    def test_list_nodes(
        self,
        namespace_manager: NamespaceClusterManager,
    ) -> None:
        """list_nodes should return at least one node in K3S cluster."""
        nodes = namespace_manager.list_nodes()

        assert len(nodes) >= 1
        # Verify node has expected attributes
        node = nodes[0]
        assert node.name is not None
        assert node.status is not None

    def test_get_node(
        self,
        namespace_manager: NamespaceClusterManager,
    ) -> None:
        """get_node should retrieve a node by name."""
        # First get the list of nodes to find a valid name
        nodes = namespace_manager.list_nodes()
        assert len(nodes) >= 1

        node_name = nodes[0].name
        result = namespace_manager.get_node(node_name)

        assert result.name == node_name
        assert result.status is not None
