"""Conflict resolution service for Kong sync operations.

This module provides models and services for detecting and resolving
conflicts between Kong Gateway and Konnect control plane during sync
operations. When entities differ between source and target, users can
interactively choose how to resolve each conflict.
"""

from __future__ import annotations

import difflib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from system_operations_manager.integrations.kong.models.unified import (
    UnifiedEntity,
    UnifiedEntityList,
)


class ResolutionAction(StrEnum):
    """Action to take when resolving a conflict."""

    KEEP_SOURCE = "keep_source"
    """Keep the source entity and overwrite target."""

    KEEP_TARGET = "keep_target"
    """Keep the target entity and skip syncing this entity."""

    SKIP = "skip"
    """Skip this entity entirely (no changes made)."""

    MERGE = "merge"
    """Merge compatible changes from both source and target."""


class Conflict(BaseModel):
    """Represents a conflict between source and target entity versions.

    A conflict occurs when an entity exists in both source and target
    with differing field values (drift). The TUI presents these conflicts
    for user resolution.

    Attributes:
        entity_type: Type of entity (services, routes, consumers, etc.)
        entity_id: Entity ID in the source system.
        entity_name: Human-readable name for display.
        source_state: Complete entity state from source.
        target_state: Complete entity state from target.
        drift_fields: List of field names that differ between versions.
        unified_entity_data: Serialized UnifiedEntity for reference.
    """

    entity_type: str = Field(description="Entity type: services, routes, etc.")
    entity_id: str | None = Field(default=None, description="Entity ID in source")
    entity_name: str = Field(description="Human-readable entity name")

    source_state: dict[str, Any] = Field(description="Entity state from source")
    target_state: dict[str, Any] = Field(description="Entity state from target")
    drift_fields: list[str] = Field(description="Fields that differ between versions")

    # Store IDs for both systems
    source_system_id: str | None = Field(default=None, description="Entity ID in source system")
    target_system_id: str | None = Field(default=None, description="Entity ID in target system")

    # Direction context
    direction: Literal["push", "pull"] = Field(description="Sync direction for context")

    model_config = {"frozen": True}

    @property
    def source_label(self) -> str:
        """Get human-readable source label based on direction."""
        return "Gateway" if self.direction == "push" else "Konnect"

    @property
    def target_label(self) -> str:
        """Get human-readable target label based on direction."""
        return "Konnect" if self.direction == "push" else "Gateway"

    @classmethod
    def from_unified_entity(
        cls,
        unified: UnifiedEntity[Any],
        entity_type: str,
        direction: Literal["push", "pull"],
    ) -> Conflict:
        """Create a Conflict from a UnifiedEntity with drift.

        Args:
            unified: UnifiedEntity that has drift between sources.
            entity_type: Type name for the entity.
            direction: Sync direction (push or pull).

        Returns:
            Conflict instance ready for resolution.

        Raises:
            ValueError: If entity doesn't have drift or missing source data.
        """
        if not unified.has_drift:
            raise ValueError(f"Entity {unified.identifier} does not have drift")

        if unified.gateway_entity is None or unified.konnect_entity is None:
            raise ValueError(f"Entity {unified.identifier} missing gateway or konnect data")

        # Determine source/target based on direction
        if direction == "push":
            source_entity = unified.gateway_entity
            target_entity = unified.konnect_entity
            source_id = unified.gateway_id
            target_id = unified.konnect_id
        else:  # pull
            source_entity = unified.konnect_entity
            target_entity = unified.gateway_entity
            source_id = unified.konnect_id
            target_id = unified.gateway_id

        return cls(
            entity_type=entity_type,
            entity_id=source_id,
            entity_name=unified.identifier,
            source_state=source_entity.model_dump(),
            target_state=target_entity.model_dump(),
            drift_fields=unified.drift_fields or [],
            source_system_id=source_id,
            target_system_id=target_id,
            direction=direction,
        )


