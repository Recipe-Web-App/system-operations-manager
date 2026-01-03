"""CLI commands for Kong Services.

This module provides commands for managing Kong Service entities:
- list: List all services
- get: Get service details
- create: Create a new service
- update: Update an existing service
- delete: Delete a service
- routes: List routes associated with a service
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    LimitOption,
    OffsetOption,
    OutputOption,
    TagsOption,
    confirm_delete,
    console,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.service_manager import ServiceManager


# Column definitions for service listings
SERVICE_COLUMNS = [
    ("name", "Name"),
    ("id", "ID"),
    ("host", "Host"),
    ("port", "Port"),
    ("protocol", "Protocol"),
    ("enabled", "Enabled"),
]


def register_service_commands(
    app: typer.Typer,
    get_manager: Callable[[], ServiceManager],
) -> None:
    """Register service commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_manager: Factory function that returns a ServiceManager instance.
    """
    services_app = typer.Typer(
        name="services",
        help="Manage Kong Services",
        no_args_is_help=True,
    )

    @services_app.command("list")
    def list_services(
        output: OutputOption = OutputFormat.TABLE,
        tags: TagsOption = None,
        limit: LimitOption = None,
        offset: OffsetOption = None,
    ) -> None:
        """List all services.

        Examples:
            ops kong services list
            ops kong services list --tag production
            ops kong services list --output json
            ops kong services list --limit 10
        """
        try:
            manager = get_manager()
            services, next_offset = manager.list(tags=tags, limit=limit, offset=offset)

            formatter = get_formatter(output, console)
            formatter.format_list(services, SERVICE_COLUMNS, title="Kong Services")

            if next_offset:
                console.print(f"\n[dim]More results available. Use --offset {next_offset}[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @services_app.command("get")
    def get_service(
        name_or_id: Annotated[str, typer.Argument(help="Service name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a service by name or ID.

        Examples:
            ops kong services get my-service
            ops kong services get 8c5b0c0e-..."
            ops kong services get my-service --output json
        """
        try:
            manager = get_manager()
            service = manager.get(name_or_id)

            formatter = get_formatter(output, console)
            title = f"Service: {service.name or service.id}"
            formatter.format_entity(service, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @services_app.command("create")
    def create_service(
        name: Annotated[
            str | None,
            typer.Option("--name", "-n", help="Service name (unique)"),
        ] = None,
        host: Annotated[
            str | None,
            typer.Option("--host", help="Upstream host"),
        ] = None,
        port: Annotated[
            int,
            typer.Option("--port", "-p", help="Upstream port", min=1, max=65535),
        ] = 80,
        protocol: Annotated[
            str,
            typer.Option("--protocol", help="Protocol (http, https, grpc, etc.)"),
        ] = "http",
        path: Annotated[
            str | None,
            typer.Option("--path", help="Path prefix for requests"),
        ] = None,
        url: Annotated[
            str | None,
            typer.Option("--url", help="Full URL shorthand (protocol://host:port/path)"),
        ] = None,
        retries: Annotated[
            int | None,
            typer.Option("--retries", help="Number of retries on failure"),
        ] = None,
        connect_timeout: Annotated[
            int | None,
            typer.Option("--connect-timeout", help="Connection timeout in ms"),
        ] = None,
        write_timeout: Annotated[
            int | None,
            typer.Option("--write-timeout", help="Write timeout in ms"),
        ] = None,
        read_timeout: Annotated[
            int | None,
            typer.Option("--read-timeout", help="Read timeout in ms"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (can be repeated)"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new service.

        Either --host or --url must be provided.

        Examples:
            ops kong services create --name my-api --host api.example.com
            ops kong services create --name my-api --url http://api.example.com:8080
            ops kong services create --host api.example.com --port 8080 --tag production
        """
        if not url and not host:
            console.print("[red]Error:[/red] Either --host or --url is required")
            raise typer.Exit(1)

        try:
            manager = get_manager()

            # Build service data, only including non-None values
            service_data: dict[str, Any] = {}
            if name is not None:
                service_data["name"] = name
            if host is not None:
                service_data["host"] = host
            if port is not None:
                service_data["port"] = port
            if protocol is not None:
                service_data["protocol"] = protocol
            if path is not None:
                service_data["path"] = path
            if url is not None:
                service_data["url"] = url
            if retries is not None:
                service_data["retries"] = retries
            if connect_timeout is not None:
                service_data["connect_timeout"] = connect_timeout
            if write_timeout is not None:
                service_data["write_timeout"] = write_timeout
            if read_timeout is not None:
                service_data["read_timeout"] = read_timeout
            if tags is not None:
                service_data["tags"] = tags

            service = Service(**service_data)

            created = manager.create(service)

            formatter = get_formatter(output, console)
            console.print("[green]Service created successfully[/green]\n")
            title = f"Service: {created.name or created.id}"
            formatter.format_entity(created, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @services_app.command("update")
    def update_service(
        name_or_id: Annotated[str, typer.Argument(help="Service name or ID to update")],
        name: Annotated[
            str | None,
            typer.Option("--name", "-n", help="New service name"),
        ] = None,
        host: Annotated[
            str | None,
            typer.Option("--host", help="Upstream host"),
        ] = None,
        port: Annotated[
            int | None,
            typer.Option("--port", "-p", help="Upstream port", min=1, max=65535),
        ] = None,
        protocol: Annotated[
            str | None,
            typer.Option("--protocol", help="Protocol"),
        ] = None,
        path: Annotated[
            str | None,
            typer.Option("--path", help="Path prefix"),
        ] = None,
        retries: Annotated[
            int | None,
            typer.Option("--retries", help="Number of retries"),
        ] = None,
        connect_timeout: Annotated[
            int | None,
            typer.Option("--connect-timeout", help="Connection timeout in ms"),
        ] = None,
        write_timeout: Annotated[
            int | None,
            typer.Option("--write-timeout", help="Write timeout in ms"),
        ] = None,
        read_timeout: Annotated[
            int | None,
            typer.Option("--read-timeout", help="Read timeout in ms"),
        ] = None,
        enabled: Annotated[
            bool | None,
            typer.Option("--enabled/--disabled", help="Enable or disable service"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (replaces existing)"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update an existing service.

        Only specified fields will be updated.

        Examples:
            ops kong services update my-api --host new-api.example.com
            ops kong services update my-api --disabled
            ops kong services update my-api --port 8080 --tag staging
        """
        # Build update data from non-None values
        update_data: dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name
        if host is not None:
            update_data["host"] = host
        if port is not None:
            update_data["port"] = port
        if protocol is not None:
            update_data["protocol"] = protocol
        if path is not None:
            update_data["path"] = path
        if retries is not None:
            update_data["retries"] = retries
        if connect_timeout is not None:
            update_data["connect_timeout"] = connect_timeout
        if write_timeout is not None:
            update_data["write_timeout"] = write_timeout
        if read_timeout is not None:
            update_data["read_timeout"] = read_timeout
        if enabled is not None:
            update_data["enabled"] = enabled
        if tags is not None:
            update_data["tags"] = tags

        if not update_data:
            console.print("[yellow]No updates specified[/yellow]")
            raise typer.Exit(0)

        try:
            manager = get_manager()
            service = Service(**update_data)
            updated = manager.update(name_or_id, service)

            formatter = get_formatter(output, console)
            console.print("[green]Service updated successfully[/green]\n")
            title = f"Service: {updated.name or updated.id}"
            formatter.format_entity(updated, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @services_app.command("delete")
    def delete_service(
        name_or_id: Annotated[str, typer.Argument(help="Service name or ID to delete")],
        force: ForceOption = False,
    ) -> None:
        """Delete a service.

        This will fail if the service has associated routes. Delete the
        routes first, or use --force to skip confirmation.

        Examples:
            ops kong services delete my-api
            ops kong services delete my-api --force
        """
        try:
            manager = get_manager()

            # Verify service exists
            service = manager.get(name_or_id)
            display_name = service.name or service.id or name_or_id

            if not force and not confirm_delete("service", display_name):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.delete(name_or_id)
            console.print(f"[green]Service '{display_name}' deleted successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @services_app.command("routes")
    def list_service_routes(
        name_or_id: Annotated[str, typer.Argument(help="Service name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List routes associated with a service.

        Examples:
            ops kong services routes my-api
            ops kong services routes my-api --output json
        """
        # Import route columns from routes module when available
        route_columns = [
            ("name", "Name"),
            ("id", "ID"),
            ("paths", "Paths"),
            ("methods", "Methods"),
            ("hosts", "Hosts"),
        ]

        try:
            manager = get_manager()
            routes = manager.get_routes(name_or_id)

            formatter = get_formatter(output, console)
            formatter.format_list(
                routes,
                route_columns,
                title=f"Routes for Service: {name_or_id}",
            )

        except KongAPIError as e:
            handle_kong_error(e)

    @services_app.command("enable")
    def enable_service(
        name_or_id: Annotated[str, typer.Argument(help="Service name or ID")],
    ) -> None:
        """Enable a service.

        Examples:
            ops kong services enable my-api
        """
        try:
            manager = get_manager()
            service = manager.enable(name_or_id)
            display_name = service.name or service.id
            console.print(f"[green]Service '{display_name}' enabled[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @services_app.command("disable")
    def disable_service(
        name_or_id: Annotated[str, typer.Argument(help="Service name or ID")],
    ) -> None:
        """Disable a service.

        Disabled services will not accept traffic.

        Examples:
            ops kong services disable my-api
        """
        try:
            manager = get_manager()
            service = manager.disable(name_or_id)
            display_name = service.name or service.id
            console.print(f"[yellow]Service '{display_name}' disabled[/yellow]")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(services_app, name="services")
