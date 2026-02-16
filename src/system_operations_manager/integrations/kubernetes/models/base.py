"""Base models for Kubernetes resource display."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class K8sEntityBase(BaseModel):
    """Base class for all Kubernetes display models."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    name: str = Field(description="Resource name")
    namespace: str | None = Field(default=None, description="Resource namespace")
    uid: str | None = Field(default=None, description="Kubernetes UID")
    creation_timestamp: str | None = Field(default=None, description="Creation time")
    labels: dict[str, str] | None = Field(default=None, description="Resource labels")
    annotations: dict[str, str] | None = Field(default=None, description="Resource annotations")

    _entity_name: ClassVar[str] = "entity"

    @property
    def age(self) -> str:
        """Human-readable age string."""
        if not self.creation_timestamp:
            return "Unknown"
        try:
            created = datetime.fromisoformat(self.creation_timestamp.replace("Z", "+00:00"))
            delta = datetime.now(UTC) - created
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes = remainder // 60
            if days > 0:
                return f"{days}d"
            if hours > 0:
                return f"{hours}h"
            return f"{minutes}m"
        except ValueError, TypeError:
            return "Unknown"


class OwnerReference(BaseModel):
    """Kubernetes owner reference."""

    model_config = ConfigDict(extra="ignore")

    api_version: str | None = None
    kind: str | None = None
    name: str | None = None
    uid: str | None = None

    @classmethod
    def from_k8s_object(cls, obj: Any) -> OwnerReference:
        """Create from a kubernetes OwnerReference object."""
        if obj is None:
            return cls()
        return cls(
            api_version=getattr(obj, "api_version", None),
            kind=getattr(obj, "kind", None),
            name=getattr(obj, "name", None),
            uid=getattr(obj, "uid", None),
        )


def _safe_get(obj: Any, *attrs: str, default: Any = None) -> Any:
    """Safely traverse nested attributes on kubernetes SDK objects."""
    current = obj
    for attr in attrs:
        if current is None:
            return default
        current = getattr(current, attr, None)
    return current if current is not None else default


def _get_timestamp(obj: Any) -> str | None:
    """Extract ISO timestamp string from a datetime or string."""
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def _get_labels(obj: Any) -> dict[str, str] | None:
    """Extract labels dict, returning None if empty."""
    labels = _safe_get(obj, "metadata", "labels")
    return dict(labels) if labels else None


def _get_annotations(obj: Any) -> dict[str, str] | None:
    """Extract annotations dict, returning None if empty."""
    annotations = _safe_get(obj, "metadata", "annotations")
    return dict(annotations) if annotations else None
