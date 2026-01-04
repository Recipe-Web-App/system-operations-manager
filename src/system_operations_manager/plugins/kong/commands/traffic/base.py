"""Base utilities for traffic control commands.

Provides common functionality for rate limiting, request size limiting,
and request/response transformation commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    OutputOption,
    console,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager

# Re-export commonly used items for convenience
__all__ = [
    "ForceOption",
    "OutputFormat",
    "OutputOption",
    "RouteScopeOption",
    "ServiceScopeOption",
    "console",
    "find_plugin_for_scope",
    "get_formatter",
    "handle_kong_error",
    "validate_scope",
]


# =============================================================================
# Common Typer Option Annotations for Traffic Commands
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


# =============================================================================
# Validation Utilities
# =============================================================================


def validate_scope(service: str | None, route: str | None) -> None:
    """Validate that at least one scope option is provided.

    Args:
        service: Service ID or name.
        route: Route ID or name.

    Raises:
        typer.Exit: If neither service nor route is provided.
    """
    if not service and not route:
        console.print("[red]Error:[/red] Either --service or --route is required")
        raise typer.Exit(1)


# =============================================================================
# Plugin Lookup Utilities
# =============================================================================


def find_plugin_for_scope(
    manager: KongPluginManager,
    plugin_name: str,
    service: str | None = None,
    route: str | None = None,
) -> dict[str, Any] | None:
    """Find an existing plugin instance for the given scope.

    Searches for a plugin by name that matches the specified service or route scope.

    Args:
        manager: The KongPluginManager instance.
        plugin_name: Name of the plugin to find (e.g., "rate-limiting").
        service: Service ID or name to filter by.
        route: Route ID or name to filter by.

    Returns:
        The plugin entity dict if found, None otherwise.
    """
    # Get all plugins of this type
    plugins_result = manager.list(name=plugin_name)

    # Handle case where list returns non-list (e.g., error or pagination cursor)
    if not isinstance(plugins_result, list):
        return None

    for plugin in plugins_result:
        plugin_data: dict[str, Any] = plugin.model_dump()

        # Check if plugin matches the requested scope
        if service:
            plugin_service = plugin_data.get("service")
            if plugin_service and isinstance(plugin_service, dict):
                service_id = plugin_service.get("id")
                service_name = plugin_service.get("name")
                if service_id == service or service_name == service:
                    return plugin_data
        elif route:
            plugin_route = plugin_data.get("route")
            if plugin_route and isinstance(plugin_route, dict):
                route_id = plugin_route.get("id")
                route_name = plugin_route.get("name")
                if route_id == route or route_name == route:
                    return plugin_data

    return None
