"""Request size limiting commands for Kong Gateway.

Provides CLI commands for configuring request payload size limits
using Kong's request-size-limiting plugin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.traffic.base import (
    ForceOption,
    OutputOption,
    RouteScopeOption,
    ServiceScopeOption,
    console,
    find_plugin_for_scope,
    get_formatter,
    handle_kong_error,
    validate_scope,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat

if TYPE_CHECKING:
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager

# Kong plugin name
PLUGIN_NAME = "request-size-limiting"

# Valid size units
SIZE_UNITS = ["megabytes", "kilobytes", "bytes"]


def register_request_size_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register request size limiting subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
    """
    request_size_app = typer.Typer(
        name="request-size",
        help="Request size limiting configuration",
        no_args_is_help=True,
    )

    @request_size_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        allowed_payload_size: Annotated[
            int,
            typer.Option(
                "--allowed-payload-size",
                "-a",
                help="Maximum allowed request body size (default unit: megabytes)",
            ),
        ] = 128,
        size_unit: Annotated[
            str,
            typer.Option(
                "--size-unit",
                "-u",
                help="Size unit: megabytes, kilobytes, or bytes",
            ),
        ] = "megabytes",
        require_content_length: Annotated[
            bool,
            typer.Option(
                "--require-content-length/--no-require-content-length",
                help="Require Content-Length header in requests",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable request size limiting on a service or route.

        Restricts the size of request payloads to protect APIs from
        oversized requests that could cause memory issues.

        Examples:
            ops kong traffic request-size enable --service my-api
            ops kong traffic request-size enable --service my-api --allowed-payload-size 10
            ops kong traffic request-size enable --route my-route --allowed-payload-size 512 --size-unit kilobytes
            ops kong traffic request-size enable --service my-api --require-content-length
        """
        validate_scope(service, route)

        # Validate size_unit
        if size_unit not in SIZE_UNITS:
            console.print(
                f"[red]Error:[/red] Invalid size unit '{size_unit}'. "
                f"Must be one of: {', '.join(SIZE_UNITS)}"
            )
            raise typer.Exit(1)

        # Build plugin configuration
        config: dict[str, Any] = {
            "allowed_payload_size": allowed_payload_size,
            "size_unit": size_unit,
            "require_content_length": require_content_length,
        }

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                PLUGIN_NAME,
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Request size limiting enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="Request Size Limiting Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @request_size_app.command("get")
    def get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get request size limiting configuration for a service or route.

        Shows the current request size limiting plugin configuration if one exists.

        Examples:
            ops kong traffic request-size get --service my-api
            ops kong traffic request-size get --route my-route
            ops kong traffic request-size get --service my-api --output json
        """
        validate_scope(service, route)

        try:
            manager = get_plugin_manager()
            plugin_data = find_plugin_for_scope(manager, PLUGIN_NAME, service, route)

            if not plugin_data:
                scope_desc = f"service '{service}'" if service else f"route '{route}'"
                console.print(
                    f"[yellow]No request size limiting plugin found for {scope_desc}[/yellow]"
                )
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="Request Size Limiting Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @request_size_app.command("disable")
    def disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable request size limiting on a service or route.

        Removes the request size limiting plugin from the specified scope.

        Examples:
            ops kong traffic request-size disable --service my-api
            ops kong traffic request-size disable --route my-route --force
        """
        validate_scope(service, route)

        try:
            manager = get_plugin_manager()
            plugin_data = find_plugin_for_scope(manager, PLUGIN_NAME, service, route)

            if not plugin_data:
                scope_desc = f"service '{service}'" if service else f"route '{route}'"
                console.print(
                    f"[yellow]No request size limiting plugin found for {scope_desc}[/yellow]"
                )
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id or not isinstance(plugin_id, str):
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope_desc = f"service '{service}'" if service else f"route '{route}'"

            # Confirm unless force flag
            if not force and not typer.confirm(
                f"Are you sure you want to disable request size limiting on {scope_desc}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(
                f"[green]Request size limiting disabled successfully on {scope_desc}[/green]"
            )

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(request_size_app, name="request-size")
