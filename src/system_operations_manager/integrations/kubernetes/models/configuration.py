"""Kubernetes configuration resource display models."""

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


class ConfigMapSummary(K8sEntityBase):
    """ConfigMap display model."""

    _entity_name: ClassVar[str] = "configmap"

    data_keys: list[str] = Field(default_factory=list, description="Data key names")
    binary_data_keys: list[str] = Field(default_factory=list, description="Binary data key names")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> ConfigMapSummary:
        """Create from a kubernetes V1ConfigMap object."""
        data = getattr(obj, "data", None) or {}
        binary_data = getattr(obj, "binary_data", None) or {}

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            data_keys=sorted(data.keys()),
            binary_data_keys=sorted(binary_data.keys()),
        )


class SecretSummary(K8sEntityBase):
    """Secret display model.

    SECURITY: Never includes actual secret data values. Only key names are exposed.
    """

    _entity_name: ClassVar[str] = "secret"

    type: str = Field(default="Opaque", description="Secret type")
    data_keys: list[str] = Field(default_factory=list, description="Data key names (values hidden)")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> SecretSummary:
        """Create from a kubernetes V1Secret object.

        Only extracts key names - never includes secret values.
        """
        data = getattr(obj, "data", None) or {}

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            type=getattr(obj, "type", "Opaque") or "Opaque",
            data_keys=sorted(data.keys()),
        )
