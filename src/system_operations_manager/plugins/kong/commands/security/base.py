"""Base utilities for security commands.

Provides common functionality for file reading, certificate handling,
and shared Typer options across security commands.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    OutputOption,
    console,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

# Re-export commonly used items for convenience
__all__ = [
    "ACL_COLUMNS",
    "JWT_COLUMNS",
    "KEY_AUTH_COLUMNS",
    "MTLS_COLUMNS",
    "OAUTH2_COLUMNS",
    "ForceOption",
    "HideCredentialsOption",
    "OutputFormat",
    "OutputOption",
    "RouteScopeOption",
    "ServiceScopeOption",
    "build_plugin_config",
    "console",
    "get_formatter",
    "handle_kong_error",
    "read_file_or_value",
]


# =============================================================================
# Common Typer Option Annotations for Security Commands
# =============================================================================

ServiceScopeOption = Annotated[
    str | None,
    typer.Option(
        "--service",
        "-s",
        help="Apply to service (ID or name)",
    ),
]

RouteScopeOption = Annotated[
    str | None,
    typer.Option(
        "--route",
        "-r",
        help="Apply to route (ID or name)",
    ),
]

HideCredentialsOption = Annotated[
    bool,
    typer.Option(
        "--hide-credentials/--show-credentials",
        help="Hide credentials from upstream request headers/body",
    ),
]


# =============================================================================
# Column Definitions for Credential Listings
# =============================================================================

KEY_AUTH_COLUMNS = [
    ("id", "ID"),
    ("key", "API Key"),
    ("ttl", "TTL"),
    ("created_at", "Created"),
]

JWT_COLUMNS = [
    ("id", "ID"),
    ("key", "Key (iss)"),
    ("algorithm", "Algorithm"),
    ("created_at", "Created"),
]

OAUTH2_COLUMNS = [
    ("id", "ID"),
    ("name", "App Name"),
    ("client_id", "Client ID"),
    ("redirect_uris", "Redirect URIs"),
]

ACL_COLUMNS = [
    ("id", "ID"),
    ("group", "Group"),
    ("tags", "Tags"),
]

MTLS_COLUMNS = [
    ("id", "ID"),
    ("subject_name", "Subject"),
    ("created_at", "Created"),
]


# =============================================================================
# File Reading Utilities
# =============================================================================


def read_file_or_value(value: str) -> str:
    """Read value from file if prefixed with @, otherwise return as-is.

    Supports the @/path/to/file pattern commonly used for certificates,
    keys, and other file-based configuration values.

    Args:
        value: Either a direct value or @/path/to/file.

    Returns:
        The value or file contents.

    Raises:
        typer.BadParameter: If file doesn't exist or can't be read.

    Example:
        >>> read_file_or_value("@/path/to/cert.pem")  # Returns file contents
        >>> read_file_or_value("inline-value")         # Returns "inline-value"
    """
    if value.startswith("@"):
        file_path = Path(value[1:])
        if not file_path.exists():
            raise typer.BadParameter(f"File not found: {file_path}")
        try:
            return file_path.read_text().strip()
        except OSError as e:
            raise typer.BadParameter(f"Cannot read file {file_path}: {e}") from e
    return value


def build_plugin_config(**kwargs: Any) -> dict[str, Any]:
    """Build plugin configuration dict from keyword arguments.

    Filters out None values and returns a clean config dictionary.

    Args:
        **kwargs: Configuration key-value pairs.

    Returns:
        Dictionary with only non-None values.

    Example:
        >>> build_plugin_config(minute=100, hour=None, policy="local")
        {'minute': 100, 'policy': 'local'}
    """
    return {k: v for k, v in kwargs.items() if v is not None}
