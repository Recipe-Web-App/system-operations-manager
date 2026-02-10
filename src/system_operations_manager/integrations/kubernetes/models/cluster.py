"""Kubernetes cluster-level resource display models."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
    _get_annotations,
    _get_labels,
    _get_timestamp,
    _safe_get,
)


class NamespaceSummary(K8sEntityBase):
    """Namespace display model."""

    _entity_name: ClassVar[str] = "namespace"

    status: str = Field(default="Active", description="Namespace phase")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> NamespaceSummary:
        """Create from a kubernetes V1Namespace object."""
        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            status=_safe_get(obj, "status", "phase", default="Active"),
        )


class NodeSummary(K8sEntityBase):
    """Node display model."""

    _entity_name: ClassVar[str] = "node"

    status: str = Field(default="Unknown", description="Node status")
    roles: list[str] = Field(default_factory=list, description="Node roles")
    version: str | None = Field(default=None, description="Kubelet version")
    internal_ip: str | None = Field(default=None, description="Internal IP address")
    os_image: str | None = Field(default=None, description="OS image")
    kernel_version: str | None = Field(default=None, description="Kernel version")
    container_runtime: str | None = Field(default=None, description="Container runtime")
    cpu_capacity: str | None = Field(default=None, description="CPU capacity")
    memory_capacity: str | None = Field(default=None, description="Memory capacity")
    pods_capacity: str | None = Field(default=None, description="Pod capacity")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> NodeSummary:
        """Create from a kubernetes V1Node object."""
        # Extract roles from labels
        labels = _safe_get(obj, "metadata", "labels") or {}
        roles = []
        for key in labels:
            if key.startswith("node-role.kubernetes.io/"):
                role = key.split("/", 1)[1]
                if role:
                    roles.append(role)
        if not roles:
            roles = ["<none>"]

        # Determine node status from conditions
        status = "Unknown"
        conditions = _safe_get(obj, "status", "conditions") or []
        for cond in conditions:
            if getattr(cond, "type", None) == "Ready":
                status = "Ready" if getattr(cond, "status", "") == "True" else "NotReady"
                break

        # Internal IP
        addresses = _safe_get(obj, "status", "addresses") or []
        internal_ip = None
        for addr in addresses:
            if getattr(addr, "type", None) == "InternalIP":
                internal_ip = getattr(addr, "address", None)
                break

        # Node info
        node_info = _safe_get(obj, "status", "node_info")
        capacity = _safe_get(obj, "status", "capacity") or {}

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            status=status,
            roles=roles,
            version=_safe_get(node_info, "kubelet_version"),
            internal_ip=internal_ip,
            os_image=_safe_get(node_info, "os_image"),
            kernel_version=_safe_get(node_info, "kernel_version"),
            container_runtime=_safe_get(node_info, "container_runtime_version"),
            cpu_capacity=capacity.get("cpu") if isinstance(capacity, dict) else None,
            memory_capacity=capacity.get("memory") if isinstance(capacity, dict) else None,
            pods_capacity=capacity.get("pods") if isinstance(capacity, dict) else None,
        )


class EventSummary(K8sEntityBase):
    """Event display model."""

    _entity_name: ClassVar[str] = "event"

    type: str = Field(default="Normal", description="Event type (Normal/Warning)")
    reason: str | None = Field(default=None, description="Event reason")
    message: str | None = Field(default=None, description="Event message")
    source_component: str | None = Field(default=None, description="Event source component")
    first_timestamp: str | None = Field(default=None, description="First occurrence")
    last_timestamp: str | None = Field(default=None, description="Last occurrence")
    count: int = Field(default=1, description="Occurrence count")
    involved_object_kind: str | None = Field(default=None, description="Involved object kind")
    involved_object_name: str | None = Field(default=None, description="Involved object name")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> EventSummary:
        """Create from a kubernetes CoreV1Event object."""
        source = getattr(obj, "source", None)
        involved = getattr(obj, "involved_object", None)

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            type=getattr(obj, "type", "Normal") or "Normal",
            reason=getattr(obj, "reason", None),
            message=getattr(obj, "message", None),
            source_component=_safe_get(source, "component"),
            first_timestamp=_get_timestamp(getattr(obj, "first_timestamp", None)),
            last_timestamp=_get_timestamp(getattr(obj, "last_timestamp", None)),
            count=getattr(obj, "count", 1) or 1,
            involved_object_kind=_safe_get(involved, "kind"),
            involved_object_name=_safe_get(involved, "name"),
        )
