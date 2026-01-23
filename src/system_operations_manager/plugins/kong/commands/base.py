"""Base utilities for Kong CLI commands.

This module provides common Typer options, error handling utilities,
and shared functionality for all Kong CLI commands.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console

from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongAuthError,
    KongConnectionError,
    KongDBLessWriteError,
    KongNotFoundError,
    KongValidationError,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat

# Shared console instance for all commands
console = Console()


# =============================================================================
# Common Typer Option Annotations
# =============================================================================

OutputOption = Annotated[
    OutputFormat,
    typer.Option(
        "--output",
        "-o",
        help="Output format: table, json, or yaml",
        case_sensitive=False,
    ),
]

TagsOption = Annotated[
    list[str] | None,
    typer.Option(
        "--tag",
        "-t",
        help="Filter by tag (can be repeated for AND logic)",
    ),
]

LimitOption = Annotated[
    int | None,
    typer.Option(
        "--limit",
        "-l",
        help="Maximum number of results to return",
        min=1,
        max=1000,
    ),
]

OffsetOption = Annotated[
    str | None,
    typer.Option(
        "--offset",
        help="Pagination offset (from previous response)",
    ),
]

ForceOption = Annotated[
    bool,
    typer.Option(
        "--force",
        "-f",
        help="Skip confirmation prompts",
    ),
]

ServiceFilterOption = Annotated[
    str | None,
    typer.Option(
        "--service",
        "-s",
        help="Filter by service ID or name",
    ),
]

RouteFilterOption = Annotated[
    str | None,
    typer.Option(
        "--route",
        "-r",
        help="Filter by route ID or name",
    ),
]

ConsumerFilterOption = Annotated[
    str | None,
    typer.Option(
        "--consumer",
        "-c",
        help="Filter by consumer ID or username",
    ),
]

DataPlaneOnlyOption = Annotated[
    bool,
    typer.Option(
        "--data-plane-only",
        "--gateway-only",
        help="Write to Gateway only, skip Konnect sync",
        envvar="KONG_DATA_PLANE_ONLY",
    ),
]


# =============================================================================
# Error Handling
# =============================================================================


def handle_kong_error(error: KongAPIError) -> None:
    """Handle Kong API errors with user-friendly output.

    Converts Kong exceptions into formatted error messages and exits
    with appropriate status codes.

    Args:
        error: The Kong API error to handle.

    Raises:
        typer.Exit: Always exits with code 1.
    """
    if isinstance(error, KongConnectionError):
        console.print("[red]Error:[/red] Cannot connect to Kong Admin API")
        console.print(f"  {error.message}")
        if error.original_error:
            console.print(f"  Cause: {error.original_error}")
        console.print("\n[dim]Hint: Check that Kong is running and the URL is correct.[/dim]")

    elif isinstance(error, KongAuthError):
        console.print("[red]Error:[/red] Authentication failed")
        console.print(f"  {error.message}")
        console.print("\n[dim]Hint: Check your API key or certificate configuration.[/dim]")

    elif isinstance(error, KongNotFoundError):
        console.print(f"[red]Error:[/red] {error.resource_type} not found")
        if error.resource_id:
            console.print(f"  Could not find {error.resource_type} '{error.resource_id}'")
        else:
            console.print(f"  {error.message}")

    elif isinstance(error, KongValidationError):
        console.print("[red]Error:[/red] Validation failed")
        console.print(f"  {error.message}")
        if error.validation_errors:
            console.print("\n  Field errors:")
            for field, err in error.validation_errors.items():
                console.print(f"    - {field}: {err}")

    elif isinstance(error, KongDBLessWriteError):
        console.print("[red]Error:[/red] Kong is running in DB-less mode")
        console.print("  Write operations are not available via the Admin API.")
        console.print("\n[dim]Hint: Use declarative configuration instead:[/dim]")
        console.print("  ops kong config apply <config-file>")

    else:
        console.print(f"[red]Error:[/red] {error.message}")
        if error.status_code:
            console.print(f"  HTTP Status: {error.status_code}")
        if error.endpoint:
            console.print(f"  Endpoint: {error.endpoint}")

    raise typer.Exit(1)


# =============================================================================
# Confirmation Utilities
# =============================================================================


def confirm_delete(entity_type: str, id_or_name: str) -> bool:
    """Prompt user to confirm deletion.

    Args:
        entity_type: Type of entity (e.g., "service", "route").
        id_or_name: Entity identifier being deleted.

    Returns:
        True if user confirms, False otherwise.
    """
    return typer.confirm(
        f"Are you sure you want to delete {entity_type} '{id_or_name}'?",
        default=False,
    )


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt user to confirm an action.

    Args:
        message: Confirmation message to display.
        default: Default response if user just presses Enter.

    Returns:
        True if user confirms, False otherwise.
    """
    return typer.confirm(message, default=default)


# =============================================================================
# Configuration Parsing Utilities
# =============================================================================


def parse_config_options(config_items: list[str] | None) -> dict[str, Any]:
    """Parse --config key=value options into a dictionary.

    Supports nested keys using dot notation (e.g., "outer.inner=value").

    Args:
        config_items: List of "key=value" strings.

    Returns:
        Dictionary of configuration values.

    Raises:
        typer.BadParameter: If a config item is malformed.

    Example:
        >>> parse_config_options(["minute=100", "hour=5000"])
        {'minute': 100, 'hour': 5000}
        >>> parse_config_options(["limits.minute=100"])
        {'limits': {'minute': 100}}
    """
    if not config_items:
        return {}

    result: dict[str, Any] = {}

    for item in config_items:
        if "=" not in item:
            raise typer.BadParameter(f"Invalid config format: '{item}'. Expected 'key=value'.")

        key, _, value = item.partition("=")
        key = key.strip()
        value = value.strip()

        if not key:
            raise typer.BadParameter(f"Empty key in config: '{item}'")

        # Parse the value
        parsed_value = _parse_config_value(value)

        # Handle nested keys
        if "." in key:
            _set_nested(result, key.split("."), parsed_value)
        else:
            result[key] = parsed_value

    return result


def _parse_config_value(value: str) -> Any:
    """Parse a config value string into the appropriate Python type.

    Args:
        value: String value to parse.

    Returns:
        Parsed value (int, float, bool, or string).
    """
    # Boolean values
    if value.lower() in ("true", "yes", "on"):
        return True
    if value.lower() in ("false", "no", "off"):
        return False

    # Numeric values
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    # Return as string
    return value


def _set_nested(d: dict[str, Any], keys: list[str], value: Any) -> None:
    """Set a value in a nested dictionary structure.

    Args:
        d: Dictionary to modify.
        keys: List of keys representing the path.
        value: Value to set at the path.
    """
    for key in keys[:-1]:
        if key not in d:
            d[key] = {}
        d = d[key]
    d[keys[-1]] = value


def merge_config(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    """Deep merge two configuration dictionaries.

    Args:
        base: Base configuration dictionary.
        override: Override values to merge in.

    Returns:
        Merged configuration dictionary.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value

    return result
