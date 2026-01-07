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
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


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
) -> None:
    """Register plugin commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_manager: Factory function that returns a KongPluginManager instance.
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
    ) -> None:
        """List enabled plugins.

        Can filter by scope (service, route, consumer) or plugin name.

        Examples:
            ops kong plugins list
            ops kong plugins list --service my-api
            ops kong plugins list --name rate-limiting
            ops kong plugins list --output json
        """
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
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable a plugin.

        If no scope is specified, the plugin is enabled globally.

        Examples:
            ops kong plugins enable key-auth --service my-api
            ops kong plugins enable rate-limiting --config minute=100 --config hour=5000
            ops kong plugins enable jwt --route my-route
            ops kong plugins enable acl --service my-api --config-json '{"allow": ["admin"]}'
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
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a plugin's configuration.

        Examples:
            ops kong plugins update abc-123 --config minute=200
            ops kong plugins update abc-123 --disabled
            ops kong plugins update abc-123 --config-json '{"minute": 500}'
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

        except KongAPIError as e:
            handle_kong_error(e)

    @plugins_app.command("disable")
    def disable_plugin(
        plugin_id: Annotated[str, typer.Argument(help="Plugin ID to disable")],
        force: ForceOption = False,
    ) -> None:
        """Disable (delete) a plugin.

        Examples:
            ops kong plugins disable abc-123
            ops kong plugins disable abc-123 --force
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
