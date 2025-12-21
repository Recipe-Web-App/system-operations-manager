"""Status command for showing system status."""

from __future__ import annotations

import platform
from datetime import datetime
from pathlib import Path

import structlog
import typer
from rich.console import Console
from rich.table import Table

from system_operations_manager import __version__

console = Console()
logger = structlog.get_logger()

# XDG-compliant config location
CONFIG_DIR = Path.home() / ".config" / "ops"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def status(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed status information.",
    ),
) -> None:
    """Show system control status and health information."""
    logger.info("Checking system status", verbose=verbose)

    table = Table(title="System Control Status")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")

    # Core status
    table.add_row("CLI Version", __version__, "ops")
    table.add_row("Python", platform.python_version(), platform.python_implementation())
    table.add_row("Platform", platform.system(), platform.release())
    table.add_row("Time", datetime.now().isoformat(), "Local timezone")

    if verbose:
        # Add more detailed information
        table.add_row("Architecture", platform.machine(), platform.processor() or "N/A")
        table.add_row("Node", platform.node(), "Hostname")

    console.print(table)

    # Check for configuration
    if CONFIG_FILE.exists():
        console.print(f"\n[green]Configuration found:[/green] {CONFIG_FILE}")
    else:
        console.print(
            "\n[yellow]No configuration found.[/yellow] Run [bold]ops init[/bold] to create one."
        )

    logger.info("Status check complete")