class Resolution(BaseModel):
    """User's resolution choice for a conflict.

    Captures the user's decision on how to resolve a specific conflict,
    along with metadata for auditing.

    Attributes:
        conflict: The conflict being resolved.
        action: Resolution action chosen by user.
        resolved_at: Timestamp when resolution was made.
        notes: Optional notes from user about the resolution.
    """

    conflict: Conflict = Field(description="The conflict being resolved")
    action: ResolutionAction = Field(description="Resolution action")
    resolved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When resolution was made",
    )
    notes: str | None = Field(default=None, description="Optional user notes")
    merged_state: dict[str, Any] | None = Field(
        default=None,
        description="Merged entity state when action is MERGE",
    )

    @property
    def entity_key(self) -> str:
        """Unique key for this resolution's entity."""
        return f"{self.conflict.entity_type}:{self.conflict.entity_name}"

    @property
    def will_modify_target(self) -> bool:
        """Whether this resolution will modify the target system."""
        return self.action in (ResolutionAction.KEEP_SOURCE, ResolutionAction.MERGE)


class ConflictSummary(BaseModel):
    """Summary of conflicts by entity type.

    Provides counts for display in TUI headers and summaries.
    """

    total: int = Field(default=0, description="Total number of conflicts")
    by_type: dict[str, int] = Field(default_factory=dict, description="Conflicts per entity type")
    resolved: int = Field(default=0, description="Number resolved")
    pending: int = Field(default=0, description="Number pending resolution")


class ResolutionPreview(BaseModel):
    """Preview of what will happen when resolutions are applied.

    Shown to user before final confirmation.
    """

    will_update: list[tuple[str, str]] = Field(
        default_factory=list,
        description="List of (entity_type, entity_name) that will be updated",
    )
    will_skip: list[tuple[str, str]] = Field(
        default_factory=list,
        description="List of (entity_type, entity_name) that will be skipped",
    )
    will_merge: list[tuple[str, str]] = Field(
        default_factory=list,
        description="List of (entity_type, entity_name) that will be merged",
    )

    @property
    def update_count(self) -> int:
        """Number of entities that will be updated (includes merged)."""
        return len(self.will_update) + len(self.will_merge)

    @property
    def skip_count(self) -> int:
        """Number of entities that will be skipped."""
        return len(self.will_skip)

    @property
    def merge_count(self) -> int:
        """Number of entities that will be merged."""
        return len(self.will_merge)


def generate_entity_diff(
    source_state: dict[str, Any],
    target_state: dict[str, Any],
    drift_fields: list[str] | None = None,
    context_lines: int = 3,
) -> list[str]:
    """Generate unified diff lines between source and target state.

    Args:
        source_state: Entity state from source system.
        target_state: Entity state from target system.
        drift_fields: Optional list of fields to highlight in diff.
        context_lines: Number of context lines around changes.

    Returns:
        List of diff lines suitable for display.
    """
    # Pretty-print JSON for readable diff
    source_json = json.dumps(source_state, indent=2, sort_keys=True, default=str)
    target_json = json.dumps(target_state, indent=2, sort_keys=True, default=str)

    source_lines = source_json.splitlines(keepends=True)
    target_lines = target_json.splitlines(keepends=True)

    diff = difflib.unified_diff(
        target_lines,  # "from" is target (current state)
        source_lines,  # "to" is source (what we're syncing)
        fromfile="target",
        tofile="source",
        n=context_lines,
    )

    return list(diff)


