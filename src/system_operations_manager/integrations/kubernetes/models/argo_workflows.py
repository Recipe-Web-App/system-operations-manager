"""Argo Workflows resource display models.

Argo Workflows CRDs are accessed via ``CustomObjectsApi`` which returns raw
``dict`` objects rather than typed SDK classes.  The ``from_k8s_object``
classmethods therefore use ``dict.get()`` instead of ``getattr()``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
)


class WorkflowSummary(K8sEntityBase):
    """Argo Workflow display model."""

    _entity_name: ClassVar[str] = "argo_workflow"

    phase: str = Field(
        default="Unknown", description="Workflow phase: Pending, Running, Succeeded, Failed, Error"
    )
    started_at: str | None = Field(default=None, description="Workflow start time")
    finished_at: str | None = Field(default=None, description="Workflow finish time")
    duration: str = Field(default="", description="Human-readable duration")
    message: str | None = Field(default=None, description="Status message")
    progress: str = Field(default="0/0", description="Completed/total nodes progress")
    entrypoint: str = Field(default="", description="Entrypoint template name")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> WorkflowSummary:
        """Create from an Argo Workflow CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        # Calculate duration
        started = status.get("startedAt")
        finished = status.get("finishedAt")
        duration = ""
        if started and finished:
            from datetime import datetime

            try:
                start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                delta = end_dt - start_dt
                total_seconds = int(delta.total_seconds())
                if total_seconds >= 3600:
                    duration = f"{total_seconds // 3600}h{(total_seconds % 3600) // 60}m"
                elif total_seconds >= 60:
                    duration = f"{total_seconds // 60}m{total_seconds % 60}s"
                else:
                    duration = f"{total_seconds}s"
            except ValueError, TypeError:
                duration = ""

        # Progress
        progress = status.get("progress", "0/0")

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            phase=status.get("phase", "Unknown"),
            started_at=started,
            finished_at=finished,
            duration=duration,
            message=status.get("message"),
            progress=progress,
            entrypoint=spec.get("entrypoint", ""),
        )


class WorkflowTemplateSummary(K8sEntityBase):
    """Argo WorkflowTemplate display model."""

    _entity_name: ClassVar[str] = "workflow_template"

    description: str = Field(default="", description="Template description")
    entrypoint: str = Field(default="", description="Entrypoint template name")
    templates_count: int = Field(default=0, description="Number of templates defined")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> WorkflowTemplateSummary:
        """Create from a WorkflowTemplate CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})

        templates: list[dict[str, Any]] = spec.get("templates", [])
        annotations: dict[str, str] = metadata.get("annotations") or {}
        description = annotations.get("workflows.argoproj.io/description", "")

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            description=description,
            entrypoint=spec.get("entrypoint", ""),
            templates_count=len(templates),
        )


class CronWorkflowSummary(K8sEntityBase):
    """Argo CronWorkflow display model."""

    _entity_name: ClassVar[str] = "cron_workflow"

    schedule: str = Field(default="", description="Cron schedule expression")
    timezone: str = Field(default="", description="Timezone for schedule")
    suspend: bool = Field(default=False, description="Whether the CronWorkflow is suspended")
    active_count: int = Field(default=0, description="Number of active workflow instances")
    last_scheduled: str | None = Field(default=None, description="Last scheduled time")
    concurrency_policy: str = Field(
        default="Allow", description="Concurrency policy: Allow, Forbid, Replace"
    )

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> CronWorkflowSummary:
        """Create from a CronWorkflow CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        active: list[dict[str, Any]] = status.get("active", [])

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            schedule=spec.get("schedule", ""),
            timezone=spec.get("timezone", ""),
            suspend=spec.get("suspend", False),
            active_count=len(active),
            last_scheduled=status.get("lastScheduledTime"),
            concurrency_policy=spec.get("concurrencyPolicy", "Allow"),
        )


class WorkflowArtifact(BaseModel):
    """Argo Workflow artifact reference."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(default="", description="Artifact name")
    node_id: str = Field(default="", description="Node that produced this artifact")
    path: str = Field(default="", description="Path within the container")
    artifact_type: str = Field(default="unknown", description="Storage type: s3, gcs, http, etc.")
    bucket: str = Field(default="", description="Storage bucket name")
    key: str = Field(default="", description="Storage object key")

    @classmethod
    def from_k8s_object(cls, artifact: dict[str, Any], node_id: str = "") -> WorkflowArtifact:
        """Create from an artifact dict in workflow status."""
        # Detect storage type
        artifact_type = "unknown"
        bucket = ""
        key = ""
        for storage in ("s3", "gcs", "oss", "hdfs", "http", "artifactory", "git"):
            if storage in artifact:
                artifact_type = storage
                storage_config = artifact[storage]
                if isinstance(storage_config, dict):
                    bucket = storage_config.get("bucket", "")
                    key = storage_config.get("key", "")
                break

        return cls(
            name=artifact.get("name", ""),
            node_id=node_id,
            path=artifact.get("path", ""),
            artifact_type=artifact_type,
            bucket=bucket,
            key=key,
        )
