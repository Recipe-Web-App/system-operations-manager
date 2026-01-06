"""Apply command for Kong declarative configuration.

This module provides the `config apply` command to apply a declarative
configuration file to Kong, making the actual state match the desired state.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import yaml
from pydantic import ValidationError as PydanticValidationError
from rich.table import Table

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.config import DeclarativeConfig
from system_operations_manager.plugins.kong.commands.base import console, handle_kong_error

if TYPE_CHECKING:
    from system_operations_manager.services.kong.config_manager import ConfigManager


def register_apply_command(
    app: typer.Typer,
    get_config_manager: Callable[[], ConfigManager],
) -> None:
    """Register the config apply command.

    Args:
        app: Typer app to register the command with.
        get_config_manager: Factory function returning ConfigManager.
    """

    @app.command("apply")
    def config_apply(
        file: Annotated[
            Path,
            typer.Argument(help="Config file to apply (.yaml, .yml, or .json)"),
        ],
        confirm: Annotated[
            bool,
            typer.Option(
                "--confirm/--no-confirm",
                help="Require confirmation before applying (default: yes)",
            ),
        ] = True,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Show what would be changed without applying",
            ),
        ] = False,
    ) -> None:
        """Apply declarative config to Kong.

        Reads the configuration file, validates it, shows what changes would be
        made, and applies them to Kong in the correct dependency order.

        Entities are applied in this order:
        1. Services, Upstreams (no dependencies)
        2. Routes (depend on services)
        3. Consumers (no dependencies)
        4. Plugins (depend on services, routes, consumers)

        Deletions are performed in reverse order.

        Examples:
            ops kong config apply kong.yaml
            ops kong config apply kong.yaml --dry-run
            ops kong config apply kong.yaml --no-confirm
        """
        # Check file exists
        if not file.exists():
            console.print(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)

        # Parse file
        try:
            content = file.read_text()

            if file.suffix.lower() in (".yaml", ".yml"):
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)

            if data is None:
                console.print("[red]Error:[/red] Empty configuration file")
                raise typer.Exit(1)

            config = DeclarativeConfig.model_validate(data)

        except yaml.YAMLError as e:
            console.print(f"[red]Error:[/red] Invalid YAML syntax: {e}")
            raise typer.Exit(1) from None
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON syntax: {e}")
            raise typer.Exit(1) from None
        except PydanticValidationError as e:
            console.print(f"[red]Error:[/red] Invalid configuration: {e}")
            raise typer.Exit(1) from None

        try:
            manager = get_config_manager()

            # Validate first
            console.print("Validating configuration...")
            validation = manager.validate_config(config)
            if not validation.valid:
                console.print(
                    "[red]Configuration validation failed.[/red] "
                    "Run 'ops kong config validate' for details."
                )
                raise typer.Exit(1)
            console.print("[green]Configuration is valid.[/green]\n")

            # Show warnings
            if validation.warnings:
                console.print("[yellow]Warnings:[/yellow]")
                for warning in validation.warnings:
                    console.print(f"  - {warning.message}")
                console.print()

            # Calculate diff
            diff = manager.diff_config(config)

            if diff.total_changes == 0:
                console.print("[green]No changes required - configuration is in sync[/green]")
                raise typer.Exit(0)

            # Display summary
            console.print("[bold]Changes to apply:[/bold]\n")

            summary_table = Table()
            summary_table.add_column("Entity Type", style="cyan")
            summary_table.add_column("Create", style="green")
            summary_table.add_column("Update", style="yellow")
            summary_table.add_column("Delete", style="red")

            entity_types = ["services", "routes", "upstreams", "consumers", "plugins"]
            for entity_type in entity_types:
                creates = diff.creates.get(entity_type, 0)
                updates = diff.updates.get(entity_type, 0)
                deletes = diff.deletes.get(entity_type, 0)
                if creates or updates or deletes:
                    summary_table.add_row(
                        entity_type.capitalize(),
                        f"+{creates}" if creates else "-",
                        f"~{updates}" if updates else "-",
                        f"-{deletes}" if deletes else "-",
                    )

            console.print(summary_table)
            console.print(f"\n[bold]Total:[/bold] {diff.total_changes} changes\n")

            # Dry run exits here
            if dry_run:
                console.print("[yellow]Dry run - no changes applied[/yellow]")
                console.print("\n[dim]Run without --dry-run to apply these changes[/dim]")
                raise typer.Exit(0)

            # Confirm
            if confirm and not typer.confirm("Apply these changes?", default=False):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            # Apply - use sync_config for DB-less mode, apply_config otherwise
            console.print("\nApplying changes...")

            if manager.is_dbless_mode():
                # DB-less mode: use /config endpoint
                try:
                    manager.sync_config(config)
                    console.print("\n[green]Successfully synced configuration[/green]")
                except KongAPIError as e:
                    console.print(f"\n[red]Failed to sync configuration: {e}[/red]")
                    raise typer.Exit(1) from None
            else:
                # Database mode: use individual entity endpoints
                operations = manager.apply_config(config, dry_run=False)

                # Report results
                successful = [o for o in operations if o.result == "success"]
                failed = [o for o in operations if o.result == "failed"]

                if failed:
                    console.print(
                        f"\n[yellow]Completed with errors: "
                        f"{len(successful)} successful, {len(failed)} failed[/yellow]\n"
                    )

                    error_table = Table(title="Failed Operations")
                    error_table.add_column("Operation", style="red")
                    error_table.add_column("Entity", style="cyan")
                    error_table.add_column("Error", style="dim")

                    for op in failed:
                        error_table.add_row(
                            op.operation.upper(),
                            f"{op.entity_type}/{op.id_or_name}",
                            op.error or "Unknown error",
                        )

                    console.print(error_table)
                    raise typer.Exit(1)
                else:
                    console.print(
                        f"\n[green]Successfully applied {len(successful)} operations[/green]"
                    )

        except KongAPIError as e:
            handle_kong_error(e)
