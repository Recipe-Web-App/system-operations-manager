"""Status command for showing system status."""

from __future__ import annotations

import platform
from datetime import datetime

import structlog
import typer
from pydantic import ValidationError
from rich.console import Console

from system_operations_manager import __version__
from system_operations_manager.cli.output import Table
from system_operations_manager.core.config.models import CONFIG_FILE, load_config

console = Console()
logger = structlog.get_logger()


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

    # Check and validate configuration
    try:
        config = load_config()
        if config:
            console.print(f"\n[green]Configuration valid:[/green] {CONFIG_FILE}")
            if verbose:
                console.print(f"  Environment: {config.environment}")
                console.print(f"  Plugins: {', '.join(config.plugins.enabled)}")
        else:
            console.print(
                "\n[yellow]No configuration found.[/yellow] Run [bold]ops init[/bold] to create one."
            )
    except (ValidationError, ValueError) as e:
        console.print(f"\n[red]Configuration invalid:[/red] {CONFIG_FILE}")
        console.print(f"  Error: {e}")
        console.print("  Run [bold]ops init --force[/bold] to regenerate.")

    logger.info("Status check complete")
