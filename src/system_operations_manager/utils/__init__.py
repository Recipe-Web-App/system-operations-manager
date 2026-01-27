"""Utility functions for system_operations_manager."""

from system_operations_manager.utils.editor import (
    create_merge_template,
    get_editor,
    parse_merge_result,
    strip_json_comments,
)
from system_operations_manager.utils.merge import (
    MergeAnalysis,
    MergeValidationResult,
    analyze_merge_potential,
    compute_auto_merge,
    validate_merged_state,
)

__all__ = [
    "MergeAnalysis",
    "MergeValidationResult",
    "analyze_merge_potential",
    "compute_auto_merge",
    "create_merge_template",
    "get_editor",
    "parse_merge_result",
    "strip_json_comments",
    "validate_merged_state",
]
