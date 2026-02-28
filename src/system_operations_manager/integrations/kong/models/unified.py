"""Unified entity models for multi-source Kong entity management.

This module provides models for representing Kong entities that may exist
in multiple sources (Gateway data plane and Konnect control plane), with
support for drift detection between sources.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from system_operations_manager.integrations.kong.models.base import KongEntityBase


class EntitySource(StrEnum):
    """Source of a Kong entity."""

    GATEWAY = "gateway"
    KONNECT = "konnect"
    BOTH = "both"


class UnifiedEntity[T: KongEntityBase](BaseModel):
    """Wrapper for entities from multiple sources with drift detection.

    This model wraps a Kong entity and tracks its source (Gateway, Konnect,
    or both). When an entity exists in both sources, drift detection can
    identify fields that differ between the two versions.

    Attributes:
        entity: The Kong entity (Service, Route, Consumer, etc.).
        source: Where the entity exists (gateway, konnect, or both).
        gateway_id: Entity ID in Gateway (if present).
        konnect_id: Entity ID in Konnect (if present).
        has_drift: True if entity exists in both sources with differences.
        drift_fields: List of field names that differ between sources.
        gateway_entity: Original entity from Gateway (for drift comparison).
        konnect_entity: Original entity from Konnect (for drift comparison).
    """

    entity: T = Field(description="The Kong entity")
    source: EntitySource = Field(description="Entity source")
    gateway_id: str | None = Field(default=None, description="ID in Gateway")
    konnect_id: str | None = Field(default=None, description="ID in Konnect")

    # Drift detection
    has_drift: bool = Field(default=False, description="Has configuration drift")
    drift_fields: list[str] | None = Field(
        default=None, description="Fields that differ between sources"
    )

    # Store original entities for detailed comparison
    gateway_entity: T | None = Field(default=None, description="Original entity from Gateway")
    konnect_entity: T | None = Field(default=None, description="Original entity from Konnect")

    model_config = {"arbitrary_types_allowed": True}

    @property
    def name(self) -> str | None:
        """Get the entity name if available."""
        return getattr(self.entity, "name", None)

    @property
    def identifier(self) -> str:
        """Get a human-readable identifier for the entity."""
        name = self.name
        if name:
            return name
        return self.gateway_id or self.konnect_id or "unknown"


class UnifiedEntityList[T: KongEntityBase](BaseModel):
    """Collection of unified entities with summary statistics.

    Provides filtering and grouping methods for working with entities
    from multiple sources.

    Attributes:
        entities: List of unified entities.
    """

    entities: list[UnifiedEntity[T]] = Field(
        default_factory=list, description="List of unified entities"
    )

    model_config = {"arbitrary_types_allowed": True}

    def __len__(self) -> int:
        """Return the number of entities."""
        return len(self.entities)

    @property
    def gateway_only(self) -> list[UnifiedEntity[T]]:
        """Get entities that exist only in Gateway."""
        return [e for e in self.entities if e.source == EntitySource.GATEWAY]

    @property
    def konnect_only(self) -> list[UnifiedEntity[T]]:
        """Get entities that exist only in Konnect."""
        return [e for e in self.entities if e.source == EntitySource.KONNECT]

    @property
    def in_both(self) -> list[UnifiedEntity[T]]:
        """Get entities that exist in both sources."""
        return [e for e in self.entities if e.source == EntitySource.BOTH]

    @property
    def with_drift(self) -> list[UnifiedEntity[T]]:
        """Get entities with configuration drift between sources."""
        return [e for e in self.entities if e.has_drift]

    @property
    def synced(self) -> list[UnifiedEntity[T]]:
        """Get entities in both sources without drift."""
        return [e for e in self.entities if e.source == EntitySource.BOTH and not e.has_drift]

    @property
    def gateway_only_count(self) -> int:
        """Count of entities only in Gateway."""
        return len(self.gateway_only)

    @property
    def konnect_only_count(self) -> int:
        """Count of entities only in Konnect."""
        return len(self.konnect_only)

    @property
    def in_both_count(self) -> int:
        """Count of entities in both sources."""
        return len(self.in_both)

    @property
    def drift_count(self) -> int:
        """Count of entities with drift."""
        return len(self.with_drift)

    @property
    def synced_count(self) -> int:
        """Count of fully synced entities."""
        return len(self.synced)

    def filter_by_source(self, source: EntitySource | str) -> UnifiedEntityList[T]:
        """Filter entities by source.

        When filtering by ``gateway`` or ``konnect``, entities that exist in
        **both** sources are included (since they are present in the requested
        source).  Filtering by ``both`` returns only entities that exist in
        both sources simultaneously.

        Args:
            source: Source to filter by (gateway, konnect, or both).

        Returns:
            New UnifiedEntityList with filtered entities.
        """
        if isinstance(source, str):
            source = EntitySource(source)

        # "both" means the entity exists in both planes, so it should be
        # included when the caller asks for either single plane.
        if source == EntitySource.GATEWAY:
            match_sources = {EntitySource.GATEWAY, EntitySource.BOTH}
        elif source == EntitySource.KONNECT:
            match_sources = {EntitySource.KONNECT, EntitySource.BOTH}
        else:
            # Explicit "both" filter — only entities present in both planes
            match_sources = {EntitySource.BOTH}

        return UnifiedEntityList(entities=[e for e in self.entities if e.source in match_sources])


def detect_drift(
    gateway_entity: KongEntityBase | None,
    konnect_entity: KongEntityBase | None,
    compare_fields: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Detect drift between Gateway and Konnect versions of an entity.

    Compares specified fields (or all common fields) between two entity
    versions to identify configuration differences.

    Args:
        gateway_entity: Entity from Gateway.
        konnect_entity: Entity from Konnect.
        compare_fields: Specific fields to compare. If None, compares all
            common fields except 'id', 'created_at', 'updated_at'.

    Returns:
        Tuple of (has_drift, list of differing field names).
    """
    if gateway_entity is None or konnect_entity is None:
        return False, []

    # Default fields to exclude from comparison (metadata that differs by source)
    exclude_fields = {"id", "created_at", "updated_at"}

    # Get fields to compare
    gateway_data = gateway_entity.model_dump(exclude_none=True)
    konnect_data = konnect_entity.model_dump(exclude_none=True)

    if compare_fields is None:
        # Compare all common fields except excluded ones
        all_fields = set(gateway_data.keys()) | set(konnect_data.keys())
        compare_fields = list(all_fields - exclude_fields)

    drift_fields = []
    for field in compare_fields:
        if field in exclude_fields:
            continue

        gateway_val = gateway_data.get(field)
        konnect_val = konnect_data.get(field)

        # Normalize None and missing as equivalent
        if gateway_val is None and konnect_val is None:
            continue

        if gateway_val != konnect_val:
            drift_fields.append(field)

    return len(drift_fields) > 0, drift_fields


