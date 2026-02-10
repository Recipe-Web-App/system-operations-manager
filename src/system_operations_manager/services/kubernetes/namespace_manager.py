"""Kubernetes namespace and cluster resource manager.

Manages Namespaces, Nodes, Events, and cluster-level information
through the Kubernetes API.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.cluster import (
    EventSummary,
    NamespaceSummary,
    NodeSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager


class NamespaceClusterManager(K8sBaseManager):
    """Manager for Kubernetes namespace and cluster resources.

    Provides operations for Namespaces, Nodes, Events, and cluster information.
    """

    _entity_name = "namespace_cluster"

    # =========================================================================
    # Namespace Operations
    # =========================================================================

    def list_namespaces(
        self,
        *,
        label_selector: str | None = None,
    ) -> list[NamespaceSummary]:
        """List all namespaces.

        Args:
            label_selector: Filter by label selector.

        Returns:
            List of namespace summaries.
        """
        self._log.debug("listing_namespaces")
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.core_v1.list_namespace(**kwargs)
            items = [NamespaceSummary.from_k8s_object(ns) for ns in result.items]
            self._log.debug("listed_namespaces", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "Namespace", None, None)

    def get_namespace(self, name: str) -> NamespaceSummary:
        """Get a single namespace by name.

        Args:
            name: Namespace name.

        Returns:
            Namespace summary.
        """
        self._log.debug("getting_namespace", name=name)
        try:
            result = self._client.core_v1.read_namespace(name=name)
            return NamespaceSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Namespace", name, None)

    def create_namespace(
        self,
        name: str,
        *,
        labels: dict[str, str] | None = None,
    ) -> NamespaceSummary:
        """Create a namespace.

        Args:
            name: Namespace name.
            labels: Namespace labels.

        Returns:
            Created namespace summary.
        """
        from kubernetes.client import V1Namespace, V1ObjectMeta

        body = V1Namespace(
            metadata=V1ObjectMeta(name=name, labels=labels),
        )

        self._log.info("creating_namespace", name=name)
        try:
            result = self._client.core_v1.create_namespace(body=body)
            self._log.info("created_namespace", name=name)
            return NamespaceSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Namespace", name, None)

    def delete_namespace(self, name: str) -> None:
        """Delete a namespace.

        Args:
            name: Namespace name.
        """
        self._log.info("deleting_namespace", name=name)
        try:
            self._client.core_v1.delete_namespace(name=name)
            self._log.info("deleted_namespace", name=name)
        except Exception as e:
            self._handle_api_error(e, "Namespace", name, None)

    # =========================================================================
    # Node Operations
    # =========================================================================

    def list_nodes(
        self,
        *,
        label_selector: str | None = None,
    ) -> list[NodeSummary]:
        """List all nodes.

        Args:
            label_selector: Filter by label selector.

        Returns:
            List of node summaries.
        """
        self._log.debug("listing_nodes")
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.core_v1.list_node(**kwargs)
            items = [NodeSummary.from_k8s_object(node) for node in result.items]
            self._log.debug("listed_nodes", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "Node", None, None)

    def get_node(self, name: str) -> NodeSummary:
        """Get a single node by name.

        Args:
            name: Node name.

        Returns:
            Node summary.
        """
        self._log.debug("getting_node", name=name)
        try:
            result = self._client.core_v1.read_node(name=name)
            return NodeSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Node", name, None)

    # =========================================================================
    # Event Operations
    # =========================================================================

    def list_events(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        field_selector: str | None = None,
        involved_object: str | None = None,
    ) -> list[EventSummary]:
        """List events.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            field_selector: Filter by field selector.
            involved_object: Filter by involved object name
                (adds involvedObject.name field selector).

        Returns:
            List of event summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_events", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}

            selectors = []
            if field_selector:
                selectors.append(field_selector)
            if involved_object:
                selectors.append(f"involvedObject.name={involved_object}")
            if selectors:
                kwargs["field_selector"] = ",".join(selectors)

            if all_namespaces:
                result = self._client.core_v1.list_event_for_all_namespaces(**kwargs)
            else:
                result = self._client.core_v1.list_namespaced_event(namespace=ns, **kwargs)

            items = [EventSummary.from_k8s_object(evt) for evt in result.items]
            self._log.debug("listed_events", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "Event", None, ns)

    # =========================================================================
    # Cluster Info
    # =========================================================================

    def get_cluster_info(self) -> dict[str, Any]:
        """Get cluster information summary.

        Returns:
            Dictionary with cluster version, node count, and namespace count.
        """
        self._log.debug("getting_cluster_info")
        info: dict[str, Any] = {}

        try:
            info["version"] = self._client.get_cluster_version()
        except Exception:
            info["version"] = "unknown"

        try:
            nodes = self._client.core_v1.list_node()
            info["node_count"] = len(nodes.items) if nodes.items else 0
        except Exception:
            info["node_count"] = "unknown"

        try:
            namespaces = self._client.core_v1.list_namespace()
            info["namespace_count"] = len(namespaces.items) if namespaces.items else 0
        except Exception:
            info["namespace_count"] = "unknown"

        info["context"] = self._client.get_current_context()
        info["default_namespace"] = self._client.default_namespace

        return info
