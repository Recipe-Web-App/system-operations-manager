"""Kyverno policy resource display models.

Kyverno CRDs are accessed via ``CustomObjectsApi`` which returns raw ``dict``
objects rather than typed SDK classes.  The ``from_k8s_object`` classmethods
therefore use ``dict.get()`` instead of ``getattr()``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
)


class KyvernoRuleSummary(BaseModel):
    """Summary of a single Kyverno policy rule."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(default="", description="Rule name")
    rule_type: str = Field(
        default="unknown",
        description="Rule type: validate, mutate, generate, verifyImages",
    )
    has_match: bool = Field(default=False, description="Whether rule has match conditions")
    has_exclude: bool = Field(default=False, description="Whether rule has exclude conditions")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> KyvernoRuleSummary:
        """Create from a Kyverno rule dict."""
        rule_type = "unknown"
        for rt in ("validate", "mutate", "generate", "verifyImages"):
            if rt in obj:
                rule_type = rt
                break

        return cls(
            name=obj.get("name", ""),
            rule_type=rule_type,
            has_match="match" in obj,
            has_exclude="exclude" in obj,
        )


class KyvernoPolicySummary(K8sEntityBase):
    """Kyverno ClusterPolicy/Policy display model."""

    _entity_name: ClassVar[str] = "kyverno_policy"

    is_cluster_policy: bool = Field(default=False, description="Whether this is a ClusterPolicy")
    background: bool = Field(default=True, description="Background scanning enabled")
    validation_failure_action: str = Field(
        default="Audit",
        description="Validation failure action",
    )
    rules_count: int = Field(default=0, description="Number of rules")
    rules: list[KyvernoRuleSummary] = Field(default_factory=list, description="Policy rules")
    ready: bool = Field(default=False, description="Whether policy is ready")
    message: str | None = Field(default=None, description="Status message")

    @classmethod
    def from_k8s_object(
        cls,
        obj: dict[str, Any],
        *,
        is_cluster_policy: bool = False,
    ) -> KyvernoPolicySummary:
        """Create from a Kyverno CRD dict response."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})
        rules_raw: list[dict[str, Any]] = spec.get("rules", [])

        ready = False
        message = None
        for condition in status.get("conditions", []):
            if condition.get("type") == "Ready":
                ready = condition.get("status") == "True"
                message = condition.get("message")
                break

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            is_cluster_policy=is_cluster_policy,
            background=spec.get("background", True),
            validation_failure_action=spec.get("validationFailureAction", "Audit"),
            rules_count=len(rules_raw),
            rules=[KyvernoRuleSummary.from_k8s_object(r) for r in rules_raw],
            ready=ready,
            message=message,
        )


class PolicyReportResult(BaseModel):
    """Individual result from a Kyverno policy report."""

    model_config = ConfigDict(extra="ignore")

    policy: str = Field(default="", description="Policy name")
    rule: str = Field(default="", description="Rule name")
    result: str = Field(default="", description="Result: pass, fail, warn, error, skip")
    message: str = Field(default="", description="Result message")
    resource_kind: str = Field(default="", description="Target resource kind")
    resource_name: str = Field(default="", description="Target resource name")
    resource_namespace: str | None = Field(default=None, description="Target resource namespace")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> PolicyReportResult:
        """Create from a policy report result dict."""
        resources: list[dict[str, Any]] = obj.get("resources", [])
        resource: dict[str, Any] = resources[0] if resources else {}

        return cls(
            policy=obj.get("policy", ""),
            rule=obj.get("rule", ""),
            result=obj.get("result", ""),
            message=obj.get("message", ""),
            resource_kind=resource.get("kind", ""),
            resource_name=resource.get("name", ""),
            resource_namespace=resource.get("namespace"),
        )


class PolicyReportSummary(K8sEntityBase):
    """Kyverno PolicyReport/ClusterPolicyReport display model."""

    _entity_name: ClassVar[str] = "policy_report"

    is_cluster_report: bool = Field(
        default=False,
        description="Whether this is a ClusterPolicyReport",
    )
    pass_count: int = Field(default=0, description="Number of passing results")
    fail_count: int = Field(default=0, description="Number of failing results")
    warn_count: int = Field(default=0, description="Number of warning results")
    error_count: int = Field(default=0, description="Number of error results")
    skip_count: int = Field(default=0, description="Number of skipped results")
    results: list[PolicyReportResult] = Field(
        default_factory=list,
        description="Report results",
    )

    @classmethod
    def from_k8s_object(
        cls,
        obj: dict[str, Any],
        *,
        is_cluster_report: bool = False,
    ) -> PolicyReportSummary:
        """Create from a Kyverno policy report CRD dict response."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        summary: dict[str, Any] = obj.get("summary", {})
        results_raw: list[dict[str, Any]] = obj.get("results", [])

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            is_cluster_report=is_cluster_report,
            pass_count=summary.get("pass", 0),
            fail_count=summary.get("fail", 0),
            warn_count=summary.get("warn", 0),
            error_count=summary.get("error", 0),
            skip_count=summary.get("skip", 0),
            results=[PolicyReportResult.from_k8s_object(r) for r in results_raw],
        )