def merge_entities[T: KongEntityBase](
    gateway_entities: list[T],
    konnect_entities: list[T],
    key_field: str = "name",
    compare_fields: list[str] | None = None,
) -> UnifiedEntityList[T]:
    """Merge entities from Gateway and Konnect into a unified list.

    Matches entities by a key field (typically 'name') and detects drift
    between matching entities.

    Args:
        gateway_entities: Entities from Gateway.
        konnect_entities: Entities from Konnect.
        key_field: Field to use for matching entities (default: 'name').
        compare_fields: Fields to compare for drift detection.

    Returns:
        UnifiedEntityList with merged entities and drift information.
    """
    unified: list[UnifiedEntity[Any]] = []

    # Index entities by key
    gateway_by_key: dict[str, T] = {}
    for entity in gateway_entities:
        key = getattr(entity, key_field, None)
        if key:
            gateway_by_key[key] = entity

    konnect_by_key: dict[str, T] = {}
    for entity in konnect_entities:
        key = getattr(entity, key_field, None)
        if key:
            konnect_by_key[key] = entity

    # Process all keys
    all_keys = set(gateway_by_key.keys()) | set(konnect_by_key.keys())

    for key in sorted(all_keys):
        gateway_entity = gateway_by_key.get(key)
        konnect_entity = konnect_by_key.get(key)

        if gateway_entity and konnect_entity:
            # Entity exists in both
            has_drift, drift_fields = detect_drift(gateway_entity, konnect_entity, compare_fields)
            unified.append(
                UnifiedEntity(
                    entity=gateway_entity,  # Use gateway as primary
                    source=EntitySource.BOTH,
                    gateway_id=getattr(gateway_entity, "id", None),
                    konnect_id=getattr(konnect_entity, "id", None),
                    has_drift=has_drift,
                    drift_fields=drift_fields if drift_fields else None,
                    gateway_entity=gateway_entity,
                    konnect_entity=konnect_entity,
                )
            )
        elif gateway_entity:
            # Only in Gateway
            unified.append(
                UnifiedEntity(
                    entity=gateway_entity,
                    source=EntitySource.GATEWAY,
                    gateway_id=getattr(gateway_entity, "id", None),
                    gateway_entity=gateway_entity,
                )
            )
        elif konnect_entity:
            # Only in Konnect
            unified.append(
                UnifiedEntity(
                    entity=konnect_entity,
                    source=EntitySource.KONNECT,
                    konnect_id=getattr(konnect_entity, "id", None),
                    konnect_entity=konnect_entity,
                )
            )

    return UnifiedEntityList(entities=unified)
