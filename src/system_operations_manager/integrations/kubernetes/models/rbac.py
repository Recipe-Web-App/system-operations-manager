"""Kubernetes RBAC resource display models."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
    _get_annotations,
    _get_labels,
    _get_timestamp,
    _safe_get,
)


class Subject(BaseModel):
    """RBAC subject (user, group, or service account)."""

    model_config = ConfigDict(extra="ignore")

    kind: str = Field(description="Subject kind (User, Group, ServiceAccount)")
    name: str = Field(description="Subject name")
    namespace: str | None = Field(default=None, description="Subject namespace")
    api_group: str | None = Field(default=None, description="API group")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> Subject:
        """Create from a kubernetes V1Subject object."""
        return cls(
            kind=getattr(obj, "kind", "") or "",
            name=getattr(obj, "name", "") or "",
            namespace=getattr(obj, "namespace", None),
            api_group=getattr(obj, "api_group", None),
        )


class PolicyRule(BaseModel):
    """RBAC policy rule."""

    model_config = ConfigDict(extra="ignore")

    verbs: list[str] = Field(default_factory=list, description="Allowed verbs")
    api_groups: list[str] = Field(default_factory=list, description="API groups")
    resources: list[str] = Field(default_factory=list, description="Resources")
    resource_names: list[str] = Field(default_factory=list, description="Resource names")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> PolicyRule:
        """Create from a kubernetes V1PolicyRule object."""
        return cls(
            verbs=list(getattr(obj, "verbs", []) or []),
            api_groups=list(getattr(obj, "api_groups", []) or []),
            resources=list(getattr(obj, "resources", []) or []),
            resource_names=list(getattr(obj, "resource_names", []) or []),
        )


class ServiceAccountSummary(K8sEntityBase):
    """ServiceAccount display model."""

    _entity_name: ClassVar[str] = "serviceaccount"

    secrets_count: int = Field(default=0, description="Number of associated secrets")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> ServiceAccountSummary:
        """Create from a kubernetes V1ServiceAccount object."""
        secrets = getattr(obj, "secrets", None) or []

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            secrets_count=len(secrets),
        )


class RoleSummary(K8sEntityBase):
    """Role/ClusterRole display model."""

    _entity_name: ClassVar[str] = "role"

    is_cluster_role: bool = Field(default=False, description="Whether this is a ClusterRole")
    rules_count: int = Field(default=0, description="Number of policy rules")
    rules: list[PolicyRule] = Field(default_factory=list, description="Policy rules")

    @classmethod
    def from_k8s_object(cls, obj: Any, *, is_cluster_role: bool = False) -> RoleSummary:
        """Create from a kubernetes V1Role or V1ClusterRole object."""
        rules_raw = getattr(obj, "rules", None) or []

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            is_cluster_role=is_cluster_role,
            rules_count=len(rules_raw),
            rules=[PolicyRule.from_k8s_object(r) for r in rules_raw],
        )


class RoleBindingSummary(K8sEntityBase):
    """RoleBinding/ClusterRoleBinding display model."""

    _entity_name: ClassVar[str] = "rolebinding"

    is_cluster_binding: bool = Field(
        default=False, description="Whether this is a ClusterRoleBinding"
    )
    role_ref_kind: str | None = Field(default=None, description="Role reference kind")
    role_ref_name: str | None = Field(default=None, description="Role reference name")
    subjects: list[Subject] = Field(default_factory=list, description="Binding subjects")

    @classmethod
    def from_k8s_object(cls, obj: Any, *, is_cluster_binding: bool = False) -> RoleBindingSummary:
        """Create from a kubernetes V1RoleBinding or V1ClusterRoleBinding object."""
        role_ref = getattr(obj, "role_ref", None)
        subjects_raw = getattr(obj, "subjects", None) or []

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            is_cluster_binding=is_cluster_binding,
            role_ref_kind=_safe_get(role_ref, "kind"),
            role_ref_name=_safe_get(role_ref, "name"),
            subjects=[Subject.from_k8s_object(s) for s in subjects_raw],
        )
