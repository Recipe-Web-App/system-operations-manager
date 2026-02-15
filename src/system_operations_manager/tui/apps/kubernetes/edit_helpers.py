"""Helpers for YAML-based editing of Kubernetes resources via TUI.

Provides functions to fetch raw Kubernetes objects as clean YAML-ready
dicts and apply edited dicts back as strategic merge patches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from system_operations_manager.tui.apps.kubernetes.types import ResourceType

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient

# Maps ResourceType -> (api_property, read_method, patch_method, is_namespaced)
RESOURCE_API_MAP: dict[ResourceType, tuple[str, str, str, bool]] = {
    ResourceType.DEPLOYMENTS: (
        "apps_v1",
        "read_namespaced_deployment",
        "patch_namespaced_deployment",
        True,
    ),
    ResourceType.STATEFULSETS: (
        "apps_v1",
        "read_namespaced_stateful_set",
        "patch_namespaced_stateful_set",
        True,
    ),
    ResourceType.DAEMONSETS: (
        "apps_v1",
        "read_namespaced_daemon_set",
        "patch_namespaced_daemon_set",
        True,
    ),
    ResourceType.SERVICES: (
        "core_v1",
        "read_namespaced_service",
        "patch_namespaced_service",
        True,
    ),
    ResourceType.INGRESSES: (
        "networking_v1",
        "read_namespaced_ingress",
        "patch_namespaced_ingress",
        True,
    ),
    ResourceType.NETWORK_POLICIES: (
        "networking_v1",
        "read_namespaced_network_policy",
        "patch_namespaced_network_policy",
        True,
    ),
    ResourceType.CONFIGMAPS: (
        "core_v1",
        "read_namespaced_config_map",
        "patch_namespaced_config_map",
        True,
    ),
    ResourceType.SECRETS: (
        "core_v1",
        "read_namespaced_secret",
        "patch_namespaced_secret",
        True,
    ),
    ResourceType.NAMESPACES: (
        "core_v1",
        "read_namespace",
        "patch_namespace",
        False,
    ),
}

# Metadata fields managed by the server that should not be shown in the editor
STRIP_METADATA_KEYS = frozenset(
    {
        "managedFields",
        "resourceVersion",
        "uid",
        "creationTimestamp",
        "generation",
        "selfLink",
        "deletionTimestamp",
        "deletionGracePeriodSeconds",
    }
)


def _strip_server_fields(obj_dict: dict[str, Any]) -> dict[str, Any]:
    """Remove server-managed fields from a resource dict.

    Strips the ``status`` block and server-managed metadata keys so the
    user sees only the editable portion of the resource.
    """
    obj_dict.pop("status", None)
    metadata = obj_dict.get("metadata", {})
    if isinstance(metadata, dict):
        for key in STRIP_METADATA_KEYS:
            metadata.pop(key, None)
    return obj_dict


def fetch_raw_resource(
    client: KubernetesClient,
    resource_type: ResourceType,
    name: str,
    namespace: str | None,
) -> dict[str, Any]:
    """Fetch a raw Kubernetes object as a clean camelCase dict.

    The returned dict has server-managed fields stripped and is suitable
    for presenting in a YAML editor and round-tripping back through
    :func:`apply_patch`.

    Args:
        client: Kubernetes API client.
        resource_type: Type of resource to fetch.
        name: Resource name.
        namespace: Resource namespace (ignored for cluster-scoped types).

    Returns:
        Clean camelCase dict ready for YAML serialization.

    Raises:
        KeyError: If the resource type is not editable.
        KubernetesError: If the API call fails.
    """
    from kubernetes.client import ApiClient

    api_attr, read_method, _, is_namespaced = RESOURCE_API_MAP[resource_type]
    api = getattr(client, api_attr)
    read_fn = getattr(api, read_method)

    if is_namespaced:
        raw = read_fn(name=name, namespace=namespace or client.default_namespace)
    else:
        raw = read_fn(name=name)

    # sanitize_for_serialization returns camelCase dict matching the K8s API
    api_client = ApiClient()
    obj_dict = api_client.sanitize_for_serialization(raw)

    return _strip_server_fields(obj_dict)


def apply_patch(
    client: KubernetesClient,
    resource_type: ResourceType,
    name: str,
    namespace: str | None,
    patch_body: dict[str, Any],
) -> None:
    """Apply a strategic merge patch to a Kubernetes resource.

    Args:
        client: Kubernetes API client.
        resource_type: Type of resource to patch.
        name: Resource name.
        namespace: Resource namespace (ignored for cluster-scoped types).
        patch_body: camelCase dict to apply as a strategic merge patch.

    Raises:
        KeyError: If the resource type is not editable.
        KubernetesError: If the API call fails.
    """
    api_attr, _, patch_method, is_namespaced = RESOURCE_API_MAP[resource_type]
    api = getattr(client, api_attr)
    patch_fn = getattr(api, patch_method)

    if is_namespaced:
        patch_fn(
            name=name,
            namespace=namespace or client.default_namespace,
            body=patch_body,
        )
    else:
        patch_fn(name=name, body=patch_body)
