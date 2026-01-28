"""Built-in core plugin providing fundamental functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from rich.console import Console

from system_operations_manager.cli.output import Table
from system_operations_manager.core.plugins.base import Plugin, hookimpl

if TYPE_CHECKING:
    pass

console = Console()


class CorePlugin(Plugin):
    """Core plugin providing basic system control functionality."""

    name = "core"
    version = "0.1.0"
    description = "Core system control functionality"

    def on_initialize(self) -> None:
        """Initialize core plugin."""

    @hookimpl
    def register_commands(self, app: typer.Typer) -> None:
        """Register core commands."""

        @app.command("plugins")
        def list_plugins() -> None:
            """List all available plugins."""
            table = Table(title="Installed Plugins")
            table.add_column("Name", style="cyan")
            table.add_column("Version", style="green")
            table.add_column("Description")

            # For now, just show this plugin
            # In a full implementation, this would access the plugin manager
            table.add_row(self.name, self.version, self.description)

            console.print(table)
