"""IP restriction commands for Kong Gateway.

Provides CLI commands for configuring IP-based access control
using Kong's ip-restriction plugin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.security.base import (
    OutputOption,
    RouteScopeOption,
    ServiceScopeOption,
    console,
    get_formatter,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat

if TYPE_CHECKING:
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


def register_ip_restriction_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register IP restriction subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
    """
    ip_app = typer.Typer(
        name="ip-restriction",
        help="IP restriction management",
        no_args_is_help=True,
    )

    @ip_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        allow: Annotated[
            list[str] | None,
            typer.Option(
                "--allow",
                "-a",
                help="Allowed IP addresses or CIDR ranges (can be repeated)",
            ),
        ] = None,
        deny: Annotated[
            list[str] | None,
            typer.Option(
                "--deny",
                "-d",
                help="Denied IP addresses or CIDR ranges (can be repeated)",
            ),
        ] = None,
        status: Annotated[
            int | None,
            typer.Option(
                "--status",
                help="HTTP status code to return when denied (default: 403)",
            ),
        ] = None,
        message: Annotated[
            str | None,
            typer.Option(
                "--message",
                "-m",
                help="Custom message to return when denied",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable IP restriction plugin on a service or route.

        Configure IP-based access control by specifying allowed or denied
        IP addresses and CIDR ranges. Use either --allow or --deny, not both.

        Examples:
            ops kong security ip-restriction enable --service my-api --allow 10.0.0.0/8
            ops kong security ip-restriction enable --route admin-route --deny 203.0.113.0/24
            ops kong security ip-restriction enable --service my-api --allow 192.168.1.100 --status 403 --message "Access denied"
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
        config: dict[str, Any] = {}
        if allow:
            config["allow"] = allow
        if deny:
            config["deny"] = deny
        if status is not None:
            config["status"] = status
        if message is not None:
            config["message"] = message

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "ip-restriction",
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]IP restriction plugin enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="IP Restriction Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(ip_app, name="ip-restriction")
