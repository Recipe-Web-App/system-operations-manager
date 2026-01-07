"""CLI commands for OpenAPI to Kong route synchronization.

This module provides commands for managing Kong routes from OpenAPI specs:
- sync-routes: Sync routes from OpenAPI spec to Kong
- diff: Preview changes without applying
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongNotFoundError,
)
from system_operations_manager.integrations.kong.models.openapi import (
    SyncChange,
    SyncResult,
)
from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    OutputOption,
    console,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter
from system_operations_manager.services.kong.openapi_sync_manager import (
    BreakingChangeError,
    OpenAPIParseError,
    OpenAPISyncManager,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kong.route_manager import RouteManager
    from system_operations_manager.services.kong.service_manager import ServiceManager


def register_openapi_commands(
    app: typer.Typer,
    get_sync_manager: Callable[[], OpenAPISyncManager],
    get_service_manager: Callable[[], ServiceManager],
    get_route_manager: Callable[[], RouteManager],
) -> None:
    """Register OpenAPI sync commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_sync_manager: Factory function that returns an OpenAPISyncManager.
        get_service_manager: Factory function that returns a ServiceManager.
        get_route_manager: Factory function that returns a RouteManager.
    """
    openapi_app = typer.Typer(
        name="openapi",
        help="OpenAPI specification management",
        no_args_is_help=True,
    )

    @openapi_app.command("sync-routes")
    def sync_routes(
        spec_file: Annotated[
            Path,
            typer.Argument(
                help="OpenAPI specification file (YAML or JSON)",
                exists=True,
                readable=True,
            ),
        ],
        service: Annotated[
            str,
            typer.Option("--service", "-s", help="Kong service name (required)"),
        ],
        path_prefix: Annotated[
            str | None,
            typer.Option("--path-prefix", help="Prefix to add to all route paths"),
        ] = None,
        strip_path: Annotated[
            bool,
            typer.Option(
                "--strip-path/--no-strip-path",
                help="Strip matched path when proxying",
            ),
        ] = True,
        dry_run: Annotated[
            bool,
            typer.Option("--dry-run", help="Preview changes without applying"),
        ] = False,
        force: ForceOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Sync Kong routes from an OpenAPI specification.

        Creates, updates, or deletes routes to match the OpenAPI spec.
        Routes are named using the pattern: {service}-{operationId}

        Breaking changes (require --force):
        - Removed paths (routes that exist in Kong but not in spec)
        - Removed HTTP methods from existing routes
        - Path structure changes

        Examples:
            ops kong openapi sync-routes api-spec.yaml --service auth-service
            ops kong openapi sync-routes api-spec.yaml --service auth-service --dry-run
            ops kong openapi sync-routes api-spec.yaml --service auth-service --force
            ops kong openapi sync-routes api.json --service my-api --path-prefix /v2
        """
        try:
            manager = get_sync_manager()

            # Parse OpenAPI spec
            console.print(f"[dim]Parsing {spec_file.name}...[/dim]")
            spec = manager.parse_openapi(spec_file)
            console.print(
                f"[green]Parsed:[/green] {spec.title} v{spec.version} "
                f"({len(spec.operations)} operations)"
            )

            # Verify service exists
            try:
                service_manager = get_service_manager()
                service_manager.get(service)
            except KongNotFoundError:
                console.print(f"[red]Error:[/red] Service '{service}' not found in Kong")
                raise typer.Exit(1) from None

            # Generate route mappings
            mappings = manager.generate_route_mappings(
                spec,
                service,
                path_prefix=path_prefix,
                strip_path=strip_path,
            )
            console.print(f"[dim]Generated {len(mappings)} route mappings[/dim]\n")

            # Calculate diff
            result = manager.calculate_diff(service, mappings)

            if not result.has_changes:
                console.print("[green]No changes needed - routes are in sync[/green]")
                return

            # Display changes
            _display_sync_result(result, output)

            # Handle dry run
            if dry_run:
                console.print("\n[yellow]Dry run - no changes applied[/yellow]")
                return

            # Handle breaking changes
            if result.has_breaking_changes and not force:
                console.print(
                    "\n[yellow]Breaking changes detected![/yellow] "
                    "Use [bold]--force[/bold] to apply."
                )
                raise typer.Exit(1)

            # Apply changes
            console.print("\n[dim]Applying changes...[/dim]")
            apply_result = manager.apply_sync(result, force=force)

            # Display results
            if apply_result.all_succeeded:
                console.print(
                    f"\n[green]Successfully applied {len(apply_result.succeeded)} change(s)[/green]"
                )
            else:
                console.print(
                    f"\n[yellow]Applied {len(apply_result.succeeded)} change(s), "
                    f"{len(apply_result.failed)} failed[/yellow]"
                )
                for op in apply_result.failed:
                    console.print(f"  [red]Failed:[/red] {op.route_name}: {op.error}")
                raise typer.Exit(1)

        except OpenAPIParseError as e:
            console.print(f"[red]Error parsing OpenAPI spec:[/red] {e}")
            if e.parse_error:
                console.print(f"[dim]{e.parse_error}[/dim]")
            raise typer.Exit(1) from None
        except BreakingChangeError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KongAPIError as e:
            handle_kong_error(e)

    @openapi_app.command("diff")
    def diff_routes(
        spec_file: Annotated[
            Path,
            typer.Argument(
                help="OpenAPI specification file (YAML or JSON)",
                exists=True,
                readable=True,
            ),
        ],
        service: Annotated[
            str,
            typer.Option("--service", "-s", help="Kong service name (required)"),
        ],
        path_prefix: Annotated[
            str | None,
            typer.Option("--path-prefix", help="Prefix to add to all route paths"),
        ] = None,
        strip_path: Annotated[
            bool,
            typer.Option(
                "--strip-path/--no-strip-path",
                help="Strip matched path when proxying",
            ),
        ] = True,
        verbose: Annotated[
            bool,
            typer.Option("--verbose", "-v", help="Show detailed field changes"),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show diff between OpenAPI spec and current Kong routes.

        Preview what would change if sync-routes is run.

        Examples:
            ops kong openapi diff api-spec.yaml --service auth-service
            ops kong openapi diff api-spec.yaml --service auth-service --verbose
            ops kong openapi diff api-spec.yaml --service auth-service --output json
        """
        try:
            manager = get_sync_manager()

            # Parse OpenAPI spec
            console.print(f"[dim]Parsing {spec_file.name}...[/dim]")
            spec = manager.parse_openapi(spec_file)

            # Verify service exists
            try:
                service_manager = get_service_manager()
                service_manager.get(service)
            except KongNotFoundError:
                console.print(f"[red]Error:[/red] Service '{service}' not found in Kong")
                raise typer.Exit(1) from None

            # Generate route mappings
            mappings = manager.generate_route_mappings(
                spec,
                service,
                path_prefix=path_prefix,
                strip_path=strip_path,
            )

            # Calculate diff
            result = manager.calculate_diff(service, mappings)

            if output == OutputFormat.TABLE:
                if not result.has_changes:
                    console.print("[green]No changes - routes are in sync[/green]")
                    return
                _display_sync_result(result, output, verbose=verbose)
            else:
                # JSON/YAML output
                formatter = get_formatter(output, console)
                data = {
                    "service": result.service_name,
                    "summary": {
                        "creates": len(result.creates),
                        "updates": len(result.updates),
                        "deletes": len(result.deletes),
                        "breaking_changes": len(result.breaking_changes),
                    },
                    "creates": [_change_to_dict(c) for c in result.creates],
                    "updates": [_change_to_dict(c, include_changes=True) for c in result.updates],
                    "deletes": [_change_to_dict(c) for c in result.deletes],
                }
                formatter.format_dict(data, title=f"Sync Diff: {service}")

        except OpenAPIParseError as e:
            console.print(f"[red]Error parsing OpenAPI spec:[/red] {e}")
            raise typer.Exit(1) from None
        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(openapi_app, name="openapi")


def _display_sync_result(
    result: SyncResult,
    output: OutputFormat,
    *,
    verbose: bool = False,
) -> None:
    """Display sync result in table format.

    Args:
        result: Sync result to display.
        output: Output format.
        verbose: Show detailed field changes.
    """
    if output != OutputFormat.TABLE:
        return

    # Summary panel
    breaking_count = len(result.breaking_changes)
    summary = (
        f"Creates: [green]{len(result.creates)}[/green]  "
        f"Updates: [yellow]{len(result.updates)}[/yellow]  "
        f"Deletes: [red]{len(result.deletes)}[/red]"
    )
    if breaking_count > 0:
        summary += f"  ([red]{breaking_count} breaking[/red])"

    console.print(Panel(summary, title=f"Sync Preview: {result.service_name}"))

    # Creates table
    if result.creates:
        table = Table(title="[green]Creates[/green]", show_header=True)
        table.add_column("Route Name", style="cyan")
        table.add_column("Path")
        table.add_column("Methods")
        table.add_column("Tags", style="dim")

        for change in result.creates:
            table.add_row(
                change.route_name,
                change.path,
                ", ".join(change.methods),
                ", ".join(change.tags[:3]) + ("..." if len(change.tags) > 3 else ""),
            )
        console.print(table)

    # Updates table
    if result.updates:
        table = Table(title="[yellow]Updates[/yellow]", show_header=True)
        table.add_column("Route Name", style="cyan")
        table.add_column("Changes")
        table.add_column("Breaking", style="red")

        for change in result.updates:
            changes_str = _format_field_changes(change, verbose)
            breaking_str = change.breaking_reason if change.is_breaking else ""
            table.add_row(change.route_name, changes_str, breaking_str)
        console.print(table)

    # Deletes table
    if result.deletes:
        table = Table(title="[red]Deletes[/red]", show_header=True)
        table.add_column("Route Name", style="cyan")
        table.add_column("Path")
        table.add_column("Methods")
        table.add_column("Warning", style="red")

        for change in result.deletes:
            table.add_row(
                change.route_name,
                change.path,
                ", ".join(change.methods),
                "BREAKING" if change.is_breaking else "",
            )
        console.print(table)


def _format_field_changes(change: SyncChange, verbose: bool) -> str:
    """Format field changes for display.

    Args:
        change: Sync change with field changes.
        verbose: Show detailed changes.

    Returns:
        Formatted string describing changes.
    """
    if not change.field_changes:
        return "No field changes"

    parts = []
    for field, (old, new) in change.field_changes.items():
        if verbose:
            parts.append(f"{field}: {old} -> {new}")
        else:
            parts.append(field)

    return ", ".join(parts)


def _change_to_dict(change: SyncChange, *, include_changes: bool = False) -> dict[str, object]:
    """Convert a SyncChange to a dictionary for JSON/YAML output.

    Args:
        change: Change to convert.
        include_changes: Include field_changes in output.

    Returns:
        Dictionary representation.
    """
    data = {
        "operation": change.operation,
        "route_name": change.route_name,
        "path": change.path,
        "methods": change.methods,
        "tags": change.tags,
        "is_breaking": change.is_breaking,
    }
    if change.breaking_reason:
        data["breaking_reason"] = change.breaking_reason
    if include_changes and change.field_changes:
        data["field_changes"] = {
            k: {"old": v[0], "new": v[1]} for k, v in change.field_changes.items()
        }
    return data
