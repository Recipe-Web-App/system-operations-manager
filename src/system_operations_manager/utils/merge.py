"""Merge analysis, computation, and validation utilities.

This module provides utilities for detecting auto-mergeable conflicts,
computing merged state, and validating the result.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MergeAnalysis(BaseModel):
    """Result of analyzing whether a conflict can be auto-merged.

    Attributes:
        can_auto_merge: True if source and target changes don't overlap.
        source_only_fields: Fields changed only in source.
        target_only_fields: Fields changed only in target.
        conflicting_fields: Fields changed in both (require manual merge).
    """

    can_auto_merge: bool = Field(description="Whether auto-merge is possible")
    source_only_fields: list[str] = Field(
        default_factory=list,
        description="Fields that only differ in source",
    )
    target_only_fields: list[str] = Field(
        default_factory=list,
        description="Fields that only differ in target",
    )
    conflicting_fields: list[str] = Field(
        default_factory=list,
        description="Fields that differ in both source and target",
    )


class MergeValidationResult(BaseModel):
    """Result of validating a merged state.

    Attributes:
        is_valid: True if merged state passes all checks.
        errors: List of error messages (validation failures).
        warnings: List of warning messages (non-blocking issues).
    """

    is_valid: bool = Field(description="Whether validation passed")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")


def _get_leaf_paths(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Get all leaf paths in a nested object.

    Args:
        obj: Object to traverse.
        prefix: Current path prefix.

    Returns:
        Dict mapping dotted paths to leaf values.

    Example:
        {"config": {"timeout": 30, "retries": 3}}
        -> {"config.timeout": 30, "config.retries": 3}
    """
    if not isinstance(obj, dict):
        return {prefix: obj} if prefix else {}

    result: dict[str, Any] = {}
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_get_leaf_paths(value, path))
        else:
            result[path] = value

    return result


def _is_array_field(path: str, source: dict[str, Any], target: dict[str, Any]) -> bool:
    """Check if a field path points to an array in either source or target."""
    parts = path.split(".")

    def get_value(obj: dict[str, Any], parts: list[str]) -> Any:
        current = obj
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    source_val = get_value(source, parts)
    target_val = get_value(target, parts)

    return isinstance(source_val, list) or isinstance(target_val, list)


def analyze_merge_potential(
    source_state: dict[str, Any],
    target_state: dict[str, Any],
    original_state: dict[str, Any] | None = None,
) -> MergeAnalysis:
    """Analyze whether a conflict can be auto-merged.

    Determines if source and target changed different fields (auto-mergeable)
    or if they changed the same fields (requires manual merge).

    Args:
        source_state: Entity state from source system.
        target_state: Entity state from target system.
        original_state: Optional original state before divergence.
            If not provided, uses target_state as the baseline.

    Returns:
        MergeAnalysis indicating merge potential.

    Rules:
        - Fields changed only in source: can auto-merge
        - Fields changed only in target: can auto-merge
        - Fields changed in both: conflict (manual required)
        - Arrays changed on both sides: always conflict
        - Nested objects: recurse to leaf level
    """
    # Use target as baseline if no original provided
    baseline = original_state if original_state is not None else target_state

    # Get leaf paths for all three states
    source_leaves = _get_leaf_paths(source_state)
    target_leaves = _get_leaf_paths(target_state)
    baseline_leaves = _get_leaf_paths(baseline)

    # Find all unique paths
    all_paths = set(source_leaves.keys()) | set(target_leaves.keys()) | set(baseline_leaves.keys())

    source_only: list[str] = []
    target_only: list[str] = []
    conflicting: list[str] = []

    for path in all_paths:
        source_val = source_leaves.get(path)
        target_val = target_leaves.get(path)
        baseline_val = baseline_leaves.get(path)

        source_changed = source_val != baseline_val
        target_changed = target_val != baseline_val

        # Check if this is an array field
        is_array = _is_array_field(path, source_state, target_state)

        if source_changed and target_changed:
            # Both changed - conflict
            conflicting.append(path)
        elif source_changed:
            # Only source changed - check for array special case
            if is_array:
                # Arrays that are modified always need attention
                # If target didn't change it, it's still source_only (OK)
                source_only.append(path)
            else:
                source_only.append(path)
        elif target_changed:
            target_only.append(path)

    # Can auto-merge if no conflicting fields
    can_auto_merge = len(conflicting) == 0

    return MergeAnalysis(
        can_auto_merge=can_auto_merge,
        source_only_fields=sorted(source_only),
        target_only_fields=sorted(target_only),
        conflicting_fields=sorted(conflicting),
    )


