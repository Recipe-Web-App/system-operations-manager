"""Distributed tracing commands for Kong Gateway.

Provides CLI commands for configuring OpenTelemetry and Zipkin tracing plugins.
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


def _find_tracing_plugin(
    manager: KongPluginManager,
    plugin_name: str,
    service: str | None,
    route: str | None,
) -> dict[str, Any] | None:
    """Find an existing tracing plugin for the given scope.

    Args:
        manager: Plugin manager instance.
        plugin_name: Name of the tracing plugin.
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


def _parse_key_value_list(items: list[str] | None) -> dict[str, str]:
    """Parse a list of key=value strings into a dictionary.

    Args:
        items: List of strings in "key=value" format.

    Returns:
        Dictionary of parsed key-value pairs.
    """
    if not items:
        return {}

    result: dict[str, str] = {}
    for item in items:
        if "=" in item:
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def register_tracing_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
) -> None:
    """Register tracing commands with the observability app.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function for KongPluginManager.
    """
    # Create tracing sub-app
    tracing_app = typer.Typer(
        name="tracing",
        help="Distributed tracing configuration (OpenTelemetry, Zipkin)",
        no_args_is_help=True,
    )

    # =========================================================================
    # OpenTelemetry Plugin Commands
    # =========================================================================

    otel_app = typer.Typer(
        name="opentelemetry",
        help="OpenTelemetry tracing plugin",
        no_args_is_help=True,
    )

    @otel_app.command("enable")
    def otel_enable(
        endpoint: Annotated[
            str,
            typer.Option(
                "--endpoint",
                "-e",
                help="OTLP endpoint URL (required)",
            ),
        ],
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        global_scope: GlobalScopeOption = False,
        header: Annotated[
            list[str] | None,
            typer.Option(
                "--header",
                "-H",
                help="Headers as key=value (can be repeated)",
            ),
        ] = None,
        resource_attribute: Annotated[
            list[str] | None,
            typer.Option(
                "--resource-attribute",
                "-r",
                help="Resource attributes as key=value (can be repeated)",
            ),
        ] = None,
        batch_span_count: Annotated[
            int,
            typer.Option(
                "--batch-span-count",
                help="Number of spans to batch before sending",
            ),
        ] = 200,
        batch_flush_delay: Annotated[
            int,
            typer.Option(
                "--batch-flush-delay",
                help="Delay before flushing batch (seconds)",
            ),
        ] = 3,
        connect_timeout: Annotated[
            int,
            typer.Option(
                "--connect-timeout",
                help="Connection timeout in milliseconds",
            ),
        ] = 1000,
        send_timeout: Annotated[
            int,
            typer.Option(
                "--send-timeout",
                help="Send timeout in milliseconds",
            ),
        ] = 5000,
        read_timeout: Annotated[
            int,
            typer.Option(
                "--read-timeout",
                help="Read timeout in milliseconds",
            ),
        ] = 5000,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable OpenTelemetry tracing.

        Sends trace data to an OTLP-compatible endpoint.

        Examples:
            ops kong observability tracing opentelemetry enable --endpoint http://otel-collector:4317 --global
            ops kong observability tracing opentelemetry enable --endpoint http://otel-collector:4317 --header "Authorization=Bearer token" --global
        """
        validate_scope(service, route, global_scope)

        config: dict[str, Any] = {
            "endpoint": endpoint,
            "batch_span_count": batch_span_count,
            "batch_flush_delay": batch_flush_delay,
            "connect_timeout": connect_timeout,
            "send_timeout": send_timeout,
            "read_timeout": read_timeout,
        }

        # Parse headers
        headers = _parse_key_value_list(header)
        if headers:
            config["headers"] = headers

        # Parse resource attributes
        attrs = _parse_key_value_list(resource_attribute)
        if attrs:
            config["resource_attributes"] = attrs

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "opentelemetry",
                service=service if not global_scope else None,
                route=route if not global_scope else None,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]OpenTelemetry tracing enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="OpenTelemetry Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @otel_app.command("get")
    def otel_get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get OpenTelemetry configuration.

        Examples:
            ops kong observability tracing opentelemetry get --service my-api
            ops kong observability tracing opentelemetry get
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_tracing_plugin(manager, "opentelemetry", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No OpenTelemetry plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="OpenTelemetry Plugin Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @otel_app.command("disable")
    def otel_disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable OpenTelemetry tracing.

        Examples:
            ops kong observability tracing opentelemetry disable --global --force
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_tracing_plugin(manager, "opentelemetry", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No OpenTelemetry plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id:
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope = f"service '{service}'" if service else f"route '{route}'" if route else "global"

            if not force and not typer.confirm(
                f"Disable OpenTelemetry tracing for {scope}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(f"[green]OpenTelemetry tracing disabled for {scope}[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # Zipkin Plugin Commands
    # =========================================================================

    zipkin_app = typer.Typer(
        name="zipkin",
        help="Zipkin tracing plugin",
        no_args_is_help=True,
    )

    @zipkin_app.command("enable")
    def zipkin_enable(
        http_endpoint: Annotated[
            str,
            typer.Option(
                "--http-endpoint",
                "-e",
                help="Zipkin HTTP endpoint URL (required)",
            ),
        ],
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        global_scope: GlobalScopeOption = False,
        sample_ratio: Annotated[
            float,
            typer.Option(
                "--sample-ratio",
                "-s",
                help="Sampling ratio (0.0 to 1.0)",
                min=0.0,
                max=1.0,
            ),
        ] = 0.001,
        default_service_name: Annotated[
            str | None,
            typer.Option(
                "--default-service-name",
                help="Default service name for spans",
            ),
        ] = None,
        include_credential: Annotated[
            bool,
            typer.Option(
                "--include-credential/--no-include-credential",
                help="Include authentication credentials in traces",
            ),
        ] = True,
        traceid_byte_count: Annotated[
            int,
            typer.Option(
                "--traceid-byte-count",
                help="Trace ID size in bytes (8 or 16)",
            ),
        ] = 16,
        header_type: Annotated[
            str,
            typer.Option(
                "--header-type",
                help="Trace header format (preserve, ignore, b3, b3-single, w3c, jaeger, ot)",
            ),
        ] = "preserve",
        default_header_type: Annotated[
            str,
            typer.Option(
                "--default-header-type",
                help="Default header type when none found",
            ),
        ] = "b3",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable Zipkin tracing.

        Sends trace data to a Zipkin-compatible endpoint.

        Examples:
            ops kong observability tracing zipkin enable --http-endpoint http://zipkin:9411/api/v2/spans --global
            ops kong observability tracing zipkin enable --http-endpoint http://zipkin:9411/api/v2/spans --sample-ratio 0.1 --global
        """
        validate_scope(service, route, global_scope)

        config: dict[str, Any] = {
            "http_endpoint": http_endpoint,
            "sample_ratio": sample_ratio,
            "include_credential": include_credential,
            "traceid_byte_count": traceid_byte_count,
            "header_type": header_type,
            "default_header_type": default_header_type,
        }

        if default_service_name:
            config["default_service_name"] = default_service_name

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "zipkin",
                service=service if not global_scope else None,
                route=route if not global_scope else None,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Zipkin tracing enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="Zipkin Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @zipkin_app.command("get")
    def zipkin_get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get Zipkin configuration.

        Examples:
            ops kong observability tracing zipkin get --service my-api
            ops kong observability tracing zipkin get
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_tracing_plugin(manager, "zipkin", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No Zipkin plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            formatter = get_formatter(output, console)
            formatter.format_dict(plugin_data, title="Zipkin Plugin Configuration")

        except KongAPIError as e:
            handle_kong_error(e)

    @zipkin_app.command("disable")
    def zipkin_disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable Zipkin tracing.

        Examples:
            ops kong observability tracing zipkin disable --global --force
        """
        try:
            manager = get_plugin_manager()
            plugin_data = _find_tracing_plugin(manager, "zipkin", service, route)

            if not plugin_data:
                scope = (
                    f"service '{service}'" if service else f"route '{route}'" if route else "global"
                )
                console.print(f"[yellow]No Zipkin plugin found for {scope}[/yellow]")
                raise typer.Exit(0)

            plugin_id = plugin_data.get("id")
            if not plugin_id:
                console.print("[red]Error:[/red] Plugin ID not found")
                raise typer.Exit(1)

            scope = f"service '{service}'" if service else f"route '{route}'" if route else "global"

            if not force and not typer.confirm(
                f"Disable Zipkin tracing for {scope}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.disable(plugin_id)
            console.print(f"[green]Zipkin tracing disabled for {scope}[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    # Add sub-apps to tracing app
    tracing_app.add_typer(otel_app, name="opentelemetry")
    tracing_app.add_typer(zipkin_app, name="zipkin")

    # Add tracing app to parent
    app.add_typer(tracing_app, name="tracing")
