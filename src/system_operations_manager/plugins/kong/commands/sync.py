"""CLI commands for Kong/Konnect sync status.

This module provides commands for checking sync status between
Kong Gateway (data plane) and Konnect (control plane):
- status: Show drift report between Gateway and Konnect
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.plugins.kong.commands.base import (
    OutputOption,
    console,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.unified_query import UnifiedQueryService


def _display_sync_status_table(
    summary: dict[str, dict[str, int]],
    entity_types: list[str],
    unified_service: UnifiedQueryService,
) -> None:
    """Display sync status as a formatted table."""
    from system_operations_manager.cli.output import Table
    from system_operations_manager.integrations.kong.models.unified import (
        UnifiedEntityList,
    )

    console.print("\n[bold]Sync Status Report[/bold]")
    console.print("=" * 50)

    # Summary table
    table = Table(title="Entity Sync Summary", show_header=True)
    table.add_column("Entity Type", style="cyan")
    table.add_column("Total", justify="right")
    table.add_column("Gateway Only", justify="right", style="blue")
    table.add_column("Konnect Only", justify="right", style="green")
    table.add_column("Synced", justify="right", style="green")
    table.add_column("With Drift", justify="right", style="yellow")

    totals = {
        "total": 0,
        "gateway_only": 0,
        "konnect_only": 0,
        "synced": 0,
        "drift": 0,
    }

    for etype in entity_types:
        if etype not in summary:
            continue
        stats = summary[etype]
        table.add_row(
            etype.capitalize(),
            str(stats["total"]),
            str(stats["gateway_only"]) if stats["gateway_only"] > 0 else "-",
            str(stats["konnect_only"]) if stats["konnect_only"] > 0 else "-",
            str(stats["synced"]) if stats["synced"] > 0 else "-",
            str(stats["drift"]) if stats["drift"] > 0 else "-",
        )
        totals["total"] += stats["total"]
        totals["gateway_only"] += stats["gateway_only"]
        totals["konnect_only"] += stats["konnect_only"]
        totals["synced"] += stats["synced"]
        totals["drift"] += stats["drift"]

    # Add totals row
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{totals['total']}[/bold]",
        f"[bold blue]{totals['gateway_only']}[/bold blue]" if totals["gateway_only"] > 0 else "-",
        f"[bold green]{totals['konnect_only']}[/bold green]" if totals["konnect_only"] > 0 else "-",
        f"[bold green]{totals['synced']}[/bold green]" if totals["synced"] > 0 else "-",
        f"[bold yellow]{totals['drift']}[/bold yellow]" if totals["drift"] > 0 else "-",
    )

    console.print(table)

    def _get_entities(etype: str) -> UnifiedEntityList[Any]:
        """Get entities for a given type."""
        if etype == "services":
            return unified_service.list_services()
        elif etype == "routes":
            return unified_service.list_routes()
        elif etype == "consumers":
            return unified_service.list_consumers()
        elif etype == "plugins":
            return unified_service.list_plugins()
        elif etype == "upstreams":
            return unified_service.list_upstreams()
        else:
            return UnifiedEntityList(entities=[])

    # Show detailed drift info if any
    if totals["drift"] > 0:
        console.print("\n[bold yellow]Entities with Configuration Drift:[/bold yellow]")
        for etype in entity_types:
            if etype not in summary or summary[etype]["drift"] == 0:
                continue

            entities = _get_entities(etype)
            drifted = entities.with_drift
            if drifted:
                console.print(f"\n  [cyan]{etype.capitalize()}:[/cyan]")
                for unified_entity in drifted:
                    name = unified_entity.identifier
                    drift_fields = unified_entity.drift_fields or []
                    console.print(f"    - {name}: [yellow]{', '.join(drift_fields)}[/yellow]")

    # Show gateway-only entities
    if totals["gateway_only"] > 0:
        console.print("\n[bold blue]Entities only in Gateway (not in Konnect):[/bold blue]")
        for etype in entity_types:
            if etype not in summary or summary[etype]["gateway_only"] == 0:
                continue

            entities = _get_entities(etype)
            gateway_only = entities.gateway_only
            if gateway_only:
                console.print(f"\n  [cyan]{etype.capitalize()}:[/cyan]")
                for unified_entity in gateway_only[:5]:  # Limit to 5
                    console.print(f"    - {unified_entity.identifier}")
                if len(gateway_only) > 5:
                    console.print(f"    [dim]... and {len(gateway_only) - 5} more[/dim]")

    # Show konnect-only entities
    if totals["konnect_only"] > 0:
        console.print("\n[bold green]Entities only in Konnect (not in Gateway):[/bold green]")
        for etype in entity_types:
            if etype not in summary or summary[etype]["konnect_only"] == 0:
                continue

            entities = _get_entities(etype)
            konnect_only = entities.konnect_only
            if konnect_only:
                console.print(f"\n  [cyan]{etype.capitalize()}:[/cyan]")
                for unified_entity in konnect_only[:5]:  # Limit to 5
                    console.print(f"    - {unified_entity.identifier}")
                if len(konnect_only) > 5:
                    console.print(f"    [dim]... and {len(konnect_only) - 5} more[/dim]")

    console.print()


def register_sync_commands(
    app: typer.Typer,
    get_unified_query_service: Callable[[], UnifiedQueryService | None],
) -> None:
    """Register sync commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_unified_query_service: Factory function that returns a UnifiedQueryService.
    """
    sync_app = typer.Typer(
        name="sync",
        help="Sync and drift detection between Gateway and Konnect",
        no_args_is_help=True,
    )

    @sync_app.command("status")
    def sync_status(
        entity_type: Annotated[
            str | None,
            typer.Option(
                "--type",
                "-t",
                help="Entity type to check (services, routes, consumers, plugins, upstreams)",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show drift between Gateway and Konnect.

        Displays:
        - Entities only in Gateway (not synced to Konnect)
        - Entities only in Konnect (not in Gateway)
        - Entities in both with configuration drift
        - Fully synced entities

        Examples:
            ops kong sync status
            ops kong sync status --type services
            ops kong sync status --output json
        """
        unified_service = get_unified_query_service()

        if unified_service is None:
            console.print(
                "[yellow]Konnect not configured.[/yellow] "
                "Configure Konnect in ops.yaml to use sync status."
            )
            console.print("\nExample configuration:")
            console.print("[dim]konnect:[/dim]")
            console.print("[dim]  api_key: ${KONNECT_API_KEY}[/dim]")
            console.print("[dim]  default_control_plane: my-control-plane[/dim]")
            raise typer.Exit(1)

        formatter = get_formatter(output, console)

        # Determine which entity types to check
        if entity_type:
            valid_types = ["services", "routes", "consumers", "plugins", "upstreams"]
            if entity_type not in valid_types:
                console.print(
                    f"[red]Invalid entity type:[/red] {entity_type}\n"
                    f"Valid types: {', '.join(valid_types)}"
                )
                raise typer.Exit(1)
            entity_types = [entity_type]
        else:
            entity_types = ["services", "routes", "consumers", "plugins", "upstreams"]

        # Get sync summary
        summary = unified_service.get_sync_summary(entity_types)

        if output == OutputFormat.TABLE:
            _display_sync_status_table(summary, entity_types, unified_service)
        else:
            formatter.format_dict(summary, title="Sync Status")

    app.add_typer(sync_app, name="sync")
