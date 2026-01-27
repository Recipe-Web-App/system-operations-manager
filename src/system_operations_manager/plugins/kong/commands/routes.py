"""CLI commands for Kong Routes.

This module provides commands for managing Kong Route entities:
- list: List all routes
- get: Get route details
- create: Create a new route
- update: Update an existing route
- delete: Delete a route
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.plugins.kong.commands.base import (
    DataPlaneOnlyOption,
    ForceOption,
    LimitOption,
    OffsetOption,
    OutputOption,
    ServiceFilterOption,
    TagsOption,
    confirm_delete,
    console,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.dual_write import DualWriteService
    from system_operations_manager.services.kong.route_manager import RouteManager
    from system_operations_manager.services.kong.unified_query import UnifiedQueryService


# Column definitions for route listings
ROUTE_COLUMNS = [
    ("name", "Name"),
    ("id", "ID"),
    ("paths", "Paths"),
    ("methods", "Methods"),
    ("hosts", "Hosts"),
    ("service", "Service"),
]


def register_route_commands(
    app: typer.Typer,
    get_manager: Callable[[], RouteManager],
    get_unified_query_service: Callable[[], UnifiedQueryService | None] | None = None,
    get_dual_write_service: Callable[[], DualWriteService[Any]] | None = None,
) -> None:
    """Register route commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_manager: Factory function that returns a RouteManager instance.
        get_unified_query_service: Optional factory that returns a UnifiedQueryService
            for querying both Gateway and Konnect.
        get_dual_write_service: Optional factory that returns a DualWriteService
            for writing to both Gateway and Konnect.
    """
    routes_app = typer.Typer(
        name="routes",
        help="Manage Kong Routes",
        no_args_is_help=True,
    )

    @routes_app.command("list")
    def list_routes(
        service: ServiceFilterOption = None,
        output: OutputOption = OutputFormat.TABLE,
        tags: TagsOption = None,
        limit: LimitOption = None,
        offset: OffsetOption = None,
        source: Annotated[
            str | None,
            typer.Option(
                "--source",
                "-S",
                help="Filter by source: gateway, konnect (only when Konnect is configured)",
            ),
        ] = None,
        compare: Annotated[
            bool,
            typer.Option(
                "--compare",
                help="Show drift details between Gateway and Konnect",
            ),
        ] = False,
    ) -> None:
        """List all routes.

        When Konnect is configured, shows routes from both Gateway and Konnect
        with a Source column indicating where each route exists.

        Examples:
            ops kong routes list
            ops kong routes list --service my-api
            ops kong routes list --tag production --output json
            ops kong routes list --source gateway
            ops kong routes list --compare
        """
        formatter = get_formatter(output, console)

        # Try unified query first if available
        unified_service = get_unified_query_service() if get_unified_query_service else None

        if unified_service is not None:
            try:
                results = unified_service.list_routes(tags=tags, service_name_or_id=service)

                # Filter by source if specified
                if source:
                    results = results.filter_by_source(source)

                title = f"Routes for Service: {service}" if service else "Kong Routes"
                formatter.format_unified_list(
                    results,
                    ROUTE_COLUMNS,
                    title=title,
                    show_drift=compare,
                )
                return
            except Exception as e:
                # Fall back to gateway-only if unified query fails
                console.print(
                    f"[dim]Note: Unified query unavailable ({e}), showing gateway only[/dim]\n"
                )

        # Fall back to gateway-only query
        if source == "konnect":
            console.print(
                "[yellow]Konnect not configured. Use 'ops kong konnect login' to configure.[/yellow]"
            )
            raise typer.Exit(1)

        try:
            manager = get_manager()

            if service:
                routes, next_offset = manager.list_by_service(
                    service, tags=tags, limit=limit, offset=offset
                )
                title = f"Routes for Service: {service}"
            else:
                routes, next_offset = manager.list(tags=tags, limit=limit, offset=offset)
                title = "Kong Routes"

            formatter.format_list(routes, ROUTE_COLUMNS, title=title)

            if next_offset:
                console.print(f"\n[dim]More results available. Use --offset {next_offset}[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @routes_app.command("get")
    def get_route(
        name_or_id: Annotated[str, typer.Argument(help="Route name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a route by name or ID.

        Examples:
            ops kong routes get my-route
            ops kong routes get my-route --output json
        """
        try:
            manager = get_manager()
            route = manager.get(name_or_id)

            formatter = get_formatter(output, console)
            title = f"Route: {route.name or route.id}"
            formatter.format_entity(route, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @routes_app.command("create")
    def create_route(
        name: Annotated[
            str | None,
            typer.Option("--name", "-n", help="Route name (unique)"),
        ] = None,
        service: Annotated[
            str | None,
            typer.Option("--service", "-s", help="Service ID or name (required)"),
        ] = None,
        paths: Annotated[
            list[str] | None,
            typer.Option("--path", "-p", help="Path to match (can be repeated)"),
        ] = None,
        methods: Annotated[
            list[str] | None,
            typer.Option("--method", "-m", help="HTTP method (can be repeated)"),
        ] = None,
        hosts: Annotated[
            list[str] | None,
            typer.Option("--host", "-H", help="Host header (can be repeated)"),
        ] = None,
        protocols: Annotated[
            list[str] | None,
            typer.Option("--protocol", help="Protocol (http, https, grpc, etc.)"),
        ] = None,
        strip_path: Annotated[
            bool,
            typer.Option("--strip-path/--no-strip-path", help="Strip matched path prefix"),
        ] = True,
        preserve_host: Annotated[
            bool,
            typer.Option("--preserve-host/--no-preserve-host", help="Preserve host header"),
        ] = False,
        regex_priority: Annotated[
            int | None,
            typer.Option("--regex-priority", help="Priority for regex matching"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (can be repeated)"),
        ] = None,
        data_plane_only: DataPlaneOnlyOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new route.

        At least one matching criterion (--path, --method, --host) should be provided.
        By default, creates the route in both Gateway and Konnect (if configured).

        Examples:
            ops kong routes create --service my-api --path /api/v1
            ops kong routes create --name my-route --service my-api --path /api --method GET
            ops kong routes create --service my-api --host api.example.com
            ops kong routes create --service my-api --path /test --data-plane-only
        """
        if not service:
            console.print("[red]Error:[/red] --service is required")
            raise typer.Exit(1)

        if not any([paths, methods, hosts]):
            console.print(
                "[red]Error:[/red] At least one of --path, --method, or --host is required"
            )
            raise typer.Exit(1)

        try:
            # Build route data, only including non-None values
            route_data: dict[str, Any] = {
                "service": KongEntityReference.from_id_or_name(service),
            }
            if name is not None:
                route_data["name"] = name
            if paths is not None:
                route_data["paths"] = paths
            if methods is not None:
                route_data["methods"] = methods
            if hosts is not None:
                route_data["hosts"] = hosts
            if protocols is not None:
                route_data["protocols"] = protocols
            if strip_path is not None:
                route_data["strip_path"] = strip_path
            if preserve_host is not None:
                route_data["preserve_host"] = preserve_host
            if regex_priority is not None:
                route_data["regex_priority"] = regex_priority
            if tags is not None:
                route_data["tags"] = tags

            route = Route(**route_data)

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.create(route, data_plane_only=data_plane_only)

                formatter = get_formatter(output, console)
                console.print("[green]Route created successfully[/green]\n")
                title = f"Route: {result.gateway_result.name or result.gateway_result.id}"
                formatter.format_entity(result.gateway_result, title=title)

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("\n[green]✓ Synced to Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"\n[yellow]⚠ Konnect sync failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("\n[dim]Konnect sync skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("\n[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager = get_manager()
                created = manager.create(route)

                formatter = get_formatter(output, console)
                console.print("[green]Route created successfully[/green]\n")
                title = f"Route: {created.name or created.id}"
                formatter.format_entity(created, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @routes_app.command("update")
    def update_route(
        name_or_id: Annotated[str, typer.Argument(help="Route name or ID to update")],
        name: Annotated[
            str | None,
            typer.Option("--name", "-n", help="New route name"),
        ] = None,
        service: Annotated[
            str | None,
            typer.Option("--service", "-s", help="New service ID or name"),
        ] = None,
        paths: Annotated[
            list[str] | None,
            typer.Option("--path", "-p", help="Paths (replaces existing)"),
        ] = None,
        methods: Annotated[
            list[str] | None,
            typer.Option("--method", "-m", help="Methods (replaces existing)"),
        ] = None,
        hosts: Annotated[
            list[str] | None,
            typer.Option("--host", "-H", help="Hosts (replaces existing)"),
        ] = None,
        protocols: Annotated[
            list[str] | None,
            typer.Option("--protocol", help="Protocols"),
        ] = None,
        strip_path: Annotated[
            bool | None,
            typer.Option("--strip-path/--no-strip-path", help="Strip matched path prefix"),
        ] = None,
        preserve_host: Annotated[
            bool | None,
            typer.Option("--preserve-host/--no-preserve-host", help="Preserve host header"),
        ] = None,
        regex_priority: Annotated[
            int | None,
            typer.Option("--regex-priority", help="Priority for regex matching"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (replaces existing)"),
        ] = None,
        data_plane_only: DataPlaneOnlyOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update an existing route.

        Only specified fields will be updated. By default, updates the route
        in both Gateway and Konnect (if configured).

        Examples:
            ops kong routes update my-route --path /api/v2
            ops kong routes update my-route --no-strip-path
            ops kong routes update my-route --method GET --method POST
            ops kong routes update my-route --path /test --data-plane-only
        """
        # Build update data from non-None values
        update_data: dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name
        if service is not None:
            update_data["service"] = KongEntityReference.from_id_or_name(service)
        if paths is not None:
            update_data["paths"] = paths
        if methods is not None:
            update_data["methods"] = methods
        if hosts is not None:
            update_data["hosts"] = hosts
        if protocols is not None:
            update_data["protocols"] = protocols
        if strip_path is not None:
            update_data["strip_path"] = strip_path
        if preserve_host is not None:
            update_data["preserve_host"] = preserve_host
        if regex_priority is not None:
            update_data["regex_priority"] = regex_priority
        if tags is not None:
            update_data["tags"] = tags

        if not update_data:
            console.print("[yellow]No updates specified[/yellow]")
            raise typer.Exit(0)

        try:
            route = Route(**update_data)

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.update(name_or_id, route, data_plane_only=data_plane_only)

                formatter = get_formatter(output, console)
                console.print("[green]Route updated successfully[/green]\n")
                title = f"Route: {result.gateway_result.name or result.gateway_result.id}"
                formatter.format_entity(result.gateway_result, title=title)

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("\n[green]✓ Synced to Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"\n[yellow]⚠ Konnect sync failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("\n[dim]Konnect sync skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("\n[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager = get_manager()
                updated = manager.update(name_or_id, route)

                formatter = get_formatter(output, console)
                console.print("[green]Route updated successfully[/green]\n")
                title = f"Route: {updated.name or updated.id}"
                formatter.format_entity(updated, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @routes_app.command("delete")
    def delete_route(
        name_or_id: Annotated[str, typer.Argument(help="Route name or ID to delete")],
        force: ForceOption = False,
        data_plane_only: DataPlaneOnlyOption = False,
    ) -> None:
        """Delete a route.

        By default, deletes from both Gateway and Konnect (if configured).

        Examples:
            ops kong routes delete my-route
            ops kong routes delete my-route --force
            ops kong routes delete my-route --data-plane-only
        """
        try:
            manager = get_manager()

            # Verify route exists
            route = manager.get(name_or_id)
            display_name = route.name or route.id or name_or_id

            if not force and not confirm_delete("route", display_name):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.delete(name_or_id, data_plane_only=data_plane_only)

                console.print(f"[green]Route '{display_name}' deleted successfully[/green]")

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("[green]✓ Deleted from Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"[yellow]⚠ Konnect delete failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("[dim]Konnect delete skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager.delete(name_or_id)
                console.print(f"[green]Route '{display_name}' deleted successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(routes_app, name="routes")
