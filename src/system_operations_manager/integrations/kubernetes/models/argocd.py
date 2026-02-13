"""ArgoCD resource display models.

ArgoCD CRDs are accessed via ``CustomObjectsApi`` which returns raw
``dict`` objects rather than typed SDK classes.  The ``from_k8s_object``
classmethods therefore use ``dict.get()`` instead of ``getattr()``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
)


class ApplicationDestination(BaseModel):
    """ArgoCD Application destination."""

    model_config = ConfigDict(extra="ignore")

    server: str = Field(default="", description="Destination cluster API server URL")
    namespace: str = Field(default="", description="Destination namespace")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> ApplicationDestination:
        """Create from destination dict."""
        return cls(
            server=obj.get("server", ""),
            namespace=obj.get("namespace", ""),
        )


class ApplicationSummary(K8sEntityBase):
    """ArgoCD Application display model."""

    _entity_name: ClassVar[str] = "argocd_application"

    project: str = Field(default="default", description="ArgoCD project name")
    repo_url: str = Field(default="", description="Source Git repository URL")
    path: str = Field(default="", description="Path within the repository")
    target_revision: str = Field(default="HEAD", description="Target revision (branch/tag/commit)")
    dest_server: str = Field(default="", description="Destination cluster server URL")
    dest_namespace: str = Field(default="", description="Destination namespace")
    sync_status: str = Field(
        default="Unknown", description="Sync status: Synced, OutOfSync, Unknown"
    )
    health_status: str = Field(
        default="Unknown", description="Health status: Healthy, Degraded, Progressing, etc."
    )
    message: str | None = Field(default=None, description="Status message")
    auto_sync: bool = Field(default=False, description="Whether auto-sync is enabled")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> ApplicationSummary:
        """Create from an ArgoCD Application CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        # Source
        source: dict[str, Any] = spec.get("source", {})
        repo_url = source.get("repoURL", "")
        path = source.get("path", "")
        target_revision = source.get("targetRevision", "HEAD")

        # Destination
        destination: dict[str, Any] = spec.get("destination", {})
        dest_server = destination.get("server", "")
        dest_namespace = destination.get("namespace", "")

        # Sync status
        sync_status_dict: dict[str, Any] = status.get("sync", {})
        sync_status = sync_status_dict.get("status", "Unknown")

        # Health status
        health_dict: dict[str, Any] = status.get("health", {})
        health_status = health_dict.get("status", "Unknown")
        message = health_dict.get("message")

        # Auto-sync
        sync_policy: dict[str, Any] = spec.get("syncPolicy", {})
        auto_sync = "automated" in sync_policy

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            project=spec.get("project", "default"),
            repo_url=repo_url,
            path=path,
            target_revision=target_revision,
            dest_server=dest_server,
            dest_namespace=dest_namespace,
            sync_status=sync_status,
            health_status=health_status,
            message=message,
            auto_sync=auto_sync,
        )


class AppProjectSummary(K8sEntityBase):
    """ArgoCD AppProject display model."""

    _entity_name: ClassVar[str] = "argocd_project"

    description: str = Field(default="", description="Project description")
    source_repos: list[str] = Field(default_factory=list, description="Allowed source repositories")
    destinations: list[ApplicationDestination] = Field(
        default_factory=list, description="Allowed destinations"
    )
    cluster_resource_whitelist_count: int = Field(
        default=0, description="Number of whitelisted cluster resources"
    )

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> AppProjectSummary:
        """Create from an ArgoCD AppProject CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})

        # Destinations
        destinations_raw: list[dict[str, Any]] = spec.get("destinations", [])
        destinations = [ApplicationDestination.from_k8s_object(d) for d in destinations_raw]

        # Cluster resource whitelist
        whitelist: list[dict[str, Any]] = spec.get("clusterResourceWhitelist", [])

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            description=spec.get("description", ""),
            source_repos=spec.get("sourceRepos", []),
            destinations=destinations,
            cluster_resource_whitelist_count=len(whitelist),
        )