def generate_side_by_side_diff(
    source_state: dict[str, Any],
    target_state: dict[str, Any],
    drift_fields: list[str] | None = None,
    width: int = 80,
) -> list[tuple[str, str, str]]:
    """Generate side-by-side diff for TUI display.

    Args:
        source_state: Entity state from source system.
        target_state: Entity state from target system.
        drift_fields: Fields that differ (for highlighting).
        width: Width of each column.

    Returns:
        List of (left_line, marker, right_line) tuples.
        Marker is ' ' for same, '|' for different, '<' for left only, '>' for right only.
    """
    source_json = json.dumps(source_state, indent=2, sort_keys=True, default=str)
    target_json = json.dumps(target_state, indent=2, sort_keys=True, default=str)

    source_lines = source_json.splitlines()
    target_lines = target_json.splitlines()

    # Use difflib to compute differences
    matcher = difflib.SequenceMatcher(None, target_lines, source_lines)

    result: list[tuple[str, str, str]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i in range(i2 - i1):
                result.append((target_lines[i1 + i], " ", source_lines[j1 + i]))
        elif tag == "replace":
            max_lines = max(i2 - i1, j2 - j1)
            for i in range(max_lines):
                left = target_lines[i1 + i] if i < (i2 - i1) else ""
                right = source_lines[j1 + i] if i < (j2 - j1) else ""
                result.append((left, "|", right))
        elif tag == "delete":
            for i in range(i2 - i1):
                result.append((target_lines[i1 + i], "<", ""))
        elif tag == "insert":
            for i in range(j2 - j1):
                result.append(("", ">", source_lines[j1 + i]))

    return result


class ConflictResolutionService:
    """Service for collecting and applying conflict resolutions.

    This service bridges the sync system and TUI by:
    - Collecting conflicts from UnifiedEntityList results
    - Tracking user resolutions
    - Applying resolutions to the target system
    - Recording resolution actions in the audit log
    """

    def __init__(self) -> None:
        """Initialize the conflict resolution service."""
        self._resolutions: dict[str, Resolution] = {}

    def collect_conflicts(
        self,
        entity_lists: dict[str, UnifiedEntityList[Any]],
        direction: Literal["push", "pull"],
    ) -> list[Conflict]:
        """Collect all conflicts from unified entity lists.

        Args:
            entity_lists: Dict mapping entity type to UnifiedEntityList.
            direction: Sync direction (push or pull).

        Returns:
            List of Conflict objects for entities with drift.
        """
        conflicts: list[Conflict] = []

        for entity_type, unified_list in entity_lists.items():
            for unified in unified_list.with_drift:
                try:
                    conflict = Conflict.from_unified_entity(unified, entity_type, direction)
                    conflicts.append(conflict)
                except ValueError:
                    # Skip entities without proper drift data
                    continue

        return conflicts

    def get_conflict_summary(self, conflicts: list[Conflict]) -> ConflictSummary:
        """Get summary statistics for a list of conflicts.

        Args:
            conflicts: List of conflicts to summarize.

        Returns:
            ConflictSummary with counts by type.
        """
        by_type: dict[str, int] = {}
        for conflict in conflicts:
            by_type[conflict.entity_type] = by_type.get(conflict.entity_type, 0) + 1

        resolved_keys = set(self._resolutions.keys())
        conflict_keys = {f"{c.entity_type}:{c.entity_name}" for c in conflicts}
        resolved_count = len(resolved_keys & conflict_keys)

        return ConflictSummary(
            total=len(conflicts),
            by_type=by_type,
            resolved=resolved_count,
            pending=len(conflicts) - resolved_count,
        )

    def set_resolution(self, resolution: Resolution) -> None:
        """Record a resolution for a conflict.

        Args:
            resolution: The resolution to record.
        """
        self._resolutions[resolution.entity_key] = resolution

    def get_resolution(self, conflict: Conflict) -> Resolution | None:
        """Get the resolution for a conflict if one exists.

        Args:
            conflict: The conflict to look up.

        Returns:
            Resolution if one has been set, None otherwise.
        """
        key = f"{conflict.entity_type}:{conflict.entity_name}"
        return self._resolutions.get(key)

    def get_all_resolutions(self) -> list[Resolution]:
        """Get all recorded resolutions.

        Returns:
            List of all resolutions.
        """
        return list(self._resolutions.values())

    def clear_resolutions(self) -> None:
        """Clear all recorded resolutions."""
        self._resolutions.clear()

    def build_preview(self, resolutions: list[Resolution]) -> ResolutionPreview:
        """Build a preview of what will happen when resolutions are applied.

        Args:
            resolutions: List of resolutions to preview.

        Returns:
            ResolutionPreview showing what will be updated/skipped.
        """
        preview = ResolutionPreview()

        for resolution in resolutions:
            entity_info = (
                resolution.conflict.entity_type,
                resolution.conflict.entity_name,
            )
            if resolution.action == ResolutionAction.KEEP_SOURCE:
                preview.will_update.append(entity_info)
            elif resolution.action == ResolutionAction.MERGE:
                preview.will_merge.append(entity_info)
            else:
                preview.will_skip.append(entity_info)

        return preview

    def apply_batch_resolution(
        self,
        conflicts: list[Conflict],
        action: ResolutionAction,
        entity_type: str | None = None,
    ) -> int:
        """Apply the same resolution to multiple conflicts.

        Args:
            conflicts: List of conflicts to resolve.
            action: Resolution action to apply.
            entity_type: If specified, only apply to conflicts of this type.

        Returns:
            Number of resolutions applied.
        """
        count = 0
        for conflict in conflicts:
            if entity_type is not None and conflict.entity_type != entity_type:
                continue

            resolution = Resolution(conflict=conflict, action=action)
            self.set_resolution(resolution)
            count += 1

        return count
