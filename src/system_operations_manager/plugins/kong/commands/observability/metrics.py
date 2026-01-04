"""Metrics commands for Kong Gateway.

Provides CLI commands for Prometheus plugin configuration and metrics viewing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.table import Table

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
    from system_operations_manager.services.kong.observability_manager import (
        ObservabilityManager,
    )
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager

# Plugin name constant
PROMETHEUS_PLUGIN = "prometheus"


def register_metrics_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
    get_observability_manager: Callable[[], ObservabilityManager],
) -> None:
    """Register metrics commands with the observability app.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function for KongPluginManager.
        get_observability_manager: Factory function for ObservabilityManager.
    """
    # Create metrics sub-app
    metrics_app = typer.Typer(
        name="metrics",
        help="Prometheus metrics and monitoring",
        no_args_is_help=True,
    )

    # Create prometheus sub-app for plugin management
    prometheus_app = typer.Typer(
        name="prometheus",
        help="Prometheus plugin configuration",
        no_args_is_help=True,
    )

    # =========================================================================
    # Prometheus Plugin Commands
    # =========================================================================

    @prometheus_app.command("enable")
    def prometheus_enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        global_scope: GlobalScopeOption = False,
        per_consumer: Annotated[
            bool,
            typer.Option(
                "--per-consumer/--no-per-consumer",
                help="Export per-consumer metrics",
            ),
        ] = False,
        status_code_metrics: Annotated[
            bool,
            typer.Option(
                "--status-code-metrics/--no-status-code-metrics",
                help="Export HTTP status code breakdown",
            ),
        ] = False,
        latency_metrics: Annotated[
            bool,
            typer.Option(
                "--latency-metrics/--no-latency-metrics",
                help="Export latency histogram metrics",
            ),
        ] = True,
        bandwidth_metrics: Annotated[
            bool,
            typer.Option(
                "--bandwidth-metrics/--no-bandwidth-metrics",
                help="Export bandwidth metrics",
            ),
        ] = False,
        upstream_health_metrics: Annotated[
            bool,
            typer.Option(
                "--upstream-health-metrics/--no-upstream-health-metrics",
                help="Export upstream health metrics",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable Prometheus metrics collection.

        Enables the Prometheus plugin to expose metrics at /metrics endpoint.

        Examples:
            ops kong observability metrics prometheus enable --global
            ops kong observability metrics prometheus enable --service my-api
            ops kong observability metrics prometheus enable --global --per-consumer
        """
        validate_scope(service, route, global_scope)

        # Build plugin config
        config: dict[str, Any] = {
            "per_consumer": per_consumer,
            "status_code_metrics": status_code_metrics,
            "latency_metrics": latency_metrics,
            "bandwidth_metrics": bandwidth_metrics,
            "upstream_health_metrics": upstream_health_metrics,
        }

        try:
            manager = get_plugin_manager()

            # For global scope, don't pass service or route
            plugin = manager.enable(
                PROMETHEUS_PLUGIN,
                service=service if not global_scope else None,
                route=route if not global_scope else None,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Prometheus metrics enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="Prometheus Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @prometheus_app.command("get")
    def prometheus_get(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get Prometheus plugin configuration.

        Shows the current Prometheus plugin settings for a service, route,
        or global scope.

        Examples:
            ops kong observability metrics prometheus get --service my-api
            ops kong observability metrics prometheus get
        """
        try:
            manager = get_plugin_manager()
            plugins = manager.list(name=PROMETHEUS_PLUGIN)

            if not isinstance(plugins, list) or not plugins:
                console.print(
                    "[yellow]No Prometheus plugin found. "
                    "Enable with: ops kong observability metrics prometheus enable --global[/yellow]"
                )
                raise typer.Exit(0)

            # Find matching plugin
            for plugin in plugins:
                plugin_data = plugin.model_dump()
                plugin_service = plugin_data.get("service")
                plugin_route = plugin_data.get("route")

                # Match based on scope
                if service:
                    if plugin_service and (
                        plugin_service.get("id") == service or plugin_service.get("name") == service
                    ):
                        formatter = get_formatter(output, console)
                        formatter.format_dict(plugin_data, title="Prometheus Plugin Configuration")
                        return
                elif route:
                    if plugin_route and (
                        plugin_route.get("id") == route or plugin_route.get("name") == route
                    ):
                        formatter = get_formatter(output, console)
                        formatter.format_dict(plugin_data, title="Prometheus Plugin Configuration")
                        return
                else:
                    # Global scope - no service or route
                    if not plugin_service and not plugin_route:
                        formatter = get_formatter(output, console)
                        formatter.format_dict(plugin_data, title="Prometheus Plugin Configuration")
                        return

            scope_desc = (
                f"service '{service}'"
                if service
                else f"route '{route}'"
                if route
                else "global scope"
            )
            console.print(f"[yellow]No Prometheus plugin found for {scope_desc}[/yellow]")

        except KongAPIError as e:
            handle_kong_error(e)

    @prometheus_app.command("disable")
    def prometheus_disable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        force: ForceOption = False,
    ) -> None:
        """Disable Prometheus metrics collection.

        Removes the Prometheus plugin from a service, route, or global scope.

        Examples:
            ops kong observability metrics prometheus disable --global --force
            ops kong observability metrics prometheus disable --service my-api
        """
        try:
            manager = get_plugin_manager()
            plugins = manager.list(name=PROMETHEUS_PLUGIN)

            if not isinstance(plugins, list) or not plugins:
                console.print("[yellow]No Prometheus plugin found[/yellow]")
                raise typer.Exit(0)

            # Find matching plugin
            for plugin in plugins:
                plugin_data = plugin.model_dump()
                plugin_service = plugin_data.get("service")
                plugin_route = plugin_data.get("route")
                plugin_id = plugin_data.get("id")

                # Match based on scope
                matched = False
                if service:
                    if plugin_service and (
                        plugin_service.get("id") == service or plugin_service.get("name") == service
                    ):
                        matched = True
                elif route:
                    if plugin_route and (
                        plugin_route.get("id") == route or plugin_route.get("name") == route
                    ):
                        matched = True
                else:
                    # Global scope
                    if not plugin_service and not plugin_route:
                        matched = True

                if matched and plugin_id:
                    scope_desc = (
                        f"service '{service}'"
                        if service
                        else f"route '{route}'"
                        if route
                        else "global scope"
                    )

                    if not force and not typer.confirm(
                        f"Disable Prometheus metrics for {scope_desc}?",
                        default=False,
                    ):
                        console.print("[yellow]Cancelled[/yellow]")
                        raise typer.Exit(0)

                    manager.disable(plugin_id)
                    console.print(f"[green]Prometheus metrics disabled for {scope_desc}[/green]")
                    return

            scope_desc = (
                f"service '{service}'"
                if service
                else f"route '{route}'"
                if route
                else "global scope"
            )
            console.print(f"[yellow]No Prometheus plugin found for {scope_desc}[/yellow]")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # Metrics Viewing Commands
    # =========================================================================

    @metrics_app.command("show")
    def metrics_show(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show aggregated metrics summary.

        Displays request counts, latency, and connection statistics
        from Kong's Prometheus metrics endpoint.

        Examples:
            ops kong observability metrics show
            ops kong observability metrics show --service my-api
            ops kong observability metrics show --output json
        """
        try:
            manager = get_observability_manager()
            summary = manager.get_metrics_summary(
                service_filter=service,
                route_filter=route,
            )

            if summary.total_requests == 0:
                console.print(
                    "[yellow]No metrics data available. "
                    "Ensure Prometheus plugin is enabled: "
                    "ops kong observability metrics prometheus enable --global[/yellow]"
                )
                raise typer.Exit(0)

            if output == OutputFormat.TABLE:
                # Summary table
                table = Table(title="Kong Metrics Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Total Requests", f"{summary.total_requests:,}")

                if summary.latency_avg_ms is not None:
                    table.add_row("Avg Latency", f"{summary.latency_avg_ms:.2f} ms")

                table.add_row("Active Connections", str(summary.connections_active))
                table.add_row("Total Connections", f"{summary.connections_total:,}")

                console.print(table)

                # Status code breakdown
                if summary.requests_per_status:
                    status_table = Table(title="Requests by Status Code")
                    status_table.add_column("Status", style="cyan")
                    status_table.add_column("Count", style="green")
                    status_table.add_column("Percentage", style="yellow")

                    for status, count in sorted(summary.requests_per_status.items()):
                        pct = (
                            (count / summary.total_requests * 100)
                            if summary.total_requests > 0
                            else 0
                        )
                        status_table.add_row(status, f"{count:,}", f"{pct:.1f}%")

                    console.print(status_table)

                # Service breakdown
                if summary.requests_per_service and len(summary.requests_per_service) > 1:
                    service_table = Table(title="Requests by Service")
                    service_table.add_column("Service", style="cyan")
                    service_table.add_column("Count", style="green")
                    service_table.add_column("Percentage", style="yellow")

                    for svc, count in sorted(
                        summary.requests_per_service.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    ):
                        pct = (
                            (count / summary.total_requests * 100)
                            if summary.total_requests > 0
                            else 0
                        )
                        service_table.add_row(svc, f"{count:,}", f"{pct:.1f}%")

                    console.print(service_table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(summary.model_dump(), title="Metrics Summary")

        except KongAPIError as e:
            handle_kong_error(e)

    @metrics_app.command("list")
    def metrics_list(
        name: Annotated[
            str | None,
            typer.Option(
                "--name",
                "-n",
                help="Filter by metric name (regex pattern)",
            ),
        ] = None,
        metric_type: Annotated[
            str | None,
            typer.Option(
                "--type",
                "-t",
                help="Filter by type (counter, gauge, histogram, summary)",
            ),
        ] = None,
        limit: Annotated[
            int,
            typer.Option(
                "--limit",
                "-l",
                help="Maximum number of metrics to show",
            ),
        ] = 50,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List available Prometheus metrics.

        Shows all metrics exposed by Kong's Prometheus plugin with optional filtering.

        Examples:
            ops kong observability metrics list
            ops kong observability metrics list --name "kong_http"
            ops kong observability metrics list --type counter
        """
        try:
            manager = get_observability_manager()
            metrics = manager.list_metrics(
                name_filter=name,
                type_filter=metric_type,
            )

            if not metrics:
                console.print(
                    "[yellow]No metrics found. Ensure Prometheus plugin is enabled.[/yellow]"
                )
                raise typer.Exit(0)

            # Limit results
            metrics = metrics[:limit]

            if output == OutputFormat.TABLE:
                table = Table(title=f"Kong Prometheus Metrics ({len(metrics)} shown)")
                table.add_column("Name", style="cyan")
                table.add_column("Type", style="yellow")
                table.add_column("Value", style="green")
                table.add_column("Labels", style="dim")

                for metric in metrics:
                    labels_str = ", ".join(f"{k}={v}" for k, v in metric.labels.items())
                    value_str = f"{metric.value:.2f}" if metric.value is not None else "-"
                    table.add_row(metric.name, metric.type, value_str, labels_str[:50])

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                data = [m.model_dump() for m in metrics]
                formatter.format_dict({"metrics": data}, title="Prometheus Metrics")

        except KongAPIError as e:
            handle_kong_error(e)

    @metrics_app.command("status")
    def metrics_status(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show Kong node status and connection statistics.

        Displays server status including connections, memory usage,
        and database connectivity from Kong's /status endpoint.

        Examples:
            ops kong observability metrics status
            ops kong observability metrics status --output json
        """
        try:
            manager = get_observability_manager()
            status = manager.get_node_status()

            if output == OutputFormat.TABLE:
                table = Table(title="Kong Node Status")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row(
                    "Database",
                    "[green]Connected[/green]"
                    if status.database_reachable
                    else "[red]Disconnected[/red]",
                )
                table.add_row("Total Requests", f"{status.server_total_requests:,}")
                table.add_row("Connections Accepted", f"{status.server_connections_accepted:,}")
                table.add_row("Connections Handled", f"{status.server_connections_handled:,}")
                table.add_row("Active Connections", str(status.server_connections_active))
                table.add_row("Reading", str(status.server_connections_reading))
                table.add_row("Writing", str(status.server_connections_writing))
                table.add_row("Waiting", str(status.server_connections_waiting))

                console.print(table)

                # Memory info if available
                if status.memory_lua_shared_dicts:
                    memory_table = Table(title="Memory Usage (Shared Dicts)")
                    memory_table.add_column("Dict", style="cyan")
                    memory_table.add_column("Allocated", style="green")
                    memory_table.add_column("Capacity", style="yellow")

                    for name, info in status.memory_lua_shared_dicts.items():
                        if isinstance(info, dict):
                            allocated = info.get("allocated_slabs", "-")
                            capacity = info.get("capacity", "-")
                            memory_table.add_row(name, str(allocated), str(capacity))

                    console.print(memory_table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(status.model_dump(), title="Node Status")

        except KongAPIError as e:
            handle_kong_error(e)

    # Add sub-apps to metrics app
    metrics_app.add_typer(prometheus_app, name="prometheus")

    # Add metrics app to parent
    app.add_typer(metrics_app, name="metrics")