def _set_nested_value(obj: dict[str, Any], path: str, value: Any) -> None:
    """Set a value at a nested path, creating intermediate dicts as needed."""
    parts = path.split(".")
    current = obj

    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    current[parts[-1]] = value


def _get_nested_value(obj: dict[str, Any], path: str, default: Any = None) -> Any:
    """Get a value at a nested path."""
    parts = path.split(".")
    current = obj

    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]

    return current


def compute_auto_merge(
    source_state: dict[str, Any],
    target_state: dict[str, Any],
    analysis: MergeAnalysis,
) -> dict[str, Any]:
    """Compute merged state for auto-mergeable conflicts.

    Takes source values for source_only_fields, target values for
    target_only_fields, and preserves unchanged fields.

    Args:
        source_state: Entity state from source system.
        target_state: Entity state from target system.
        analysis: MergeAnalysis from analyze_merge_potential.

    Returns:
        Merged entity state dictionary.

    Raises:
        ValueError: If analysis indicates conflicting fields exist.
    """
    if not analysis.can_auto_merge:
        raise ValueError(f"Cannot auto-merge: conflicting fields: {analysis.conflicting_fields}")

    # Start with a deep copy of target state (preserves structure)
    import copy

    merged = copy.deepcopy(target_state)

    # Apply source-only changes
    for path in analysis.source_only_fields:
        value = _get_nested_value(source_state, path)
        _set_nested_value(merged, path, value)

    return merged


# Required fields by entity type (Kong entities)
REQUIRED_FIELDS: dict[str, list[str]] = {
    "services": ["name", "host"],
    "routes": ["name"],
    "consumers": ["username"],
    "plugins": ["name"],
    "upstreams": ["name"],
    "targets": ["target"],
    "certificates": ["cert", "key"],
    "snis": ["name"],
    "ca_certificates": ["cert"],
}

# Expected types for common fields
EXPECTED_TYPES: dict[str, type | tuple[type, ...]] = {
    "name": str,
    "host": str,
    "port": int,
    "retries": int,
    "connect_timeout": int,
    "write_timeout": int,
    "read_timeout": int,
    "enabled": bool,
    "tags": list,
    "protocols": list,
    "methods": list,
    "paths": list,
    "hosts": list,
}


def validate_merged_state(
    merged_state: dict[str, Any],
    entity_type: str,
    source_state: dict[str, Any] | None = None,
    target_state: dict[str, Any] | None = None,
) -> MergeValidationResult:
    """Validate merged entity state.

    Checks:
    1. Required fields present (based on entity type)
    2. Field types match expected (numbers stay numbers, etc.)
    3. Unknown fields generate warnings

    Args:
        merged_state: The merged entity state to validate.
        entity_type: Kong entity type (services, routes, etc.).
        source_state: Original source state for comparison.
        target_state: Original target state for comparison.

    Returns:
        MergeValidationResult with validation status and messages.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check required fields
    required = REQUIRED_FIELDS.get(entity_type, [])
    for field in required:
        if field not in merged_state or merged_state[field] is None:
            errors.append(f"Missing required field: {field}")

    # Check field types
    for field, value in merged_state.items():
        if value is None:
            continue

        expected_type = EXPECTED_TYPES.get(field)
        if expected_type and not isinstance(value, expected_type):
            # Handle both single type and tuple of types for error message
            if isinstance(expected_type, tuple):
                type_names = ", ".join(t.__name__ for t in expected_type)
            else:
                type_names = expected_type.__name__
            errors.append(
                f"Type mismatch for field '{field}': expected {type_names}, "
                f"got {type(value).__name__}"
            )

    # Check for unknown fields (compare to known fields)
    if source_state and target_state:
        known_fields = set(source_state.keys()) | set(target_state.keys())
        for field in merged_state:
            if field not in known_fields:
                warnings.append(f"Unknown field added: {field}")

    return MergeValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
