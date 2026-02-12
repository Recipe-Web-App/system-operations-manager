"""Kubernetes resource optimization display models.

Provides models for resource usage analysis, right-sizing recommendations,
orphan pod detection, and stale job identification.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
    _get_labels,
    _get_timestamp,
    _safe_get,
)

# =============================================================================
# Resource Metrics & Specs
# =============================================================================


class ResourceMetrics(BaseModel):
    """CPU and memory usage from metrics-server."""

    model_config = ConfigDict(extra="ignore")

    cpu_millicores: int = Field(default=0, description="CPU usage in millicores")
    memory_bytes: int = Field(default=0, description="Memory usage in bytes")

    @property
    def cpu_display(self) -> str:
        """Human-readable CPU usage."""
        if self.cpu_millicores >= 1000:
            return f"{self.cpu_millicores / 1000:.1f}"
        return f"{self.cpu_millicores}m"

    @property
    def memory_display(self) -> str:
        """Human-readable memory usage."""
        if self.memory_bytes >= 1024 * 1024 * 1024:
            return f"{self.memory_bytes / (1024 * 1024 * 1024):.1f}Gi"
        if self.memory_bytes >= 1024 * 1024:
            return f"{self.memory_bytes / (1024 * 1024):.0f}Mi"
        if self.memory_bytes >= 1024:
            return f"{self.memory_bytes / 1024:.0f}Ki"
        return f"{self.memory_bytes}B"


class ResourceSpec(BaseModel):
    """Requested and limit CPU/memory from a pod spec."""

    model_config = ConfigDict(extra="ignore")

    cpu_request_millicores: int = Field(default=0, description="CPU request in millicores")
    cpu_limit_millicores: int = Field(default=0, description="CPU limit in millicores")
    memory_request_bytes: int = Field(default=0, description="Memory request in bytes")
    memory_limit_bytes: int = Field(default=0, description="Memory limit in bytes")


# =============================================================================
# Analysis & Recommendations
# =============================================================================


class WorkloadResourceAnalysis(K8sEntityBase):
    """Per-workload resource usage vs request/limit analysis."""

    _entity_name: ClassVar[str] = "workload_analysis"

    workload_type: str = Field(description="Workload kind (Deployment, StatefulSet, DaemonSet)")
    replicas: int = Field(default=1, description="Number of replicas")
    total_usage: ResourceMetrics = Field(
        default_factory=ResourceMetrics,
        description="Aggregate resource usage across all pods",
    )
    total_spec: ResourceSpec = Field(
        default_factory=ResourceSpec,
        description="Aggregate resource requests/limits across all pods",
    )
    cpu_utilization_pct: float = Field(
        default=0.0, description="CPU usage as percentage of request"
    )
    memory_utilization_pct: float = Field(
        default=0.0, description="Memory usage as percentage of request"
    )
    status: str = Field(
        default="ok", description="Optimization status: ok, overprovisioned, underutilized"
    )

    @property
    def cpu_usage_display(self) -> str:
        """CPU usage / request display."""
        return f"{self.total_usage.cpu_display}/{self.total_spec.cpu_request_millicores}m"

    @property
    def memory_usage_display(self) -> str:
        """Memory usage / request display."""
        req_mi = self.total_spec.memory_request_bytes / (1024 * 1024)
        return f"{self.total_usage.memory_display}/{req_mi:.0f}Mi"


class RightsizingRecommendation(K8sEntityBase):
    """Right-sizing recommendation for a single workload."""

    _entity_name: ClassVar[str] = "recommendation"

    workload_type: str = Field(description="Workload kind")
    current_spec: ResourceSpec = Field(description="Current resource spec")
    current_usage: ResourceMetrics = Field(description="Current resource usage")
    recommended_cpu_request_millicores: int = Field(
        description="Recommended CPU request in millicores"
    )
    recommended_memory_request_bytes: int = Field(description="Recommended memory request in bytes")
    recommended_cpu_limit_millicores: int = Field(description="Recommended CPU limit in millicores")
    recommended_memory_limit_bytes: int = Field(description="Recommended memory limit in bytes")
    cpu_savings_millicores: int = Field(
        default=0, description="CPU savings in millicores (positive = saving)"
    )
    memory_savings_bytes: int = Field(
        default=0, description="Memory savings in bytes (positive = saving)"
    )


# =============================================================================
# Hygiene: Orphan Pods & Stale Jobs
# =============================================================================


class OrphanPod(K8sEntityBase):
    """A pod with no owner controller."""

    _entity_name: ClassVar[str] = "orphan_pod"

    phase: str = Field(default="Unknown", description="Pod phase")
    node_name: str | None = Field(default=None, description="Node running this pod")
    cpu_usage: str = Field(default="-", description="Current CPU usage")
    memory_usage: str = Field(default="-", description="Current memory usage")

    @classmethod
    def from_k8s_object(cls, obj: Any, metrics: ResourceMetrics | None = None) -> OrphanPod:
        """Create from a kubernetes V1Pod object."""
        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            phase=_safe_get(obj, "status", "phase", default="Unknown"),
            node_name=_safe_get(obj, "spec", "node_name"),
            cpu_usage=metrics.cpu_display if metrics else "-",
            memory_usage=metrics.memory_display if metrics else "-",
        )


class StaleJob(K8sEntityBase):
    """A completed or failed job that is still lingering."""

    _entity_name: ClassVar[str] = "stale_job"

    status: str = Field(default="Unknown", description="Job completion status")
    completion_time: str | None = Field(default=None, description="When the job completed")
    age_hours: float = Field(default=0.0, description="Hours since completion")

    @classmethod
    def from_k8s_object(cls, obj: Any, age_hours: float = 0.0) -> StaleJob:
        """Create from a kubernetes V1Job object."""
        conditions = _safe_get(obj, "status", "conditions") or []
        status = "Unknown"
        for cond in conditions:
            cond_type = getattr(cond, "type", None)
            cond_status = getattr(cond, "status", None)
            if cond_type == "Complete" and cond_status == "True":
                status = "Complete"
                break
            if cond_type == "Failed" and cond_status == "True":
                status = "Failed"
                break

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            status=status,
            completion_time=_get_timestamp(_safe_get(obj, "status", "completion_time")),
            age_hours=age_hours,
        )


# =============================================================================
# Summary
# =============================================================================


class OptimizationSummary(BaseModel):
    """High-level optimization opportunities rollup."""

    model_config = ConfigDict(extra="ignore")

    total_workloads_analyzed: int = Field(default=0, description="Total workloads analyzed")
    overprovisioned_count: int = Field(
        default=0, description="Workloads with significantly more resources than used"
    )
    underutilized_count: int = Field(
        default=0, description="Workloads using very little of their allocation"
    )
    ok_count: int = Field(default=0, description="Workloads with reasonable utilization")
    orphan_pod_count: int = Field(default=0, description="Pods with no owner controller")
    stale_job_count: int = Field(default=0, description="Completed/failed jobs still lingering")
    total_cpu_waste_millicores: int = Field(
        default=0, description="Total CPU over-provisioned across all workloads"
    )
    total_memory_waste_bytes: int = Field(
        default=0, description="Total memory over-provisioned across all workloads"
    )

    @property
    def cpu_waste_display(self) -> str:
        """Human-readable CPU waste."""
        if self.total_cpu_waste_millicores >= 1000:
            return f"{self.total_cpu_waste_millicores / 1000:.1f} cores"
        return f"{self.total_cpu_waste_millicores}m"

    @property
    def memory_waste_display(self) -> str:
        """Human-readable memory waste."""
        b = self.total_memory_waste_bytes
        if b >= 1024 * 1024 * 1024:
            return f"{b / (1024 * 1024 * 1024):.1f}Gi"
        if b >= 1024 * 1024:
            return f"{b / (1024 * 1024):.0f}Mi"
        return f"{b}B"
