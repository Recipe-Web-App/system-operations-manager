"""Kubernetes storage resource display models."""

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


class PersistentVolumeSummary(K8sEntityBase):
    """PersistentVolume display model."""

    _entity_name: ClassVar[str] = "persistentvolume"

    capacity: str | None = Field(default=None, description="Storage capacity")
    access_modes: list[str] = Field(default_factory=list, description="Access modes")
    reclaim_policy: str | None = Field(default=None, description="Reclaim policy")
    status: str = Field(default="Available", description="Volume phase")
    storage_class: str | None = Field(default=None, description="Storage class name")
    claim_ref: str | None = Field(default=None, description="Bound PVC reference")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> PersistentVolumeSummary:
        """Create from a kubernetes V1PersistentVolume object."""
        capacity = _safe_get(obj, "spec", "capacity") or {}
        storage_capacity = capacity.get("storage") if isinstance(capacity, dict) else None

        # Claim reference
        claim = _safe_get(obj, "spec", "claim_ref")
        claim_ref = None
        if claim:
            claim_ns = getattr(claim, "namespace", "")
            claim_name = getattr(claim, "name", "")
            claim_ref = f"{claim_ns}/{claim_name}" if claim_ns else claim_name

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            capacity=str(storage_capacity) if storage_capacity else None,
            access_modes=list(_safe_get(obj, "spec", "access_modes") or []),
            reclaim_policy=_safe_get(obj, "spec", "persistent_volume_reclaim_policy"),
            status=_safe_get(obj, "status", "phase", default="Available"),
            storage_class=_safe_get(obj, "spec", "storage_class_name"),
            claim_ref=claim_ref,
        )


class PersistentVolumeClaimSummary(K8sEntityBase):
    """PersistentVolumeClaim display model."""

    _entity_name: ClassVar[str] = "persistentvolumeclaim"

    status: str = Field(default="Pending", description="PVC phase")
    volume: str | None = Field(default=None, description="Bound volume name")
    capacity: str | None = Field(default=None, description="Allocated capacity")
    access_modes: list[str] = Field(default_factory=list, description="Access modes")
    storage_class: str | None = Field(default=None, description="Storage class name")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> PersistentVolumeClaimSummary:
        """Create from a kubernetes V1PersistentVolumeClaim object."""
        # Capacity from status (actual allocation)
        status_capacity = _safe_get(obj, "status", "capacity") or {}
        capacity = status_capacity.get("storage") if isinstance(status_capacity, dict) else None

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            status=_safe_get(obj, "status", "phase", default="Pending"),
            volume=_safe_get(obj, "spec", "volume_name"),
            capacity=str(capacity) if capacity else None,
            access_modes=list(_safe_get(obj, "status", "access_modes") or []),
            storage_class=_safe_get(obj, "spec", "storage_class_name"),
        )


class StorageClassSummary(K8sEntityBase):
    """StorageClass display model."""

    _entity_name: ClassVar[str] = "storageclass"

    provisioner: str = Field(default="", description="Volume provisioner")
    reclaim_policy: str | None = Field(default=None, description="Reclaim policy")
    volume_binding_mode: str | None = Field(default=None, description="Volume binding mode")
    allow_volume_expansion: bool = Field(
        default=False, description="Whether volume expansion is allowed"
    )

    @classmethod
    def from_k8s_object(cls, obj: Any) -> StorageClassSummary:
        """Create from a kubernetes V1StorageClass object."""
        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            provisioner=getattr(obj, "provisioner", "") or "",
            reclaim_policy=getattr(obj, "reclaim_policy", None),
            volume_binding_mode=getattr(obj, "volume_binding_mode", None),
            allow_volume_expansion=getattr(obj, "allow_volume_expansion", False) or False,
        )
