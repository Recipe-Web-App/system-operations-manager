"""Helpers for deleting Kubernetes resources via TUI.

Maps resource types to their corresponding Kubernetes API delete methods
for uniform dispatch from any TUI screen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from system_operations_manager.tui.apps.kubernetes.types import ResourceType

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient

# Maps ResourceType -> (api_property, delete_method_name, is_namespaced)
RESOURCE_DELETE_MAP: dict[ResourceType, tuple[str, str, bool]] = {
    ResourceType.PODS: ("core_v1", "delete_namespaced_pod", True),
    ResourceType.DEPLOYMENTS: ("apps_v1", "delete_namespaced_deployment", True),
    ResourceType.STATEFULSETS: ("apps_v1", "delete_namespaced_stateful_set", True),
    ResourceType.DAEMONSETS: ("apps_v1", "delete_namespaced_daemon_set", True),
    ResourceType.REPLICASETS: ("apps_v1", "delete_namespaced_replica_set", True),
    ResourceType.SERVICES: ("core_v1", "delete_namespaced_service", True),
    ResourceType.INGRESSES: ("networking_v1", "delete_namespaced_ingress", True),
    ResourceType.NETWORK_POLICIES: (
        "networking_v1",
        "delete_namespaced_network_policy",
        True,
    ),
    ResourceType.CONFIGMAPS: ("core_v1", "delete_namespaced_config_map", True),
    ResourceType.SECRETS: ("core_v1", "delete_namespaced_secret", True),
    ResourceType.NAMESPACES: ("core_v1", "delete_namespace", False),
}


def delete_resource(
    client: KubernetesClient,
    resource_type: ResourceType,
    name: str,
    namespace: str | None,
) -> None:
    """Delete a Kubernetes resource.

    Args:
        client: Kubernetes API client.
        resource_type: Type of resource to delete.
        name: Resource name.
        namespace: Resource namespace (ignored for cluster-scoped types).

    Raises:
        KeyError: If the resource type does not support deletion.
        KubernetesError: If the API call fails.
    """
    api_attr, delete_method, is_namespaced = RESOURCE_DELETE_MAP[resource_type]
    api = getattr(client, api_attr)
    delete_fn = getattr(api, delete_method)

    if is_namespaced:
        delete_fn(name=name, namespace=namespace or client.default_namespace)
    else:
        delete_fn(name=name)
