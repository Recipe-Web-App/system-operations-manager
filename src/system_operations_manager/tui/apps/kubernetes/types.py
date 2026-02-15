"""Resource type definitions for Kubernetes TUI browser.

This module defines the ResourceType enum and related constants,
extracted to avoid circular imports between app.py and screens.py.
"""

from __future__ import annotations

from enum import Enum


class ResourceType(Enum):
    """Kubernetes resource types available in the TUI browser."""

    # Workloads
    PODS = "Pods"
    DEPLOYMENTS = "Deployments"
    STATEFULSETS = "StatefulSets"
    DAEMONSETS = "DaemonSets"
    REPLICASETS = "ReplicaSets"

    # Networking
    SERVICES = "Services"
    INGRESSES = "Ingresses"
    NETWORK_POLICIES = "NetworkPolicies"

    # Configuration
    CONFIGMAPS = "ConfigMaps"
    SECRETS = "Secrets"

    # Cluster
    NAMESPACES = "Namespaces"
    NODES = "Nodes"
    EVENTS = "Events"


# Resource types that are cluster-scoped (not namespaced)
CLUSTER_SCOPED_TYPES = frozenset(
    {
        ResourceType.NAMESPACES,
        ResourceType.NODES,
    }
)

# Ordered list for cycling through types
RESOURCE_TYPE_ORDER = list(ResourceType)

# Resource types that support creation via the TUI
CREATABLE_TYPES = frozenset(
    {
        ResourceType.DEPLOYMENTS,
        ResourceType.STATEFULSETS,
        ResourceType.DAEMONSETS,
        ResourceType.SERVICES,
        ResourceType.INGRESSES,
        ResourceType.NETWORK_POLICIES,
        ResourceType.CONFIGMAPS,
        ResourceType.SECRETS,
        ResourceType.NAMESPACES,
    }
)

# Resource types that support editing (YAML patch) via the TUI
EDITABLE_TYPES = frozenset(
    {
        ResourceType.DEPLOYMENTS,
        ResourceType.STATEFULSETS,
        ResourceType.DAEMONSETS,
        ResourceType.SERVICES,
        ResourceType.INGRESSES,
        ResourceType.NETWORK_POLICIES,
        ResourceType.CONFIGMAPS,
        ResourceType.SECRETS,
        ResourceType.NAMESPACES,
    }
)

# Resource types that support deletion
DELETABLE_TYPES = frozenset(
    {
        ResourceType.PODS,
        ResourceType.DEPLOYMENTS,
        ResourceType.STATEFULSETS,
        ResourceType.DAEMONSETS,
        ResourceType.REPLICASETS,
        ResourceType.SERVICES,
        ResourceType.INGRESSES,
        ResourceType.NETWORK_POLICIES,
        ResourceType.CONFIGMAPS,
        ResourceType.SECRETS,
        ResourceType.NAMESPACES,
    }
)
