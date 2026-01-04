"""Logging commands for Kong Gateway.

Provides CLI commands for configuring HTTP, file, syslog, and TCP logging plugins.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.observability.base import (
    ForceOption,
    GlobalScopeOption,
    OutputFormat,
    OutputOption,
    RouteScopeOption,
    ServiceScopeOption,
    console,
    get_formatter,
    handle_kong_error,
    validate_scope,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


def _find_log_plugin(
    manager: KongPluginManager,
    plugin_name: str,
    service: str | None,
    route: str | None,
) -> dict[str, Any] | None:
    """Find an existing log plugin for the given scope.

    Args:
        manager: Plugin manager instance.
        plugin_name: Name of the logging plugin.
        service: Service ID or name filter.
        route: Route ID or name filter.

    Returns:
        Plugin data dict if found, None otherwise.
    """
    plugins = manager.list(name=plugin_name)
    if not isinstance(plugins, list):
        return None

    for plugin in plugins:
        plugin_data = plugin.model_dump()
        plugin_service = plugin_data.get("service")
        plugin_route = plugin_data.get("route")

        if service:
            if plugin_service and (
                plugin_service.get("id") == service or plugin_service.get("name") == service
            ):
                return plugin_data
        elif route:
            if plugin_route and (
                plugin_route.get("id") == route or plugin_route.get("name") == route
            ):
                return plugin_data
        else:
            # Global scope
            if not plugin_service and not plugin_route:
                return plugin_data

    return None


def register_logs_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register logging commands with the observability app.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function for KongPluginManager.
    """
    # Create logs sub-app
    logs_app = typer.Typer(
        name="logs",
        help="Logging plugin configuration (HTTP, file, syslog, TCP)",
        no_args_is_help=True,
    )

    # =========================================================================
    # HTTP Log Plugin Commands
    # =========================================================================

    http_app = typer.Typer(
        name="http",
        help="HTTP logging plugin",
        no_args_is_help=True,
    )

    @http_app.command("enable")
    def http_enable(
        http_endpoint: Annotated[
            str,
            typer.Option(
                "--http-endpoint",
                "-e",
                help="HTTP endpoint URL to send logs to (required)",
            ),
        ],
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        global_scope: GlobalScopeOption = False,
        method: Annotated[
            str,
            typer.Option(
                "--method",
                "-m",
                help="HTTP method for log requests",
            ),
        ] = "POST",
        content_type: Annotated[
            str,
            typer.Option(
                "--content-type",
                help="Content-Type header for log requests",
            ),
        ] = "application/json",
        timeout: Annotated[
            int,
            typer.Option(
                "--timeout",
                help="Request timeout in milliseconds",
            ),
        ] = 10000,
        keepalive: Annotated[
            int,
            typer.Option(
                "--keepalive",
                help="Keepalive timeout in milliseconds",
            ),
        ] = 60000,
        retry_count: Annotated[
            int | None,
            typer.Option(
                "--retry-count",
                help="Number of retries on failure",
            ),
        ] = None,
        queue_size: Annotated[
            int | None,
            typer.Option(
                "--queue-size",
                help="Maximum number of entries in the queue",
            ),
        ] = None,
        flush_timeout: Annotated[
            int | None,
            typer.Option(
                "--flush-timeout",
                help="Maximum time to wait before flushing queue (seconds)",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable HTTP logging.

        Sends log data to an HTTP endpoint for each request.

        Examples:
            ops kong observability logs http enable --http-endpoint http://logs.example.com --global
            ops kong observability logs http enable --http-endpoint http://logs.example.com --service my-api
        """
        validate_scope(service, route, global_scope)

        config: dict[str, Any] = {
            "http_endpoint": http_endpoint,
            "method": method,
            "content_type": content_type,
            "timeout": timeout,
            "keepalive": keepalive,
        }

        if retry_count is not None:
            config["retry_count"] = retry_count
        if queue_size is not None:
            config["queue_size"] = queue_size
        if flush_timeout is not None:
            config["flush_timeout"] = flush_timeout

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "http-log",
                service=service if not global_scope else None,
                route=route if not global_scope else None,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]HTTP logging enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="HTTP Log Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @http_app.command("get")
    def http_get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get HTTP logging configuration.

        Examples:
            ops kong observability logs http get --service my-api
            ops kong observability logs http get
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_log_plugin(manager, "http-log", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No HTTP log plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="HTTP Log Plugin Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @http_app.command("disable")
    def http_disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable HTTP logging.

        Examples:
            ops kong observability logs http disable --global --force
            ops kong observability logs http disable --service my-api
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_log_plugin(manager, "http-log", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No HTTP log plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id:
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope = f"service '{service}'" if service else f"route '{route}'" if route else "global"

            if not force and not typer.confirm(
                f"Disable HTTP logging for {scope}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(f"[green]HTTP logging disabled for {scope}[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # File Log Plugin Commands
    # =========================================================================

    file_app = typer.Typer(
        name="file",
        help="File logging plugin",
        no_args_is_help=True,
    )

    @file_app.command("enable")
    def file_enable(
        path: Annotated[
            str,
            typer.Option(
                "--path",
                "-p",
                help="File path to write logs to (required)",
            ),
        ],
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        global_scope: GlobalScopeOption = False,
        reopen: Annotated[
            bool,
            typer.Option(
                "--reopen/--no-reopen",
                help="Reopen the file on every request (for log rotation)",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable file logging.

        Writes log data to a file on the Kong node.

        Examples:
            ops kong observability logs file enable --path /var/log/kong/access.log --global
            ops kong observability logs file enable --path /var/log/kong/api.log --service my-api
        """
        validate_scope(service, route, global_scope)

        config: dict[str, Any] = {
            "path": path,
            "reopen": reopen,
        }

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "file-log",
                service=service if not global_scope else None,
                route=route if not global_scope else None,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]File logging enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="File Log Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @file_app.command("get")
    def file_get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get file logging configuration.

        Examples:
            ops kong observability logs file get --service my-api
            ops kong observability logs file get
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_log_plugin(manager, "file-log", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No file log plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="File Log Plugin Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @file_app.command("disable")
    def file_disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable file logging.

        Examples:
            ops kong observability logs file disable --global --force
            ops kong observability logs file disable --service my-api
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_log_plugin(manager, "file-log", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No file log plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id:
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope = f"service '{service}'" if service else f"route '{route}'" if route else "global"

            if not force and not typer.confirm(
                f"Disable file logging for {scope}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(f"[green]File logging disabled for {scope}[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # Syslog Plugin Commands
    # =========================================================================

    syslog_app = typer.Typer(
        name="syslog",
        help="Syslog logging plugin",
        no_args_is_help=True,
    )

    @syslog_app.command("enable")
    def syslog_enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        global_scope: GlobalScopeOption = False,
        host: Annotated[
            str,
            typer.Option(
                "--host",
                "-h",
                help="Syslog server host",
            ),
        ] = "127.0.0.1",
        port: Annotated[
            int,
            typer.Option(
                "--port",
                "-p",
                help="Syslog server port",
            ),
        ] = 514,
        facility: Annotated[
            str,
            typer.Option(
                "--facility",
                help="Syslog facility (kern, user, mail, daemon, auth, syslog, lpr, news, uucp, cron, local0-7)",
            ),
        ] = "user",
        severity: Annotated[
            str,
            typer.Option(
                "--severity",
                help="Minimum log severity (debug, info, notice, warning, err, crit, alert, emerg)",
            ),
        ] = "info",
        log_level: Annotated[
            str,
            typer.Option(
                "--log-level",
                help="Log level for successful requests",
            ),
        ] = "info",
        successful_severity: Annotated[
            str | None,
            typer.Option(
                "--successful-severity",
                help="Severity for successful requests",
            ),
        ] = None,
        client_errors_severity: Annotated[
            str | None,
            typer.Option(
                "--client-errors-severity",
                help="Severity for 4xx errors",
            ),
        ] = None,
        server_errors_severity: Annotated[
            str | None,
            typer.Option(
                "--server-errors-severity",
                help="Severity for 5xx errors",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable syslog logging.

        Sends log data to a syslog server.

        Examples:
            ops kong observability logs syslog enable --global
            ops kong observability logs syslog enable --host syslog.example.com --port 514 --global
        """
        validate_scope(service, route, global_scope)

        config: dict[str, Any] = {
            "host": host,
            "port": port,
            "facility": facility,
            "severity": severity,
            "log_level": log_level,
        }

        if successful_severity:
            config["successful_severity"] = successful_severity
        if client_errors_severity:
            config["client_errors_severity"] = client_errors_severity
        if server_errors_severity:
            config["server_errors_severity"] = server_errors_severity

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "syslog",
                service=service if not global_scope else None,
                route=route if not global_scope else None,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Syslog logging enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="Syslog Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @syslog_app.command("get")
    def syslog_get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get syslog configuration.

        Examples:
            ops kong observability logs syslog get --service my-api
            ops kong observability logs syslog get
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_log_plugin(manager, "syslog", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No syslog plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="Syslog Plugin Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @syslog_app.command("disable")
    def syslog_disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable syslog logging.

        Examples:
            ops kong observability logs syslog disable --global --force
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_log_plugin(manager, "syslog", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No syslog plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id:
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope = f"service '{service}'" if service else f"route '{route}'" if route else "global"

            if not force and not typer.confirm(
                f"Disable syslog logging for {scope}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(f"[green]Syslog logging disabled for {scope}[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # TCP Log Plugin Commands
    # =========================================================================

    tcp_app = typer.Typer(
        name="tcp",
        help="TCP logging plugin",
        no_args_is_help=True,
    )

    @tcp_app.command("enable")
    def tcp_enable(
        host: Annotated[
            str,
            typer.Option(
                "--host",
                "-h",
                help="TCP server host (required)",
            ),
        ],
        port: Annotated[
            int,
            typer.Option(
                "--port",
                "-p",
                help="TCP server port (required)",
            ),
        ],
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        global_scope: GlobalScopeOption = False,
        tls: Annotated[
            bool,
            typer.Option(
                "--tls/--no-tls",
                help="Enable TLS for the connection",
            ),
        ] = False,
        tls_sni: Annotated[
            str | None,
            typer.Option(
                "--tls-sni",
                help="TLS SNI hostname",
            ),
        ] = None,
        timeout: Annotated[
            int,
            typer.Option(
                "--timeout",
                help="Connection timeout in milliseconds",
            ),
        ] = 10000,
        keepalive: Annotated[
            int,
            typer.Option(
                "--keepalive",
                help="Keepalive timeout in milliseconds",
            ),
        ] = 60000,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable TCP logging.

        Sends log data to a TCP server.

        Examples:
            ops kong observability logs tcp enable --host logs.example.com --port 5000 --global
            ops kong observability logs tcp enable --host logs.example.com --port 5000 --tls --global
        """
        validate_scope(service, route, global_scope)

        config: dict[str, Any] = {
            "host": host,
            "port": port,
            "tls": tls,
            "timeout": timeout,
            "keepalive": keepalive,
        }

        if tls_sni:
            config["tls_sni"] = tls_sni

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "tcp-log",
                service=service if not global_scope else None,
                route=route if not global_scope else None,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]TCP logging enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="TCP Log Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @tcp_app.command("get")
    def tcp_get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get TCP logging configuration.

        Examples:
            ops kong observability logs tcp get --service my-api
            ops kong observability logs tcp get
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_log_plugin(manager, "tcp-log", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No TCP log plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="TCP Log Plugin Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @tcp_app.command("disable")
    def tcp_disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable TCP logging.

        Examples:
            ops kong observability logs tcp disable --global --force
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_log_plugin(manager, "tcp-log", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No TCP log plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id:
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope = f"service '{service}'" if service else f"route '{route}'" if route else "global"

            if not force and not typer.confirm(
                f"Disable TCP logging for {scope}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(f"[green]TCP logging disabled for {scope}[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    # Add all sub-apps to logs app
    logs_app.add_typer(http_app, name="http")
    logs_app.add_typer(file_app, name="file")
    logs_app.add_typer(syslog_app, name="syslog")
    logs_app.add_typer(tcp_app, name="tcp")

    # Add logs app to parent
    app.add_typer(logs_app, name="logs")
