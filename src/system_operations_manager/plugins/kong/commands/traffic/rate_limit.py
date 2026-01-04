"""Rate limiting commands for Kong Gateway.

Provides CLI commands for configuring request rate limiting
using Kong's rate-limiting plugin.
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
PLUGIN_NAME = "rate-limiting"

# Valid policy options
POLICIES = ["local", "cluster", "redis"]

# Valid limit_by options
LIMIT_BY_OPTIONS = ["consumer", "credential", "ip", "service", "header", "path"]


def register_rate_limit_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register rate limiting subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
    """
    rate_limit_app = typer.Typer(
        name="rate-limit",
        help="Rate limiting configuration",
        no_args_is_help=True,
    )

    @rate_limit_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        second: Annotated[
            int | None,
            typer.Option(
                "--second",
                help="Maximum requests per second",
            ),
        ] = None,
        minute: Annotated[
            int | None,
            typer.Option(
                "--minute",
                help="Maximum requests per minute",
            ),
        ] = None,
        hour: Annotated[
            int | None,
            typer.Option(
                "--hour",
                help="Maximum requests per hour",
            ),
        ] = None,
        day: Annotated[
            int | None,
            typer.Option(
                "--day",
                help="Maximum requests per day",
            ),
        ] = None,
        month: Annotated[
            int | None,
            typer.Option(
                "--month",
                help="Maximum requests per month",
            ),
        ] = None,
        year: Annotated[
            int | None,
            typer.Option(
                "--year",
                help="Maximum requests per year",
            ),
        ] = None,
        policy: Annotated[
            str | None,
            typer.Option(
                "--policy",
                "-p",
                help="Rate limiting policy: local, cluster, or redis",
            ),
        ] = None,
        limit_by: Annotated[
            str | None,
            typer.Option(
                "--limit-by",
                help="Entity to limit by: consumer, credential, ip, service, header, or path",
            ),
        ] = None,
        header_name: Annotated[
            str | None,
            typer.Option(
                "--header-name",
                help="Header name when limit-by is 'header'",
            ),
        ] = None,
        path: Annotated[
            str | None,
            typer.Option(
                "--path",
                help="Path when limit-by is 'path'",
            ),
        ] = None,
        hide_client_headers: Annotated[
            bool,
            typer.Option(
                "--hide-client-headers/--show-client-headers",
                help="Hide X-RateLimit headers from response",
            ),
        ] = False,
        fault_tolerant: Annotated[
            bool,
            typer.Option(
                "--fault-tolerant/--strict",
                help="Proxy requests when datastore is unreachable",
            ),
        ] = True,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable rate limiting on a service or route.

        Configure request rate limiting to protect APIs from excessive traffic.
        At least one rate limit (second, minute, hour, day, month, or year) is required.

        Examples:
            ops kong traffic rate-limit enable --service my-api --minute 100
            ops kong traffic rate-limit enable --service my-api --second 10 --minute 100 --hour 5000
            ops kong traffic rate-limit enable --route my-route --minute 60 --policy cluster
            ops kong traffic rate-limit enable --service my-api --minute 100 --limit-by consumer
        """
        validate_scope(service, route)

        # Validate at least one limit is provided
        limits = {
            "second": second,
            "minute": minute,
            "hour": hour,
            "day": day,
            "month": month,
            "year": year,
        }
        active_limits = {k: v for k, v in limits.items() if v is not None}

        if not active_limits:
            console.print(
                "[red]Error:[/red] At least one rate limit is required "
                "(--second, --minute, --hour, --day, --month, or --year)"
            )
            raise typer.Exit(1)

        # Validate policy if provided
        if policy and policy not in POLICIES:
            console.print(
                f"[red]Error:[/red] Invalid policy '{policy}'. "
                f"Must be one of: {', '.join(POLICIES)}"
            )
            raise typer.Exit(1)

        # Validate limit_by if provided
        if limit_by and limit_by not in LIMIT_BY_OPTIONS:
            console.print(
                f"[red]Error:[/red] Invalid limit-by '{limit_by}'. "
                f"Must be one of: {', '.join(LIMIT_BY_OPTIONS)}"
            )
            raise typer.Exit(1)

        # Validate header_name when limit_by is header
        if limit_by == "header" and not header_name:
            console.print("[red]Error:[/red] --header-name is required when --limit-by is 'header'")
            raise typer.Exit(1)

        # Build plugin configuration
        config: dict[str, Any] = {
            **active_limits,
            "hide_client_headers": hide_client_headers,
            "fault_tolerant": fault_tolerant,
        }

        if policy:
            config["policy"] = policy
        if limit_by:
            config["limit_by"] = limit_by
        if header_name:
            config["header_name"] = header_name
        if path:
            config["path"] = path

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                PLUGIN_NAME,
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Rate limiting enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="Rate Limiting Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @rate_limit_app.command("get")
    def get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get rate limiting configuration for a service or route.

        Shows the current rate limiting plugin configuration if one exists.

        Examples:
            ops kong traffic rate-limit get --service my-api
            ops kong traffic rate-limit get --route my-route
            ops kong traffic rate-limit get --service my-api --output json
        """
        validate_scope(service, route)

        try:
            manager = get_plugin_manager()
            plugin_data = find_plugin_for_scope(manager, PLUGIN_NAME, service, route)

            if not plugin_data:
                scope_desc = f"service '{service}'" if service else f"route '{route}'"
                console.print(f"[yellow]No rate limiting plugin found for {scope_desc}[/yellow]")
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="Rate Limiting Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @rate_limit_app.command("disable")
    def disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable rate limiting on a service or route.

        Removes the rate limiting plugin from the specified scope.

        Examples:
            ops kong traffic rate-limit disable --service my-api
            ops kong traffic rate-limit disable --route my-route --force
        """
        validate_scope(service, route)

        try:
            manager = get_plugin_manager()
            plugin_data = find_plugin_for_scope(manager, PLUGIN_NAME, service, route)

            if not plugin_data:
                scope_desc = f"service '{service}'" if service else f"route '{route}'"
                console.print(f"[yellow]No rate limiting plugin found for {scope_desc}[/yellow]")
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id or not isinstance(plugin_id, str):
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope_desc = f"service '{service}'" if service else f"route '{route}'"

            # Confirm unless force flag
            if not force and not typer.confirm(
                f"Are you sure you want to disable rate limiting on {scope_desc}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(f"[green]Rate limiting disabled successfully on {scope_desc}[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(rate_limit_app, name="rate-limit")
