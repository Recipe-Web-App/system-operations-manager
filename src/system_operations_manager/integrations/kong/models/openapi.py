"""Pydantic models for OpenAPI to Kong route synchronization.

This module provides models for parsing OpenAPI specifications and
mapping them to Kong route configurations.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OpenAPIOperation(BaseModel):
    """Represents a parsed OpenAPI operation (endpoint).

    Attributes:
        path: The OpenAPI path (e.g., "/users/{userId}/profile").
        method: HTTP method (GET, POST, PUT, DELETE, etc.).
        operation_id: Unique operation identifier from spec.
        tags: Tags associated with the operation.
        summary: Brief description of the operation.
        deprecated: Whether the operation is deprecated.
    """

    model_config = ConfigDict(extra="ignore")

    path: str = Field(description="OpenAPI path pattern")
    method: str = Field(description="HTTP method (uppercase)")
    operation_id: str | None = Field(default=None, description="Operation identifier")
    tags: list[str] = Field(default_factory=list, description="Operation tags")
    summary: str | None = Field(default=None, description="Operation summary")
    deprecated: bool = Field(default=False, description="Whether operation is deprecated")


class OpenAPISpec(BaseModel):
    """Parsed OpenAPI specification.

    Attributes:
        title: API title from info section.
        version: API version from info section.
        base_path: Base path extracted from servers section.
        operations: List of parsed operations.
        all_tags: All unique tags found in the specification.
    """

    model_config = ConfigDict(extra="ignore")

    title: str = Field(description="API title")
    version: str = Field(description="API version")
    base_path: str | None = Field(default=None, description="Base path from servers")
    operations: list[OpenAPIOperation] = Field(
        default_factory=list, description="Parsed operations"
    )
    all_tags: list[str] = Field(default_factory=list, description="All unique tags")


class RouteMapping(BaseModel):
    """Maps an OpenAPI path to a Kong route.

    Attributes:
        route_name: Generated Kong route name.
        path: The OpenAPI path pattern.
        methods: HTTP methods for this route.
        tags: Tags to apply to the Kong route.
        operation_ids: Source operation IDs from OpenAPI.
        strip_path: Whether to strip the matched path.
    """

    model_config = ConfigDict(extra="ignore")

    route_name: str = Field(description="Kong route name")
    path: str = Field(description="Path pattern")
    methods: list[str] = Field(description="HTTP methods")
    tags: list[str] = Field(default_factory=list, description="Route tags")
    operation_ids: list[str] = Field(default_factory=list, description="Source operation IDs")
    strip_path: bool = Field(default=True, description="Strip path when proxying")


SyncOperation = Literal["create", "update", "delete"]


class SyncChange(BaseModel):
    """A single change in the sync operation.

    Attributes:
        operation: Type of change (create, update, delete).
        route_name: Name of the affected route.
        path: Path pattern for the route.
        methods: HTTP methods for the route.
        tags: Tags for the route.
        is_breaking: Whether this is a breaking change.
        breaking_reason: Explanation of why this is breaking.
        field_changes: For updates, the changed fields.
    """

    model_config = ConfigDict(extra="ignore")

    operation: SyncOperation = Field(description="Type of sync operation")
    route_name: str = Field(description="Route name")
    path: str = Field(description="Route path")
    methods: list[str] = Field(default_factory=list, description="HTTP methods")
    tags: list[str] = Field(default_factory=list, description="Route tags")
    is_breaking: bool = Field(default=False, description="Is this a breaking change")
    breaking_reason: str | None = Field(default=None, description="Why this is breaking")
    field_changes: dict[str, tuple[Any, Any]] | None = Field(
        default=None, description="Field changes (old, new) for updates"
    )


class SyncResult(BaseModel):
    """Result of calculating sync changes.

    Attributes:
        creates: Routes to create.
        updates: Routes to update.
        deletes: Routes to delete.
        service_name: Target Kong service name.
    """

    model_config = ConfigDict(extra="ignore")

    creates: list[SyncChange] = Field(default_factory=list, description="Routes to create")
    updates: list[SyncChange] = Field(default_factory=list, description="Routes to update")
    deletes: list[SyncChange] = Field(default_factory=list, description="Routes to delete")
    service_name: str = Field(description="Target service name")

    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return len(self.creates) + len(self.updates) + len(self.deletes)

    @property
    def has_changes(self) -> bool:
        """Whether there are any changes."""
        return self.total_changes > 0

    @property
    def breaking_changes(self) -> list[SyncChange]:
        """All breaking changes across all operations."""
        breaking = []
        for change in self.creates + self.updates + self.deletes:
            if change.is_breaking:
                breaking.append(change)
        return breaking

    @property
    def has_breaking_changes(self) -> bool:
        """Whether there are any breaking changes."""
        return len(self.breaking_changes) > 0


class SyncOperationResult(BaseModel):
    """Result of applying a single sync operation.

    Attributes:
        operation: Type of operation performed.
        route_name: Name of the affected route.
        result: Whether the operation succeeded.
        error: Error message if operation failed.
    """

    model_config = ConfigDict(extra="ignore")

    operation: SyncOperation = Field(description="Operation type")
    route_name: str = Field(description="Route name")
    result: Literal["success", "failed", "skipped"] = Field(description="Operation result")
    error: str | None = Field(default=None, description="Error message if failed")


class SyncApplyResult(BaseModel):
    """Result of applying all sync operations.

    Attributes:
        operations: Results of individual operations.
        service_name: Target Kong service name.
    """

    model_config = ConfigDict(extra="ignore")

    operations: list[SyncOperationResult] = Field(
        default_factory=list, description="Operation results"
    )
    service_name: str = Field(description="Target service name")

    @property
    def succeeded(self) -> list[SyncOperationResult]:
        """Operations that succeeded."""
        return [op for op in self.operations if op.result == "success"]

    @property
    def failed(self) -> list[SyncOperationResult]:
        """Operations that failed."""
        return [op for op in self.operations if op.result == "failed"]

    @property
    def skipped(self) -> list[SyncOperationResult]:
        """Operations that were skipped."""
        return [op for op in self.operations if op.result == "skipped"]

    @property
    def all_succeeded(self) -> bool:
        """Whether all operations succeeded."""
        return len(self.failed) == 0
