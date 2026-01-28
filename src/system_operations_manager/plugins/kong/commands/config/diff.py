"""Diff command for Kong declarative configuration.

This module provides the `config diff` command to show what changes would
be applied if a configuration file were applied to Kong.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import yaml
from pydantic import ValidationError as PydanticValidationError

from system_operations_manager.cli.output import Table
from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.config import (
    ConfigDiffSummary,
    DeclarativeConfig,
)
from system_operations_manager.plugins.kong.commands.base import (
    OutputOption,
    console,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.config_manager import ConfigManager


def register_diff_command(
    app: typer.Typer,
    get_config_manager: Callable[[], ConfigManager],
) -> None:
    """Register the config diff command.

    Args:
        app: Typer app to register the command with.
        get_config_manager: Factory function returning ConfigManager.
    """

    @app.command("diff")
    def config_diff(
        file: Annotated[
            Path,
            typer.Argument(help="Config file to compare (.yaml, .yml, or .json)"),
        ],
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose",
                "-v",
                help="Show field-level changes for updates",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show what would change if config is applied.

        Compares the configuration file with the current Kong state and shows
        which entities would be created, updated, or deleted.

        Examples:
            ops kong config diff kong.yaml
            ops kong config diff kong.yaml --verbose
            ops kong config diff kong.yaml --output json
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
            diff = manager.diff_config(config)

            if diff.total_changes == 0:
                console.print("[green]No changes required - configuration is in sync[/green]")
                raise typer.Exit(0)

            if output == OutputFormat.TABLE:
                _display_diff_table(diff, verbose)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(
                    diff.model_dump(exclude_none=True),
                    title="Configuration Diff",
                )

        except KongAPIError as e:
            handle_kong_error(e)


def _display_diff_table(diff: ConfigDiffSummary, verbose: bool) -> None:
    """Display diff in table format.

    Args:
        diff: Diff summary to display.
        verbose: Whether to show field-level changes.
    """

    # Summary table
    summary_table = Table(title="Change Summary")
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
                str(creates) if creates else "-",
                str(updates) if updates else "-",
                str(deletes) if deletes else "-",
            )

    console.print(summary_table)
    console.print(f"\n[bold]Total changes:[/bold] {diff.total_changes}")

    # Detailed changes
    if verbose and diff.diffs:
        console.print("\n[bold]Detailed Changes:[/bold]\n")

        for d in diff.diffs:
            op_style = {
                "create": "green",
                "update": "yellow",
                "delete": "red",
            }.get(d.operation, "white")

            console.print(
                f"  [{op_style}]{d.operation.upper():6}[/{op_style}] "
                f"[cyan]{d.entity_type}[/cyan]: {d.id_or_name}"
            )

            # Show field changes for updates
            if d.operation == "update" and d.changes:
                for field, (old_val, new_val) in d.changes.items():
                    old_display = _format_value(old_val)
                    new_display = _format_value(new_val)
                    console.print(
                        f"           {field}: [red]{old_display}[/red] -> [green]{new_display}[/green]"
                    )

    elif diff.diffs:
        # Non-verbose: just list entities
        console.print("\n[dim]Use --verbose to see field-level changes[/dim]")

    # Next steps
    console.print("\n[dim]Run 'ops kong config apply <file>' to apply these changes[/dim]")


def _format_value(value: object) -> str:
    """Format a value for display.

    Args:
        value: Value to format.

    Returns:
        String representation.
    """
    if value is None:
        return "(none)"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        if not value:
            return "[]"
        if len(value) <= 3:
            return str(value)
        return f"[{len(value)} items]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        return f"{{{len(value)} keys}}"
    return str(value)
