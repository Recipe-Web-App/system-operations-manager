"""Flux CD resource display models.

Flux CRDs are accessed via ``CustomObjectsApi`` which returns raw
``dict`` objects rather than typed SDK classes.  The ``from_k8s_object``
classmethods therefore use ``dict.get()`` instead of ``getattr()``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
)


class FluxCondition(BaseModel):
    """Flux status condition from ``.status.conditions[]``."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(default="", description="Condition type (Ready, Reconciling, Stalled, etc.)")
    status: str = Field(default="Unknown", description="Condition status (True, False, Unknown)")
    reason: str = Field(default="", description="Machine-readable reason")
    message: str | None = Field(default=None, description="Human-readable message")
    last_transition_time: str | None = Field(default=None, description="Last transition timestamp")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> FluxCondition:
        """Create from a condition dict."""
        return cls(
            type=obj.get("type", ""),
            status=obj.get("status", "Unknown"),
            reason=obj.get("reason", ""),
            message=obj.get("message"),
            last_transition_time=obj.get("lastTransitionTime"),
        )


def _is_ready(conditions: list[FluxCondition]) -> bool:
    """Determine readiness from a list of Flux conditions."""
    for c in conditions:
        if c.type == "Ready":
            return c.status == "True"
    return False


def _is_reconciling(conditions: list[FluxCondition]) -> bool:
    """Determine if reconciliation is in progress."""
    for c in conditions:
        if c.type == "Reconciling":
            return c.status == "True"
    return False


def _parse_conditions(status: dict[str, Any]) -> list[FluxCondition]:
    """Parse ``.status.conditions`` into a list of FluxCondition."""
    raw: list[dict[str, Any]] = status.get("conditions", [])
    return [FluxCondition.from_k8s_object(c) for c in raw]


# =============================================================================
# GitRepository
# =============================================================================


class GitRepositorySummary(K8sEntityBase):
    """Flux GitRepository display model."""

    _entity_name: ClassVar[str] = "flux_git_repository"

    url: str = Field(default="", description="Git repository URL")
    ref_branch: str | None = Field(default=None, description="Branch reference")
    ref_tag: str | None = Field(default=None, description="Tag reference")
    ref_semver: str | None = Field(default=None, description="Semver range reference")
    ref_commit: str | None = Field(default=None, description="Commit SHA reference")
    interval: str = Field(default="", description="Reconciliation interval")
    secret_ref_name: str | None = Field(default=None, description="Secret reference name")
    suspended: bool = Field(default=False, description="Whether reconciliation is suspended")
    ready: bool = Field(default=False, description="Whether the resource is ready")
    reconciling: bool = Field(default=False, description="Whether reconciliation is in progress")
    artifact_revision: str | None = Field(default=None, description="Latest artifact revision")
    conditions: list[FluxCondition] = Field(default_factory=list, description="Status conditions")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> GitRepositorySummary:
        """Create from a Flux GitRepository CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        ref: dict[str, Any] = spec.get("ref", {})
        secret_ref: dict[str, Any] = spec.get("secretRef", {})
        artifact: dict[str, Any] = status.get("artifact", {})
        conditions = _parse_conditions(status)

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            url=spec.get("url", ""),
            ref_branch=ref.get("branch"),
            ref_tag=ref.get("tag"),
            ref_semver=ref.get("semver"),
            ref_commit=ref.get("commit"),
            interval=spec.get("interval", ""),
            secret_ref_name=secret_ref.get("name") if secret_ref else None,
            suspended=spec.get("suspend", False),
            ready=_is_ready(conditions),
            reconciling=_is_reconciling(conditions),
            artifact_revision=artifact.get("revision"),
            conditions=conditions,
        )


# =============================================================================
# HelmRepository
# =============================================================================


class HelmRepositorySummary(K8sEntityBase):
    """Flux HelmRepository display model."""

    _entity_name: ClassVar[str] = "flux_helm_repository"

    url: str = Field(default="", description="Helm repository URL")
    repo_type: str = Field(default="default", description="Repository type (default or oci)")
    interval: str = Field(default="", description="Reconciliation interval")
    secret_ref_name: str | None = Field(default=None, description="Secret reference name")
    suspended: bool = Field(default=False, description="Whether reconciliation is suspended")
    ready: bool = Field(default=False, description="Whether the resource is ready")
    reconciling: bool = Field(default=False, description="Whether reconciliation is in progress")
    artifact_revision: str | None = Field(default=None, description="Latest artifact revision")
    conditions: list[FluxCondition] = Field(default_factory=list, description="Status conditions")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> HelmRepositorySummary:
        """Create from a Flux HelmRepository CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        secret_ref: dict[str, Any] = spec.get("secretRef", {})
        artifact: dict[str, Any] = status.get("artifact", {})
        conditions = _parse_conditions(status)

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            url=spec.get("url", ""),
            repo_type=spec.get("type", "default"),
            interval=spec.get("interval", ""),
            secret_ref_name=secret_ref.get("name") if secret_ref else None,
            suspended=spec.get("suspend", False),
            ready=_is_ready(conditions),
            reconciling=_is_reconciling(conditions),
            artifact_revision=artifact.get("revision"),
            conditions=conditions,
        )


