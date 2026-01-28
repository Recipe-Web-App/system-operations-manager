"""ACL commands for Kong Gateway.

Provides CLI commands for configuring Access Control Lists
using Kong's acl plugin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.security.base import (
    ACL_COLUMNS,
    ForceOption,
    OutputOption,
    RouteScopeOption,
    ServiceScopeOption,
    console,
    get_formatter,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat

if TYPE_CHECKING:
    from system_operations_manager.services.kong.consumer_manager import ConsumerManager
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


def register_acl_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
    get_consumer_manager: Callable[[], ConsumerManager],
) -> None:
    """Register ACL subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
        get_consumer_manager: Factory function that returns a ConsumerManager instance.
    """
    acl_app = typer.Typer(
        name="acl",
        help="Access Control List management",
        no_args_is_help=True,
    )

    @acl_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        allow: Annotated[
            list[str] | None,
            typer.Option(
                "--allow",
                "-a",
                help="Allowed ACL groups (can be repeated)",
            ),
        ] = None,
        deny: Annotated[
            list[str] | None,
            typer.Option(
                "--deny",
                "-d",
                help="Denied ACL groups (can be repeated)",
            ),
        ] = None,
        hide_groups_header: Annotated[
            bool,
            typer.Option(
                "--hide-groups-header/--show-groups-header",
                help="Hide X-Consumer-Groups header from upstream",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable ACL plugin on a service or route.

        Configure access control based on consumer group membership.
        Use either --allow or --deny, not both.

        Examples:
            ops kong security acl enable --service my-api --allow admin --allow premium
            ops kong security acl enable --route internal --deny blocked-users
            ops kong security acl enable --service my-api --allow admins --hide-groups-header
        """
        if not service and not route:
            console.print("[red]Error:[/red] Either --service or --route is required")
            raise typer.Exit(1)

        if allow and deny:
            console.print("[red]Error:[/red] Cannot use both --allow and --deny. Choose one.")
            raise typer.Exit(1)

        if not allow and not deny:
            console.print("[red]Error:[/red] Either --allow or --deny is required")
            raise typer.Exit(1)

        # Build plugin configuration
        config: dict[str, Any] = {
            "hide_groups_header": hide_groups_header,
        }
        if allow:
            config["allow"] = allow
        if deny:
            config["deny"] = deny

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "acl",
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]ACL plugin enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="ACL Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @acl_app.command("add-group")
    def add_group(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        group: Annotated[str, typer.Argument(help="ACL group name")],
        tags: Annotated[
            list[str] | None,
            typer.Option(
                "--tag",
                "-t",
                help="Tags (can be repeated)",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Add a consumer to an ACL group.

        Examples:
            ops kong security acl add-group my-user admin-group
            ops kong security acl add-group my-user premium-users --tag production
        """
        try:
            manager = get_consumer_manager()
            acl = manager.add_to_acl_group(consumer, group, tags)

            formatter = get_formatter(output, console)
            console.print(f"[green]Consumer added to group '{group}' successfully[/green]\n")
            formatter.format_entity(acl, title="ACL Membership")

        except KongAPIError as e:
            handle_kong_error(e)

    @acl_app.command("remove-group")
    def remove_group(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        acl_id: Annotated[str, typer.Argument(help="ACL entry ID to remove")],
        force: ForceOption = False,
    ) -> None:
        """Remove a consumer from an ACL group.

        Examples:
            ops kong security acl remove-group my-user abc-123-acl-id
            ops kong security acl remove-group my-user abc-123-acl-id --force
        """
        try:
            manager = get_consumer_manager()

            if not force and not typer.confirm(
                f"Are you sure you want to remove ACL membership '{acl_id}'?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.remove_from_acl_group(consumer, acl_id)
            console.print("[green]Consumer removed from ACL group successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @acl_app.command("list-groups")
    def list_groups(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ACL groups for a consumer.

        Examples:
            ops kong security acl list-groups my-user
            ops kong security acl list-groups my-user --output json
        """
        try:
            manager = get_consumer_manager()
            groups = manager.list_acl_groups(consumer)

            formatter = get_formatter(output, console)
            formatter.format_list(
                groups,
                ACL_COLUMNS,
                title=f"ACL Groups for: {consumer}",
            )

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(acl_app, name="acl")
