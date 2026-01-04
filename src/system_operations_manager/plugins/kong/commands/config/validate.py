"""Validate command for Kong declarative configuration.

This module provides the `config validate` command to validate a declarative
configuration file without applying it to Kong.
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


def register_validate_command(
    app: typer.Typer,
    get_config_manager: Callable[[], ConfigManager],
) -> None:
    """Register the config validate command.

    Args:
        app: Typer app to register the command with.
        get_config_manager: Factory function returning ConfigManager.
    """

    @app.command("validate")
    def config_validate(
        file: Annotated[
            Path,
            typer.Argument(help="Config file to validate (.yaml, .yml, or .json)"),
        ],
    ) -> None:
        """Validate a config file without applying.

        Performs the following checks:
        - YAML/JSON syntax validation
        - Schema validation (required fields, types)
        - Reference integrity (routes reference valid services, etc.)

        Examples:
            ops kong config validate kong.yaml
            ops kong config validate config.json
        """
        # Check file exists
        if not file.exists():
            console.print(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)

        # Parse file
        console.print(f"Validating {file}...\n")

        try:
            content = file.read_text()

            # Parse based on extension
            if file.suffix.lower() in (".yaml", ".yml"):
                try:
                    data = yaml.safe_load(content)
                except yaml.YAMLError as e:
                    console.print("[red]Error:[/red] Invalid YAML syntax")
                    console.print(f"  {e}")
                    raise typer.Exit(1) from None
            else:
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    console.print("[red]Error:[/red] Invalid JSON syntax")
                    console.print(f"  Line {e.lineno}, column {e.colno}: {e.msg}")
                    raise typer.Exit(1) from None

            if data is None:
                console.print("[red]Error:[/red] Empty configuration file")
                raise typer.Exit(1)

            # Schema validation via Pydantic
            try:
                config = DeclarativeConfig.model_validate(data)
            except PydanticValidationError as e:
                console.print("[red]Error:[/red] Schema validation failed\n")
                for error in e.errors():
                    loc = ".".join(str(x) for x in error["loc"])
                    console.print(f"  [red]{loc}:[/red] {error['msg']}")
                raise typer.Exit(1) from None

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to parse config: {e}")
            raise typer.Exit(1) from None

        # Reference validation via ConfigManager
        try:
            manager = get_config_manager()
            result = manager.validate_config(config)

            if result.valid:
                console.print("[green]Configuration is valid[/green]\n")

                # Show summary
                console.print("  [cyan]Configuration summary:[/cyan]")
                console.print(f"    Services:  {len(config.services)}")
                console.print(f"    Routes:    {len(config.routes)}")
                console.print(f"    Upstreams: {len(config.upstreams)}")
                console.print(f"    Consumers: {len(config.consumers)}")
                console.print(f"    Plugins:   {len(config.plugins)}")

                # Show warnings if any
                if result.warnings:
                    console.print("\n[yellow]Warnings:[/yellow]")
                    for warning in result.warnings:
                        console.print(f"  - {warning.path}: {warning.message}")

            else:
                console.print("[red]Configuration has errors:[/red]\n")

                table = Table(title="Validation Errors")
                table.add_column("Path", style="cyan")
                table.add_column("Entity", style="yellow")
                table.add_column("Message", style="red")

                for validation_err in result.errors:
                    entity = (
                        f"{validation_err.entity_type}:{validation_err.entity_name}"
                        if validation_err.entity_name
                        else "-"
                    )
                    table.add_row(validation_err.path, entity, validation_err.message)

                console.print(table)

                if result.warnings:
                    console.print("\n[yellow]Warnings:[/yellow]")
                    for warning in result.warnings:
                        console.print(f"  - {warning.path}: {warning.message}")

                raise typer.Exit(1)

        except KongAPIError as e:
            handle_kong_error(e)
