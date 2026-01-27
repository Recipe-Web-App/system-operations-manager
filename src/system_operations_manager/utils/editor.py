"""Editor configuration and merge template utilities.

This module provides utilities for getting the configured editor and
creating/parsing merge templates for manual conflict resolution.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from system_operations_manager.services.kong.conflict_resolver import Conflict


def get_editor() -> str:
    """Get the configured editor command.

    Priority order:
    1. ProfileConfig.default_editor (from ~/.config/ops/config.yaml)
    2. OPS_DEFAULT_EDITOR environment variable
    3. EDITOR environment variable
    4. VISUAL environment variable
    5. "vim" fallback

    Returns:
        Editor command string (e.g., "vim", "code --wait", "nano").
    """
    # Try loading from config first
    try:
        from system_operations_manager.core.config import load_config

        config = load_config()
        if config:
            profile = config.profiles.get("default")
            if profile and profile.default_editor:
                return profile.default_editor
    except ImportError:
        pass

    # Fall through environment variables
    return (
        os.environ.get("OPS_DEFAULT_EDITOR")
        or os.environ.get("EDITOR")
        or os.environ.get("VISUAL")
        or "vim"
    )


def create_merge_template(conflict: Conflict) -> str:
    """Create a JSON template for manual merge resolution.

    The template includes JSON5-style comments showing the source and target
    values for each field, with the user expected to choose or edit values.

    Args:
        conflict: The conflict to create a template for.

    Returns:
        JSON string with comments for manual editing.

    Example output:
        {
          // CONFLICT RESOLUTION TEMPLATE
          // Entity: my-service (services)
          // Direction: push (Gateway -> Konnect)
          //
          // Edit the values below to create your merged result.
          // Remove these comments before saving.

          // Field: host
          // Source (Gateway): "new-api.example.com"
          // Target (Konnect): "old-api.example.com"
          "host": "new-api.example.com",

          ...
        }
    """
    lines: list[str] = []

    # Header
    lines.append("// CONFLICT RESOLUTION TEMPLATE")
    lines.append(f"// Entity: {conflict.entity_name} ({conflict.entity_type})")
    lines.append(
        f"// Direction: {conflict.direction} ({conflict.source_label} -> {conflict.target_label})"
    )
    lines.append("//")
    lines.append("// Edit the values below to create your merged result.")
    lines.append("// Remove these comments before saving.")
    lines.append("")
    lines.append("{")

    # Get all keys from both source and target
    all_keys = set(conflict.source_state.keys()) | set(conflict.target_state.keys())
    sorted_keys = sorted(all_keys)

    for i, key in enumerate(sorted_keys):
        source_val = conflict.source_state.get(key)
        target_val = conflict.target_state.get(key)

        is_drift = key in conflict.drift_fields

        # Add field comment
        if is_drift:
            lines.append(f"  // CHANGED - Field: {key}")
        else:
            lines.append(f"  // Field: {key}")

        lines.append(
            f"  // Source ({conflict.source_label}): {json.dumps(source_val, default=str)}"
        )
        lines.append(
            f"  // Target ({conflict.target_label}): {json.dumps(target_val, default=str)}"
        )

        # Default to source value for drift fields, keep existing for unchanged
        value = source_val if key in conflict.source_state else target_val
        value_str = json.dumps(value, indent=2, default=str)

        # Handle multi-line values
        if "\n" in value_str:
            value_lines = value_str.split("\n")
            value_str = value_lines[0]
            for vl in value_lines[1:]:
                value_str += "\n  " + vl

        # Add trailing comma except for last item
        comma = "," if i < len(sorted_keys) - 1 else ""
        lines.append(f'  "{key}": {value_str}{comma}')
        lines.append("")

    lines.append("}")

    return "\n".join(lines)


def parse_merge_result(content: str) -> dict[str, Any]:
    """Parse edited JSON content, stripping comments.

    Handles JSON5-style // comments that were added by create_merge_template.

    Args:
        content: The edited content from the editor.

    Returns:
        Parsed dictionary from the JSON content.

    Raises:
        json.JSONDecodeError: If the content is not valid JSON after stripping comments.
        ValueError: If the parsed content is not a dictionary.
    """
    # Remove single-line comments (// ...)
    # Be careful not to remove // inside strings
    cleaned_lines: list[str] = []
    in_string = False
    escape_next = False

    for line in content.split("\n"):
        cleaned_line = ""
        i = 0
        in_string = False
        escape_next = False

        while i < len(line):
            char = line[i]

            if escape_next:
                cleaned_line += char
                escape_next = False
                i += 1
                continue

            if char == "\\":
                escape_next = True
                cleaned_line += char
                i += 1
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                cleaned_line += char
                i += 1
                continue

            # Check for comment start
            if not in_string and char == "/" and i + 1 < len(line) and line[i + 1] == "/":
                # Rest of line is comment, skip it
                break

            cleaned_line += char
            i += 1

        cleaned_lines.append(cleaned_line)

    cleaned_content = "\n".join(cleaned_lines)

    # Parse the cleaned JSON
    result = json.loads(cleaned_content)

    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object, got {type(result).__name__}")

    return result


def strip_json_comments(content: str) -> str:
    """Strip JSON5-style // comments from content.

    This is a simpler alternative to parse_merge_result when you just
    need the cleaned string.

    Args:
        content: JSON content with // comments.

    Returns:
        Cleaned JSON content without comments.
    """
    # Use regex to remove // comments that are not inside strings
    # This is a simplified approach that handles most cases
    result_lines = []
    for line in content.split("\n"):
        # Find // that's not inside a string
        # Simple heuristic: if odd number of " before //, it's inside a string
        comment_pos = -1
        i = 0
        in_string = False
        escape_next = False

        while i < len(line):
            if escape_next:
                escape_next = False
                i += 1
                continue

            char = line[i]
            if char == "\\":
                escape_next = True
            elif char == '"':
                in_string = not in_string
            elif not in_string and char == "/" and i + 1 < len(line) and line[i + 1] == "/":
                comment_pos = i
                break
            i += 1

        if comment_pos >= 0:
            result_lines.append(line[:comment_pos].rstrip())
        else:
            result_lines.append(line)

    return "\n".join(result_lines)
