"""Argo Rollouts resource display models.

Argo Rollouts CRDs are accessed via ``CustomObjectsApi`` which returns raw
``dict`` objects rather than typed SDK classes.  The ``from_k8s_object``
classmethods therefore use ``dict.get()`` instead of ``getattr()``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
)


class RolloutSummary(K8sEntityBase):
    """Argo Rollouts Rollout display model."""

    _entity_name: ClassVar[str] = "argo_rollout"

    strategy: str = Field(default="unknown", description="Deployment strategy: canary or blueGreen")
    replicas: int = Field(default=0, description="Desired number of replicas")
    ready_replicas: int = Field(default=0, description="Number of ready replicas")
    available_replicas: int = Field(default=0, description="Number of available replicas")
    phase: str = Field(
        default="Unknown", description="Rollout phase: Healthy, Progressing, Degraded, Paused, etc."
    )
    message: str | None = Field(default=None, description="Status message")
    current_step_index: int | None = Field(
        default=None, description="Current step index for canary"
    )
    canary_weight: int = Field(default=0, description="Current canary traffic weight percentage")
    stable_rs: str = Field(default="", description="Stable ReplicaSet hash")
    canary_rs: str = Field(default="", description="Canary ReplicaSet hash")
    image: str = Field(default="", description="Container image")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> RolloutSummary:
        """Create from an Argo Rollouts Rollout CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        # Determine strategy
        strategy = "unknown"
        if "canary" in spec.get("strategy", {}):
            strategy = "canary"
        elif "blueGreen" in spec.get("strategy", {}):
            strategy = "blueGreen"

        # Extract image from first container in template
        image = ""
        template: dict[str, Any] = spec.get("template", {})
        containers: list[dict[str, Any]] = template.get("spec", {}).get("containers", [])
        if containers:
            image = containers[0].get("image", "")

        # Canary status
        canary_status: dict[str, Any] = status.get("canary", {})

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            strategy=strategy,
            replicas=spec.get("replicas", 0),
            ready_replicas=status.get("readyReplicas", 0),
            available_replicas=status.get("availableReplicas", 0),
            phase=status.get("phase", "Unknown"),
            message=status.get("message"),
            current_step_index=status.get("currentStepIndex"),
            canary_weight=canary_status.get("weight", 0),
            stable_rs=status.get("stableRS", ""),
            canary_rs=status.get("currentPodHash", ""),
            image=image,
        )


class AnalysisTemplateSummary(K8sEntityBase):
    """Argo Rollouts AnalysisTemplate display model."""

    _entity_name: ClassVar[str] = "analysis_template"

    metrics_count: int = Field(default=0, description="Number of metrics defined")
    args: list[str] = Field(default_factory=list, description="Template argument names")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> AnalysisTemplateSummary:
        """Create from an AnalysisTemplate CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})

        metrics: list[dict[str, Any]] = spec.get("metrics", [])
        args_raw: list[dict[str, Any]] = spec.get("args", [])
        arg_names = [a.get("name", "") for a in args_raw]

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            metrics_count=len(metrics),
            args=arg_names,
        )


class AnalysisRunSummary(K8sEntityBase):
    """Argo Rollouts AnalysisRun display model."""

    _entity_name: ClassVar[str] = "analysis_run"

    phase: str = Field(
        default="Unknown",
        description="Analysis run phase: Pending, Running, Successful, Failed, Error, Inconclusive",
    )
    message: str | None = Field(default=None, description="Status message")
    metrics_count: int = Field(default=0, description="Number of metric results")
    rollout_ref: str = Field(default="", description="Associated rollout name")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> AnalysisRunSummary:
        """Create from an AnalysisRun CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        status: dict[str, Any] = obj.get("status", {})

        # Get rollout reference from owner references
        rollout_ref = ""
        owner_refs: list[dict[str, Any]] = metadata.get("ownerReferences", [])
        for ref in owner_refs:
            if ref.get("kind") == "Rollout":
                rollout_ref = ref.get("name", "")
                break

        metric_results: list[dict[str, Any]] = status.get("metricResults", [])

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            phase=status.get("phase", "Unknown"),
            message=status.get("message"),
            metrics_count=len(metric_results),
            rollout_ref=rollout_ref,
        )
