"""Health check commands for Kong Gateway.

Provides CLI commands for viewing and configuring upstream health checks.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.table import Table

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.observability.base import (
    OutputFormat,
    OutputOption,
    UpstreamArgument,
    console,
    get_formatter,
    handle_kong_error,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kong.observability_manager import (
        ObservabilityManager,
    )
    from system_operations_manager.services.kong.upstream_manager import UpstreamManager


def register_health_commands(
    app: typer.Typer,
    get_upstream_manager: Callable[[], UpstreamManager],
    get_observability_manager: Callable[[], ObservabilityManager],
) -> None:
    """Register health check commands with the observability app.

    Args:
        app: Typer app to register commands on.
        get_upstream_manager: Factory function for UpstreamManager.
        get_observability_manager: Factory function for ObservabilityManager.
    """
    # Create health sub-app
    health_app = typer.Typer(
        name="health",
        help="Upstream health check monitoring and configuration",
        no_args_is_help=True,
    )

    # =========================================================================
    # Health Viewing Commands
    # =========================================================================

    @health_app.command("show")
    def health_show(
        upstream: UpstreamArgument,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show health status for an upstream.

        Displays the health status of all targets in an upstream,
        including individual address health.

        Examples:
            ops kong observability health show my-upstream
            ops kong observability health show my-upstream --output json
        """
        try:
            manager = get_observability_manager()
            summary = manager.get_upstream_health(upstream)

            if output == OutputFormat.TABLE:
                # Header info
                status_color = (
                    "green"
                    if summary.overall_health == "HEALTHY"
                    else "red"
                    if summary.overall_health == "UNHEALTHY"
                    else "yellow"
                )
                console.print(f"\n[bold]Upstream:[/bold] {summary.upstream_name}")
                console.print(
                    f"[bold]Status:[/bold] [{status_color}]{summary.overall_health}[/{status_color}]"
                )
                console.print(
                    f"[bold]Targets:[/bold] {summary.healthy_targets} healthy, "
                    f"{summary.unhealthy_targets} unhealthy, "
                    f"{summary.total_targets} total\n"
                )

                if summary.targets:
                    table = Table(title="Target Health")
                    table.add_column("Target", style="cyan")
                    table.add_column("Weight", style="dim")
                    table.add_column("Status", style="bold")
                    table.add_column("Addresses", style="dim")

                    for target in summary.targets:
                        status_style = (
                            "green"
                            if target.health == "HEALTHY"
                            else "red"
                            if target.health == "UNHEALTHY"
                            else "yellow"
                        )
                        addresses = ""
                        if target.addresses:
                            addresses = ", ".join(a.get("ip", "?") for a in target.addresses[:3])
                            if len(target.addresses) > 3:
                                addresses += f" (+{len(target.addresses) - 3})"

                        table.add_row(
                            target.target,
                            str(target.weight),
                            f"[{status_style}]{target.health}[/{status_style}]",
                            addresses,
                        )

                    console.print(table)
                else:
                    console.print("[yellow]No targets configured for this upstream[/yellow]")
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(summary.model_dump(), title=f"Upstream Health: {upstream}")

        except KongAPIError as e:
            handle_kong_error(e)

    @health_app.command("list")
    def health_list(
        unhealthy_only: Annotated[
            bool,
            typer.Option(
                "--unhealthy-only",
                "-u",
                help="Show only unhealthy upstreams",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List all upstreams with health status.

        Provides an overview of health status for all configured upstreams.

        Examples:
            ops kong observability health list
            ops kong observability health list --unhealthy-only
            ops kong observability health list --output json
        """
        try:
            manager = get_observability_manager()
            summaries = manager.list_upstreams_health()

            if not summaries:
                console.print("[yellow]No upstreams configured[/yellow]")
                raise typer.Exit(0)

            # Filter if requested
            if unhealthy_only:
                summaries = [s for s in summaries if s.overall_health == "UNHEALTHY"]
                if not summaries:
                    console.print("[green]All upstreams are healthy[/green]")
                    raise typer.Exit(0)

            if output == OutputFormat.TABLE:
                table = Table(title="Upstream Health Overview")
                table.add_column("Upstream", style="cyan")
                table.add_column("Status", style="bold")
                table.add_column("Healthy", style="green")
                table.add_column("Unhealthy", style="red")
                table.add_column("Total", style="dim")

                for summary in summaries:
                    status_style = (
                        "green"
                        if summary.overall_health == "HEALTHY"
                        else "red"
                        if summary.overall_health == "UNHEALTHY"
                        else "yellow"
                    )
                    table.add_row(
                        summary.upstream_name,
                        f"[{status_style}]{summary.overall_health}[/{status_style}]",
                        str(summary.healthy_targets),
                        str(summary.unhealthy_targets),
                        str(summary.total_targets),
                    )

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                data = [s.model_dump() for s in summaries]
                formatter.format_dict({"upstreams": data}, title="Upstream Health")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # Health Configuration Commands
    # =========================================================================

    @health_app.command("set")
    def health_set(
        upstream: UpstreamArgument,
        # Active health check options
        active_type: Annotated[
            str | None,
            typer.Option(
                "--active-type",
                help="Active health check type: http, https, tcp, or grpc",
            ),
        ] = None,
        active_http_path: Annotated[
            str | None,
            typer.Option(
                "--active-http-path",
                help="HTTP path for active health checks",
            ),
        ] = None,
        active_timeout: Annotated[
            int | None,
            typer.Option(
                "--active-timeout",
                help="Active health check timeout in seconds",
            ),
        ] = None,
        active_interval: Annotated[
            int | None,
            typer.Option(
                "--active-interval",
                help="Interval between active health checks (seconds)",
            ),
        ] = None,
        active_healthy_threshold: Annotated[
            int | None,
            typer.Option(
                "--active-healthy-threshold",
                help="Successes required to mark target healthy",
            ),
        ] = None,
        active_unhealthy_threshold: Annotated[
            int | None,
            typer.Option(
                "--active-unhealthy-threshold",
                help="Failures required to mark target unhealthy",
            ),
        ] = None,
        # Passive health check options
        passive_healthy_successes: Annotated[
            int | None,
            typer.Option(
                "--passive-healthy-successes",
                help="Successes to mark healthy (passive)",
            ),
        ] = None,
        passive_unhealthy_failures: Annotated[
            int | None,
            typer.Option(
                "--passive-unhealthy-failures",
                help="Failures to mark unhealthy (passive)",
            ),
        ] = None,
        passive_unhealthy_timeouts: Annotated[
            int | None,
            typer.Option(
                "--passive-unhealthy-timeouts",
                help="Timeouts to mark unhealthy (passive)",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Configure health checks for an upstream.

        Sets active and/or passive health check parameters for an upstream.
        Only specified options are updated; others remain unchanged.

        Examples:
            ops kong observability health set my-upstream --active-type http
            ops kong observability health set my-upstream --active-http-path /health
            ops kong observability health set my-upstream --active-interval 30
            ops kong observability health set my-upstream --passive-unhealthy-failures 5
        """
        try:
            upstream_manager = get_upstream_manager()

            # Build health check config
            healthchecks: dict[str, Any] = {}

            # Active health checks
            active: dict[str, Any] = {}
            if active_type:
                active["type"] = active_type
            if active_http_path:
                active["http_path"] = active_http_path
            if active_timeout is not None:
                active["timeout"] = active_timeout
            if active_interval is not None:
                active["healthy"] = active.get("healthy", {})
                active["healthy"]["interval"] = active_interval
                active["unhealthy"] = active.get("unhealthy", {})
                active["unhealthy"]["interval"] = active_interval
            if active_healthy_threshold is not None:
                active["healthy"] = active.get("healthy", {})
                active["healthy"]["successes"] = active_healthy_threshold
            if active_unhealthy_threshold is not None:
                active["unhealthy"] = active.get("unhealthy", {})
                active["unhealthy"]["http_failures"] = active_unhealthy_threshold

            if active:
                healthchecks["active"] = active

            # Passive health checks
            passive: dict[str, Any] = {}
            if passive_healthy_successes is not None:
                passive["healthy"] = passive.get("healthy", {})
                passive["healthy"]["successes"] = passive_healthy_successes
            if passive_unhealthy_failures is not None:
                passive["unhealthy"] = passive.get("unhealthy", {})
                passive["unhealthy"]["http_failures"] = passive_unhealthy_failures
            if passive_unhealthy_timeouts is not None:
                passive["unhealthy"] = passive.get("unhealthy", {})
                passive["unhealthy"]["timeouts"] = passive_unhealthy_timeouts

            if passive:
                healthchecks["passive"] = passive

            if not healthchecks:
                console.print(
                    "[yellow]No health check options specified. "
                    "Use --help to see available options.[/yellow]"
                )
                raise typer.Exit(1)

            # Get current upstream and update
            current = upstream_manager.get(upstream)
            current_data = current.model_dump()

            # Merge with existing healthchecks
            existing_healthchecks = current_data.get("healthchecks", {}) or {}
            if "active" in healthchecks:
                existing_active = existing_healthchecks.get("active", {}) or {}
                existing_active.update(healthchecks["active"])
                existing_healthchecks["active"] = existing_active
            if "passive" in healthchecks:
                existing_passive = existing_healthchecks.get("passive", {}) or {}
                existing_passive.update(healthchecks["passive"])
                existing_healthchecks["passive"] = existing_passive

            # Update upstream
            from system_operations_manager.integrations.kong.models.upstream import (
                Upstream,
            )

            updated_upstream = Upstream(
                name=current_data["name"],
                healthchecks=existing_healthchecks,
            )
            result = upstream_manager.update(upstream, updated_upstream)

            formatter = get_formatter(output, console)
            console.print("[green]Health check configuration updated[/green]\n")
            formatter.format_entity(result, title=f"Upstream: {upstream}")

        except KongAPIError as e:
            handle_kong_error(e)

    # Add health app to parent
    app.add_typer(health_app, name="health")
