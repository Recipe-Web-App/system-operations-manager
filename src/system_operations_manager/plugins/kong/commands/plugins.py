"""CLI commands for Kong Plugins.

This module provides commands for managing Kong Plugin entities:
- list: List enabled plugins
- available: List available plugin types
- get: Get plugin details
- enable: Enable a plugin
- update: Update plugin configuration
- disable: Disable a plugin
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.base import (
    ConsumerFilterOption,
    DataPlaneOnlyOption,
    ForceOption,
    LimitOption,
    OffsetOption,
    OutputOption,
    RouteFilterOption,
    ServiceFilterOption,
    TagsOption,
    confirm_delete,
    console,
    handle_kong_error,
    parse_config_options,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.dual_write import DualWriteService
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager
    from system_operations_manager.services.kong.unified_query import UnifiedQueryService


# Column definitions for plugin listings
PLUGIN_COLUMNS = [
    ("name", "Name"),
    ("id", "ID"),
    ("service", "Service"),
    ("route", "Route"),
    ("consumer", "Consumer"),
    ("enabled", "Enabled"),
]


def register_plugin_commands(
    app: typer.Typer,
    get_manager: Callable[[], KongPluginManager],
    get_unified_query_service: Callable[[], UnifiedQueryService | None] | None = None,
    get_dual_write_service: Callable[[], DualWriteService[Any]] | None = None,
) -> None:
    """Register plugin commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_manager: Factory function that returns a KongPluginManager instance.
        get_unified_query_service: Optional factory that returns a UnifiedQueryService
            for querying both Gateway and Konnect.
        get_dual_write_service: Optional factory that returns a DualWriteService
            for writing to both Gateway and Konnect.
    """
    plugins_app = typer.Typer(
        name="plugins",
        help="Manage Kong Plugins",
        no_args_is_help=True,
    )

    @plugins_app.command("list")
    def list_plugins(
        service: ServiceFilterOption = None,
        route: RouteFilterOption = None,
        consumer: ConsumerFilterOption = None,
        name: Annotated[
            str | None,
            typer.Option("--name", "-n", help="Filter by plugin name"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
        tags: TagsOption = None,
        limit: LimitOption = None,
        offset: OffsetOption = None,
        source: Annotated[
            str | None,
            typer.Option(
                "--source",
                "-s",
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
        """List enabled plugins.

        Can filter by scope (service, route, consumer) or plugin name.
        When Konnect is configured, shows plugins from both Gateway and Konnect.

        Examples:
            ops kong plugins list
            ops kong plugins list --service my-api
            ops kong plugins list --name rate-limiting
            ops kong plugins list --output json
            ops kong plugins list --source gateway
            ops kong plugins list --compare
        """
        formatter = get_formatter(output, console)

        # Try unified query first if available and no scope filter
        unified_service = get_unified_query_service() if get_unified_query_service else None

        if unified_service is not None and not service and not route and not consumer:
            try:
                results = unified_service.list_plugins(tags=tags)

                # Filter by source if specified
                if source:
                    results = results.filter_by_source(source)

                # Filter by name if specified
                if name:
                    results.entities = [e for e in results.entities if e.entity.name == name]

                title = "Kong Plugins"
                if name:
                    title = f"{title} (name={name})"

                formatter.format_unified_list(
                    results,
                    PLUGIN_COLUMNS,
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

            # Determine which list method to use based on filters
            if service:
                plugins = manager.list_by_service(service)
                title = f"Plugins for Service: {service}"
            elif route:
                plugins = manager.list_by_route(route)
                title = f"Plugins for Route: {route}"
            elif consumer:
                plugins = manager.list_by_consumer(consumer)
                title = f"Plugins for Consumer: {consumer}"
            else:
                all_plugins, next_offset = manager.list(tags=tags, limit=limit, offset=offset)
                plugins = all_plugins
                title = "Kong Plugins"

                if next_offset:
                    console.print(
                        f"\n[dim]More results available. Use --offset {next_offset}[/dim]"
                    )

            # Filter by name if specified
            if name:
                plugins = [p for p in plugins if p.name == name]
                title = f"{title} (name={name})"

            formatter = get_formatter(output, console)
            formatter.format_list(plugins, PLUGIN_COLUMNS, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @plugins_app.command("available")
    def list_available_plugins(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List available plugin types.

        Shows all plugins that can be enabled in this Kong cluster.

        Examples:
            ops kong plugins available
            ops kong plugins available --output json
        """
        try:
            manager = get_manager()
            available = manager.list_available()

            if output == OutputFormat.TABLE:
                from system_operations_manager.cli.output import Table

                table = Table(title="Available Kong Plugins")
                table.add_column("Name", style="cyan")
                table.add_column("Version")
                table.add_column("Priority")

                for name in sorted(available.keys()):
                    plugin = available[name]
                    table.add_row(
                        name,
                        plugin.version or "-",
                        str(plugin.priority) if plugin.priority else "-",
                    )

                console.print(table)
                console.print(f"\n[dim]Total: {len(available)} plugins[/dim]")
            else:
                formatter = get_formatter(output, console)
                data = {
                    name: plugin.model_dump(exclude_none=True) for name, plugin in available.items()
                }
                formatter.format_dict(data, title="Available Plugins")

        except KongAPIError as e:
            handle_kong_error(e)

    @plugins_app.command("get")
    def get_plugin(
        plugin_id: Annotated[str, typer.Argument(help="Plugin ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a plugin by ID.

        Examples:
            ops kong plugins get abc-123
            ops kong plugins get abc-123 --output json
        """
        try:
            manager = get_manager()
            plugin = manager.get(plugin_id)

            formatter = get_formatter(output, console)
            title = f"Plugin: {plugin.name} ({plugin.id})"
            formatter.format_entity(plugin, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @plugins_app.command("enable")
    def enable_plugin(
        plugin_name: Annotated[
            str, typer.Argument(help="Plugin name (e.g., 'rate-limiting', 'key-auth')")
        ],
        service: Annotated[
            str | None,
            typer.Option("--service", "-s", help="Service to scope to"),
        ] = None,
        route: Annotated[
            str | None,
            typer.Option("--route", "-r", help="Route to scope to"),
        ] = None,
        consumer: Annotated[
            str | None,
            typer.Option("--consumer", "-c", help="Consumer to scope to"),
        ] = None,
        config: Annotated[
            list[str] | None,
            typer.Option(
                "--config",
                "-C",
                help="Config as key=value (can be repeated)",
            ),
        ] = None,
        config_json: Annotated[
            str | None,
            typer.Option(
                "--config-json",
                help="Config as JSON string",
            ),
        ] = None,
        protocols: Annotated[
            list[str] | None,
            typer.Option("--protocol", help="Protocols (can be repeated)"),
        ] = None,
        instance_name: Annotated[
            str | None,
            typer.Option("--instance-name", help="Unique instance name"),
        ] = None,
        data_plane_only: DataPlaneOnlyOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable a plugin.

        If no scope is specified, the plugin is enabled globally. By default,
        enables the plugin in both Gateway and Konnect (if configured).

        Examples:
            ops kong plugins enable key-auth --service my-api
            ops kong plugins enable rate-limiting --config minute=100 --config hour=5000
            ops kong plugins enable jwt --route my-route
            ops kong plugins enable acl --service my-api --config-json '{"allow": ["admin"]}'
            ops kong plugins enable key-auth --service my-api --data-plane-only
        """
        # Build config
        plugin_config: dict[str, Any] = {}

        if config:
            plugin_config.update(parse_config_options(config))

        if config_json:
            try:
                json_data = json.loads(config_json)
                plugin_config.update(json_data)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error:[/red] Invalid JSON: {e}")
                raise typer.Exit(1) from None

        try:
            manager = get_manager()
            plugin = manager.enable(
                plugin_name,
                service=service,
                route=route,
                consumer=consumer,
                config=plugin_config if plugin_config else None,
                protocols=protocols,
                instance_name=instance_name,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Plugin enabled successfully[/green]\n")
            formatter.format_entity(plugin, title=f"Plugin: {plugin.name}")

            # Handle Konnect sync for dual-write
            if get_dual_write_service is not None and not data_plane_only:
                dual_write = get_dual_write_service()
                if dual_write.konnect_configured and dual_write._konnect is not None:
                    try:
                        dual_write._konnect.enable(
                            plugin_name,
                            service=service,
                            route=route,
                            consumer=consumer,
                            config=plugin_config if plugin_config else None,
                            protocols=protocols,
                            instance_name=instance_name,
                        )
                        console.print("\n[green]✓ Synced to Konnect[/green]")
                    except Exception as e:
                        console.print(f"\n[yellow]⚠ Konnect sync failed: {e}[/yellow]")
                        console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                else:
                    console.print("\n[dim]Konnect not configured[/dim]")
            elif data_plane_only:
                console.print("\n[dim]Konnect sync skipped (--data-plane-only)[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @plugins_app.command("update")
    def update_plugin(
        plugin_id: Annotated[str, typer.Argument(help="Plugin ID to update")],
        config: Annotated[
            list[str] | None,
            typer.Option(
                "--config",
                "-C",
                help="Config as key=value (can be repeated)",
            ),
        ] = None,
        config_json: Annotated[
            str | None,
            typer.Option(
                "--config-json",
                help="Config as JSON string",
            ),
        ] = None,
        enabled: Annotated[
            bool | None,
            typer.Option("--enabled/--disabled", help="Enable or disable"),
        ] = None,
        data_plane_only: DataPlaneOnlyOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a plugin's configuration.

        By default, updates the plugin in both Gateway and Konnect (if configured).

        Examples:
            ops kong plugins update abc-123 --config minute=200
            ops kong plugins update abc-123 --disabled
            ops kong plugins update abc-123 --config-json '{"minute": 500}'
            ops kong plugins update abc-123 --config minute=200 --data-plane-only
        """
        # Build config
        plugin_config: dict[str, Any] = {}

        if config:
            plugin_config.update(parse_config_options(config))

        if config_json:
            try:
                json_data = json.loads(config_json)
                plugin_config.update(json_data)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error:[/red] Invalid JSON: {e}")
                raise typer.Exit(1) from None

        if not plugin_config and enabled is None:
            console.print("[yellow]No updates specified[/yellow]")
            raise typer.Exit(0)

        try:
            manager = get_manager()

            if plugin_config:
                plugin = manager.update_config(plugin_id, plugin_config, enabled)
            else:
                # enabled must be set here (we exited early if both were None)
                assert enabled is not None
                plugin = manager.toggle(plugin_id, enabled)

            formatter = get_formatter(output, console)
            console.print("[green]Plugin updated successfully[/green]\n")
            formatter.format_entity(plugin, title=f"Plugin: {plugin.name}")

            # Handle Konnect sync for dual-write
            if get_dual_write_service is not None and not data_plane_only:
                dual_write = get_dual_write_service()
                if dual_write.konnect_configured and dual_write._konnect is not None:
                    try:
                        if plugin_config:
                            dual_write._konnect.update_config(plugin_id, plugin_config, enabled)
                        else:
                            dual_write._konnect.toggle(plugin_id, enabled)
                        console.print("\n[green]✓ Synced to Konnect[/green]")
                    except Exception as e:
                        console.print(f"\n[yellow]⚠ Konnect sync failed: {e}[/yellow]")
                        console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                else:
                    console.print("\n[dim]Konnect not configured[/dim]")
            elif data_plane_only:
                console.print("\n[dim]Konnect sync skipped (--data-plane-only)[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @plugins_app.command("disable")
    def disable_plugin(
        plugin_id: Annotated[str, typer.Argument(help="Plugin ID to disable")],
        force: ForceOption = False,
        data_plane_only: DataPlaneOnlyOption = False,
    ) -> None:
        """Disable (delete) a plugin.

        By default, disables the plugin in both Gateway and Konnect (if configured).

        Examples:
            ops kong plugins disable abc-123
            ops kong plugins disable abc-123 --force
            ops kong plugins disable abc-123 --data-plane-only
        """
        try:
            manager = get_manager()

            # Get plugin info first
            plugin = manager.get(plugin_id)

            if not force and not confirm_delete(f"plugin '{plugin.name}'", plugin_id):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(f"[green]Plugin '{plugin.name}' disabled successfully[/green]")

            # Handle Konnect sync for dual-write
            if get_dual_write_service is not None and not data_plane_only:
                dual_write = get_dual_write_service()
                if dual_write.konnect_configured and dual_write._konnect is not None:
                    try:
                        dual_write._konnect.disable(plugin_id)
                        console.print("[green]✓ Deleted from Konnect[/green]")
                    except Exception as e:
                        console.print(f"[yellow]⚠ Konnect delete failed: {e}[/yellow]")
                        console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                else:
                    console.print("[dim]Konnect not configured[/dim]")
            elif data_plane_only:
                console.print("[dim]Konnect delete skipped (--data-plane-only)[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @plugins_app.command("schema")
    def show_plugin_schema(
        plugin_name: Annotated[str, typer.Argument(help="Plugin name")],
        output: OutputOption = OutputFormat.JSON,
    ) -> None:
        """Show configuration schema for a plugin.

        Displays the available configuration options for a plugin type.

        Examples:
            ops kong plugins schema rate-limiting
            ops kong plugins schema key-auth --output yaml
        """
        try:
            manager = get_manager()
            schema = manager.get_schema(plugin_name)

            formatter = get_formatter(output, console)
            if schema.fields:
                formatter.format_dict(
                    {"name": plugin_name, "fields": schema.fields},
                    title=f"Schema: {plugin_name}",
                )
            else:
                console.print(f"[yellow]No schema found for plugin '{plugin_name}'[/yellow]")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(plugins_app, name="plugins")
