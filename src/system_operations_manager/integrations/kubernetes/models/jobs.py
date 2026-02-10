"""Kubernetes job resource display models."""

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


class JobSummary(K8sEntityBase):
    """Job display model."""

    _entity_name: ClassVar[str] = "job"

    completions: int | None = Field(default=None, description="Desired completions")
    succeeded: int = Field(default=0, description="Succeeded pod count")
    failed: int = Field(default=0, description="Failed pod count")
    active: int = Field(default=0, description="Active pod count")
    start_time: str | None = Field(default=None, description="Job start time")
    completion_time: str | None = Field(default=None, description="Job completion time")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> JobSummary:
        """Create from a kubernetes V1Job object."""
        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            completions=_safe_get(obj, "spec", "completions"),
            succeeded=_safe_get(obj, "status", "succeeded", default=0) or 0,
            failed=_safe_get(obj, "status", "failed", default=0) or 0,
            active=_safe_get(obj, "status", "active", default=0) or 0,
            start_time=_get_timestamp(_safe_get(obj, "status", "start_time")),
            completion_time=_get_timestamp(_safe_get(obj, "status", "completion_time")),
        )


class CronJobSummary(K8sEntityBase):
    """CronJob display model."""

    _entity_name: ClassVar[str] = "cronjob"

    schedule: str = Field(default="", description="Cron schedule expression")
    suspend: bool = Field(default=False, description="Whether the CronJob is suspended")
    active_count: int = Field(default=0, description="Number of active jobs")
    last_schedule_time: str | None = Field(default=None, description="Last schedule time")
    last_successful_time: str | None = Field(default=None, description="Last successful time")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> CronJobSummary:
        """Create from a kubernetes V1CronJob object."""
        active_jobs = _safe_get(obj, "status", "active") or []

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            schedule=_safe_get(obj, "spec", "schedule", default=""),
            suspend=_safe_get(obj, "spec", "suspend", default=False) or False,
            active_count=len(active_jobs),
            last_schedule_time=_get_timestamp(_safe_get(obj, "status", "last_schedule_time")),
            last_successful_time=_get_timestamp(_safe_get(obj, "status", "last_successful_time")),
        )