# =============================================================================
# Kustomization
# =============================================================================


class KustomizationSummary(K8sEntityBase):
    """Flux Kustomization display model."""

    _entity_name: ClassVar[str] = "flux_kustomization"

    source_kind: str = Field(default="", description="Source reference kind")
    source_name: str = Field(default="", description="Source reference name")
    source_namespace: str | None = Field(default=None, description="Source reference namespace")
    path: str = Field(default="./", description="Path within the source")
    interval: str = Field(default="", description="Reconciliation interval")
    prune: bool = Field(default=False, description="Whether to prune resources not in source")
    target_namespace: str | None = Field(default=None, description="Target namespace override")
    suspended: bool = Field(default=False, description="Whether reconciliation is suspended")
    ready: bool = Field(default=False, description="Whether the resource is ready")
    reconciling: bool = Field(default=False, description="Whether reconciliation is in progress")
    last_applied_revision: str | None = Field(
        default=None, description="Last successfully applied revision"
    )
    last_attempted_revision: str | None = Field(default=None, description="Last attempted revision")
    conditions: list[FluxCondition] = Field(default_factory=list, description="Status conditions")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> KustomizationSummary:
        """Create from a Flux Kustomization CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        source_ref: dict[str, Any] = spec.get("sourceRef", {})
        conditions = _parse_conditions(status)

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            source_kind=source_ref.get("kind", ""),
            source_name=source_ref.get("name", ""),
            source_namespace=source_ref.get("namespace"),
            path=spec.get("path", "./"),
            interval=spec.get("interval", ""),
            prune=spec.get("prune", False),
            target_namespace=spec.get("targetNamespace"),
            suspended=spec.get("suspend", False),
            ready=_is_ready(conditions),
            reconciling=_is_reconciling(conditions),
            last_applied_revision=status.get("lastAppliedRevision"),
            last_attempted_revision=status.get("lastAttemptedRevision"),
            conditions=conditions,
        )


# =============================================================================
# HelmRelease
# =============================================================================


class HelmReleaseSummary(K8sEntityBase):
    """Flux HelmRelease display model."""

    _entity_name: ClassVar[str] = "flux_helm_release"

    chart_name: str = Field(default="", description="Helm chart name")
    chart_source_kind: str = Field(default="", description="Chart source reference kind")
    chart_source_name: str = Field(default="", description="Chart source reference name")
    chart_source_namespace: str | None = Field(
        default=None, description="Chart source reference namespace"
    )
    interval: str = Field(default="", description="Reconciliation interval")
    target_namespace: str | None = Field(default=None, description="Target namespace override")
    release_name: str | None = Field(default=None, description="Helm release name override")
    suspended: bool = Field(default=False, description="Whether reconciliation is suspended")
    ready: bool = Field(default=False, description="Whether the resource is ready")
    reconciling: bool = Field(default=False, description="Whether reconciliation is in progress")
    conditions: list[FluxCondition] = Field(default_factory=list, description="Status conditions")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> HelmReleaseSummary:
        """Create from a Flux HelmRelease CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        chart_spec: dict[str, Any] = spec.get("chart", {}).get("spec", {})
        source_ref: dict[str, Any] = chart_spec.get("sourceRef", {})
        conditions = _parse_conditions(status)

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            chart_name=chart_spec.get("chart", ""),
            chart_source_kind=source_ref.get("kind", ""),
            chart_source_name=source_ref.get("name", ""),
            chart_source_namespace=source_ref.get("namespace"),
            interval=spec.get("interval", ""),
            target_namespace=spec.get("targetNamespace"),
            release_name=spec.get("releaseName"),
            suspended=spec.get("suspend", False),
            ready=_is_ready(conditions),
            reconciling=_is_reconciling(conditions),
            conditions=conditions,
        )
