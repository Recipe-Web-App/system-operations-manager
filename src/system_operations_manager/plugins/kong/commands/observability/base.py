"""Base utilities for observability commands.

Provides common functionality for logging, metrics, health, and tracing commands.
"""

from __future__ import annotations

from typing import Annotated

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
    "ForceOption",
    "GlobalScopeOption",
    "OutputFormat",
    "OutputOption",
    "RouteScopeOption",
    "ServiceScopeOption",
    "UpstreamArgument",
    "console",
    "get_formatter",
    "handle_kong_error",
    "validate_scope",
    "validate_scope_optional",
]


# =============================================================================
# Common Typer Option Annotations for Observability Commands
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

GlobalScopeOption = Annotated[
    bool,
    typer.Option(
        "--global",
        "-g",
        help="Apply globally (all services and routes)",
    ),
]

UpstreamArgument = Annotated[
    str,
    typer.Argument(
        help="Upstream name or ID",
    ),
]


# =============================================================================
# Validation Utilities
# =============================================================================


def validate_scope(
    service: str | None,
    route: str | None,
    global_scope: bool = False,
) -> None:
    """Validate that at least one scope option is provided.

    Args:
        service: Service ID or name.
        route: Route ID or name.
        global_scope: Whether to apply globally.

    Raises:
        typer.Exit: If no scope is provided.
    """
    if not service and not route and not global_scope:
        console.print("[red]Error:[/red] Either --service, --route, or --global is required")
        raise typer.Exit(1)


def validate_scope_optional(
    service: str | None,
    route: str | None,
) -> None:
    """Validate scope when at least one is provided (but both optional).

    This is used for get/disable commands where we need to find
    existing plugins.

    Args:
        service: Service ID or name.
        route: Route ID or name.

    Raises:
        typer.Exit: If neither service nor route is provided.
    """
    if not service and not route:
        console.print("[red]Error:[/red] Either --service or --route is required")
        raise typer.Exit(1)
