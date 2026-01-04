"""CORS commands for Kong Gateway.

Provides CLI commands for configuring Cross-Origin Resource Sharing
using Kong's cors plugin.
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


def register_cors_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register CORS subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
    """
    cors_app = typer.Typer(
        name="cors",
        help="CORS configuration",
        no_args_is_help=True,
    )

    @cors_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        origins: Annotated[
            list[str] | None,
            typer.Option(
                "--origin",
                "-O",
                help="Allowed origins (can be repeated). Use '*' for all.",
            ),
        ] = None,
        methods: Annotated[
            list[str] | None,
            typer.Option(
                "--method",
                "-M",
                help="Allowed HTTP methods (can be repeated)",
            ),
        ] = None,
        headers: Annotated[
            list[str] | None,
            typer.Option(
                "--header",
                "-H",
                help="Allowed request headers (can be repeated)",
            ),
        ] = None,
        exposed_headers: Annotated[
            list[str] | None,
            typer.Option(
                "--exposed-header",
                "-E",
                help="Headers exposed to the browser (can be repeated)",
            ),
        ] = None,
        credentials: Annotated[
            bool,
            typer.Option(
                "--credentials/--no-credentials",
                help="Allow credentials (cookies, authorization headers)",
            ),
        ] = False,
        max_age: Annotated[
            int | None,
            typer.Option(
                "--max-age",
                help="Preflight response cache time in seconds",
            ),
        ] = None,
        preflight_continue: Annotated[
            bool,
            typer.Option(
                "--preflight-continue/--no-preflight-continue",
                help="Proxy OPTIONS requests to upstream",
            ),
        ] = False,
        private_network: Annotated[
            bool,
            typer.Option(
                "--private-network/--no-private-network",
                help="Allow private network access",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable CORS plugin on a service or route.

        Configure Cross-Origin Resource Sharing to allow browsers
        to make requests from different origins.

        Examples:
            ops kong security cors enable --service my-api --origin "https://example.com"
            ops kong security cors enable --service my-api --origin "*" --credentials
            ops kong security cors enable --service my-api \\
                --origin "https://app.example.com" \\
                --method GET --method POST --method PUT --method DELETE \\
                --header Accept --header Authorization --header Content-Type \\
                --credentials --max-age 3600
        """
        if not service and not route:
            console.print("[red]Error:[/red] Either --service or --route is required")
            raise typer.Exit(1)

        # Build plugin configuration
        config: dict[str, Any] = {
            "credentials": credentials,
            "preflight_continue": preflight_continue,
            "private_network": private_network,
        }

        if origins:
            config["origins"] = origins
        if methods:
            config["methods"] = methods
        if headers:
            config["headers"] = headers
        if exposed_headers:
            config["exposed_headers"] = exposed_headers
        if max_age is not None:
            config["max_age"] = max_age

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "cors",
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]CORS plugin enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="CORS Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(cors_app, name="cors")
