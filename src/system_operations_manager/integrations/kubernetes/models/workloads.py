"""Kubernetes workload resource display models."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
    OwnerReference,
    _get_annotations,
    _get_labels,
    _get_timestamp,
    _safe_get,
)


class ContainerStatus(K8sEntityBase):
    """Container status within a pod."""

    _entity_name: ClassVar[str] = "container"

    image: str | None = Field(default=None, description="Container image")
    ready: bool = Field(default=False, description="Whether container is ready")
    restart_count: int = Field(default=0, description="Number of restarts")
    state: str = Field(default="unknown", description="Current state")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> ContainerStatus:
        """Create from a kubernetes ContainerStatus object."""
        state = "unknown"
        if obj_state := getattr(obj, "state", None):
            if getattr(obj_state, "running", None):
                state = "running"
            elif getattr(obj_state, "waiting", None):
                reason = _safe_get(obj_state, "waiting", "reason", default="Waiting")
                state = str(reason)
            elif getattr(obj_state, "terminated", None):
                reason = _safe_get(obj_state, "terminated", "reason", default="Terminated")
                state = str(reason)

        return cls(
            name=getattr(obj, "name", ""),
            image=getattr(obj, "image", None),
            ready=getattr(obj, "ready", False) or False,
            restart_count=getattr(obj, "restart_count", 0) or 0,
            state=state,
        )


class PodSummary(K8sEntityBase):
    """Pod display model."""

    _entity_name: ClassVar[str] = "pod"

    phase: str = Field(default="Unknown", description="Pod phase")
    node_name: str | None = Field(default=None, description="Node the pod is running on")
    pod_ip: str | None = Field(default=None, description="Pod IP address")
    restarts: int = Field(default=0, description="Total container restarts")
    ready_count: int = Field(default=0, description="Number of ready containers")
    total_count: int = Field(default=0, description="Total number of containers")
    containers: list[ContainerStatus] = Field(
        default_factory=list, description="Container statuses"
    )

    @classmethod
    def from_k8s_object(cls, obj: Any) -> PodSummary:
        """Create from a kubernetes V1Pod object."""
        container_statuses = _safe_get(obj, "status", "container_statuses") or []
        containers = [ContainerStatus.from_k8s_object(cs) for cs in container_statuses]
        restarts = sum(c.restart_count for c in containers)
        ready_count = sum(1 for c in containers if c.ready)

        # Total containers from spec
        spec_containers = _safe_get(obj, "spec", "containers") or []
        total_count = len(spec_containers)

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            phase=_safe_get(obj, "status", "phase", default="Unknown"),
            node_name=_safe_get(obj, "spec", "node_name"),
            pod_ip=_safe_get(obj, "status", "pod_ip"),
            restarts=restarts,
            ready_count=ready_count,
            total_count=total_count,
            containers=containers,
        )


class DeploymentSummary(K8sEntityBase):
    """Deployment display model."""

    _entity_name: ClassVar[str] = "deployment"

    replicas: int = Field(default=0, description="Desired replicas")
    ready_replicas: int = Field(default=0, description="Ready replicas")
    available_replicas: int = Field(default=0, description="Available replicas")
    updated_replicas: int = Field(default=0, description="Updated replicas")
    strategy: str | None = Field(default=None, description="Deployment strategy")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> DeploymentSummary:
        """Create from a kubernetes V1Deployment object."""
        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            replicas=_safe_get(obj, "spec", "replicas", default=0) or 0,
            ready_replicas=_safe_get(obj, "status", "ready_replicas", default=0) or 0,
            available_replicas=_safe_get(obj, "status", "available_replicas", default=0) or 0,
            updated_replicas=_safe_get(obj, "status", "updated_replicas", default=0) or 0,
            strategy=_safe_get(obj, "spec", "strategy", "type"),
        )


class StatefulSetSummary(K8sEntityBase):
    """StatefulSet display model."""

    _entity_name: ClassVar[str] = "statefulset"

    replicas: int = Field(default=0, description="Desired replicas")
    ready_replicas: int = Field(default=0, description="Ready replicas")
    service_name: str | None = Field(default=None, description="Governing service name")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> StatefulSetSummary:
        """Create from a kubernetes V1StatefulSet object."""
        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            replicas=_safe_get(obj, "spec", "replicas", default=0) or 0,
            ready_replicas=_safe_get(obj, "status", "ready_replicas", default=0) or 0,
            service_name=_safe_get(obj, "spec", "service_name"),
        )


class DaemonSetSummary(K8sEntityBase):
    """DaemonSet display model."""

    _entity_name: ClassVar[str] = "daemonset"

    desired_number_scheduled: int = Field(default=0, description="Desired pods")
    current_number_scheduled: int = Field(default=0, description="Current pods")
    number_ready: int = Field(default=0, description="Ready pods")
    node_selector: dict[str, str] | None = Field(default=None, description="Node selector")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> DaemonSetSummary:
        """Create from a kubernetes V1DaemonSet object."""
        node_selector = _safe_get(obj, "spec", "template", "spec", "node_selector")
        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            desired_number_scheduled=_safe_get(obj, "status", "desired_number_scheduled", default=0)
            or 0,
            current_number_scheduled=_safe_get(obj, "status", "current_number_scheduled", default=0)
            or 0,
            number_ready=_safe_get(obj, "status", "number_ready", default=0) or 0,
            node_selector=dict(node_selector) if node_selector else None,
        )


class ReplicaSetSummary(K8sEntityBase):
    """ReplicaSet display model."""

    _entity_name: ClassVar[str] = "replicaset"

    replicas: int = Field(default=0, description="Desired replicas")
    ready_replicas: int = Field(default=0, description="Ready replicas")
    owner_references: list[OwnerReference] = Field(
        default_factory=list, description="Owner references"
    )

    @classmethod
    def from_k8s_object(cls, obj: Any) -> ReplicaSetSummary:
        """Create from a kubernetes V1ReplicaSet object."""
        owner_refs = _safe_get(obj, "metadata", "owner_references") or []
        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            replicas=_safe_get(obj, "spec", "replicas", default=0) or 0,
            ready_replicas=_safe_get(obj, "status", "ready_replicas", default=0) or 0,
            owner_references=[OwnerReference.from_k8s_object(ref) for ref in owner_refs],
        )
