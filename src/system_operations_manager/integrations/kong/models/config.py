"""Pydantic models for Kong Declarative Configuration.

This module provides models for Kong's declarative configuration format,
supporting export/import of full gateway state including services, routes,
upstreams, consumers, and plugins.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kong.models.base import KongEntityBase


class DeclarativeConfig(BaseModel):
    """Full Kong declarative configuration.

    Represents the complete gateway state including all services, routes,
    upstreams, consumers, and plugins. Follows Kong's declarative configuration
    format (version 3.0).

    Attributes:
        _format_version: Kong declarative format version.
        _transform: Whether to transform config during import.
        services: List of service configurations.
        routes: List of route configurations.
        upstreams: List of upstream configurations with embedded targets.
        consumers: List of consumer configurations with optional credentials.
        plugins: List of plugin configurations.
        certificates: List of certificate configurations.
        ca_certificates: List of CA certificate configurations.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    format_version: str = Field(
        default="3.0",
        alias="_format_version",
        description="Kong declarative format version",
    )
    transform: bool | None = Field(
        default=None,
        alias="_transform",
        description="Whether to transform config during import",
    )

    # Core entities
    services: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Service configurations",
    )
    routes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Route configurations",
    )
    upstreams: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Upstream configurations with targets",
    )
    consumers: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Consumer configurations",
    )
    plugins: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Plugin configurations",
    )

    # Additional entities
    certificates: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Certificate configurations",
    )
    ca_certificates: list[dict[str, Any]] = Field(
        default_factory=list,
        description="CA certificate configurations",
    )


class ConfigDiff(BaseModel):
    """Represents a single difference between current and desired state.

    Used to track what changes need to be made when applying a declarative
    configuration.

    Attributes:
        entity_type: Type of entity (service, route, etc.).
        operation: Required operation (create, update, delete).
        id_or_name: Entity identifier (name or ID).
        current: Current state of the entity (None for creates).
        desired: Desired state of the entity (None for deletes).
        changes: Field-level changes as (old_value, new_value) tuples.
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(description="Entity type (service, route, etc.)")
    operation: Literal["create", "update", "delete"] = Field(description="Required operation")
    id_or_name: str = Field(description="Entity identifier")
    current: dict[str, Any] | None = Field(
        default=None,
        description="Current state",
    )
    desired: dict[str, Any] | None = Field(
        default=None,
        description="Desired state",
    )
    changes: dict[str, tuple[Any, Any]] | None = Field(
        default=None,
        description="Field changes as (old, new) tuples",
    )


class ConfigDiffSummary(BaseModel):
    """Summary of all differences between current and desired state.

    Provides aggregate counts and detailed diffs for configuration changes.

    Attributes:
        total_changes: Total number of changes required.
        creates: Count of entities to create by type.
        updates: Count of entities to update by type.
        deletes: Count of entities to delete by type.
        diffs: List of individual ConfigDiff objects.
    """

    model_config = ConfigDict(extra="forbid")

    total_changes: int = Field(default=0, description="Total changes required")
    creates: dict[str, int] = Field(
        default_factory=dict,
        description="Create counts by entity type",
    )
    updates: dict[str, int] = Field(
        default_factory=dict,
        description="Update counts by entity type",
    )
    deletes: dict[str, int] = Field(
        default_factory=dict,
        description="Delete counts by entity type",
    )
    diffs: list[ConfigDiff] = Field(
        default_factory=list,
        description="Individual diffs",
    )


class ConfigValidationError(BaseModel):
    """Validation error details for configuration files.

    Represents a single validation error with location and message.

    Attributes:
        path: JSON/YAML path to error location.
        message: Error description.
        entity_type: Type of entity with error (if applicable).
        entity_name: Name of entity with error (if applicable).
    """

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Path to error location")
    message: str = Field(description="Error message")
    entity_type: str | None = Field(
        default=None,
        description="Entity type with error",
    )
    entity_name: str | None = Field(
        default=None,
        description="Entity name with error",
    )


class ConfigValidationResult(BaseModel):
    """Result of configuration validation.

    Contains validation status and any errors or warnings found.

    Attributes:
        valid: Whether configuration is valid.
        errors: List of validation errors.
        warnings: List of validation warnings.
    """

    model_config = ConfigDict(extra="forbid")

    valid: bool = Field(description="Whether config is valid")
    errors: list[ConfigValidationError] = Field(
        default_factory=list,
        description="Validation errors",
    )
    warnings: list[ConfigValidationError] = Field(
        default_factory=list,
        description="Validation warnings",
    )


class ApplyOperation(BaseModel):
    """Result of a single apply operation.

    Records the outcome of applying a single entity change.

    Attributes:
        operation: Operation performed (create, update, delete).
        entity_type: Type of entity affected.
        id_or_name: Entity identifier.
        result: Operation result (success, failed).
        error: Error message if failed.
    """

    model_config = ConfigDict(extra="forbid")

    operation: Literal["create", "update", "delete"] = Field(description="Operation performed")
    entity_type: str = Field(description="Entity type")
    id_or_name: str = Field(description="Entity identifier")
    result: Literal["success", "failed"] = Field(description="Operation result")
    error: str | None = Field(default=None, description="Error if failed")


class PercentileMetrics(KongEntityBase):
    """Latency percentile metrics calculated from histogram data.

    Provides P50, P95, and P99 latency values computed from Prometheus
    histogram bucket data.

    Attributes:
        p50_ms: 50th percentile (median) latency in milliseconds.
        p95_ms: 95th percentile latency in milliseconds.
        p99_ms: 99th percentile latency in milliseconds.
        service: Service filter applied (if any).
        route: Route filter applied (if any).
    """

    model_config = ConfigDict(extra="allow")
    _entity_name: ClassVar[str] = "percentile_metrics"

    p50_ms: float | None = Field(
        default=None,
        description="50th percentile latency (ms)",
    )
    p95_ms: float | None = Field(
        default=None,
        description="95th percentile latency (ms)",
    )
    p99_ms: float | None = Field(
        default=None,
        description="99th percentile latency (ms)",
    )
    service: str | None = Field(
        default=None,
        description="Service filter applied",
    )
    route: str | None = Field(
        default=None,
        description="Route filter applied",
    )


class HealthFailure(KongEntityBase):
    """Health check failure details for an upstream target.

    Represents a target that has failed health checks with details
    about the failure type and current state.

    Attributes:
        target: Target address (host:port).
        failure_type: Type of failure (timeout, http_error, tcp_error, etc.).
        failure_count: Number of consecutive failures.
        last_failure_at: Timestamp of last failure.
        details: Additional failure details.
    """

    model_config = ConfigDict(extra="allow")
    _entity_name: ClassVar[str] = "health_failure"

    target: str = Field(description="Target address (host:port)")
    failure_type: str = Field(description="Type of failure")
    failure_count: int = Field(default=0, description="Consecutive failure count")
    last_failure_at: int | None = Field(
        default=None,
        description="Last failure timestamp",
    )
    details: str | None = Field(default=None, description="Failure details")
