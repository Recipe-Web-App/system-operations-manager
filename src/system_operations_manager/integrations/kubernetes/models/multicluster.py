"""Multi-cluster operation result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClusterStatus(BaseModel):
    """Status information for a single cluster."""

    model_config = ConfigDict(extra="forbid")

    cluster: str = Field(description="Cluster name from configuration")
    context: str = Field(description="Kubeconfig context name")
    connected: bool = Field(description="Whether the cluster is reachable")
    version: str | None = Field(default=None, description="Kubernetes version")
    node_count: int | None = Field(default=None, description="Number of nodes")
    namespace: str = Field(default="default", description="Default namespace")
    error: str | None = Field(default=None, description="Error message if connection failed")


class MultiClusterStatusResult(BaseModel):
    """Aggregated status result for multiple clusters."""

    model_config = ConfigDict(extra="forbid")

    clusters: list[ClusterStatus] = Field(default_factory=list, description="Per-cluster status")
    total: int = Field(default=0, description="Total number of clusters checked")
    connected: int = Field(default=0, description="Number of connected clusters")
    disconnected: int = Field(default=0, description="Number of disconnected clusters")


class ClusterDeployResult(BaseModel):
    """Deploy result for a single cluster."""

    model_config = ConfigDict(extra="forbid")

    cluster: str = Field(description="Cluster name")
    success: bool = Field(description="Whether all resources were applied successfully")
    resources_applied: int = Field(default=0, description="Number of resources applied")
    resources_failed: int = Field(default=0, description="Number of resources that failed")
    results: list[dict[str, Any]] = Field(
        default_factory=list, description="Per-resource apply results"
    )
    error: str | None = Field(default=None, description="Error message if deploy failed")


class MultiClusterDeployResult(BaseModel):
    """Aggregated deploy result for multiple clusters."""

    model_config = ConfigDict(extra="forbid")

    cluster_results: list[ClusterDeployResult] = Field(
        default_factory=list, description="Per-cluster deploy results"
    )
    total_clusters: int = Field(default=0, description="Total clusters targeted")
    successful: int = Field(default=0, description="Clusters where all resources succeeded")
    failed: int = Field(default=0, description="Clusters where one or more resources failed")


class ClusterSyncResult(BaseModel):
    """Sync result for a single target cluster."""

    model_config = ConfigDict(extra="forbid")

    cluster: str = Field(description="Target cluster name")
    success: bool = Field(description="Whether the sync was successful")
    action: str = Field(default="", description="Action taken (created, configured, skipped)")
    error: str | None = Field(default=None, description="Error message if sync failed")


class MultiClusterSyncResult(BaseModel):
    """Aggregated sync result for a resource across clusters."""

    model_config = ConfigDict(extra="forbid")

    source_cluster: str = Field(description="Source cluster name")
    resource_type: str = Field(description="Kubernetes resource kind")
    resource_name: str = Field(description="Resource name")
    namespace: str | None = Field(default=None, description="Resource namespace")
    cluster_results: list[ClusterSyncResult] = Field(
        default_factory=list, description="Per-target-cluster sync results"
    )
    total_targets: int = Field(default=0, description="Total target clusters")
    successful: int = Field(default=0, description="Successful syncs")
    failed: int = Field(default=0, description="Failed syncs")
