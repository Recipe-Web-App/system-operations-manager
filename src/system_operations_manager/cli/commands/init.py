"""Init command for initializing a new project."""

from __future__ import annotations

import structlog
import typer
from rich.console import Console
from rich.panel import Panel

from system_operations_manager.core.config.models import (
    CONFIG_DIR,
    CONFIG_FILE,
    SystemConfig,
)

app = typer.Typer(help="Initialize a new system control project.")
console = Console()
logger = structlog.get_logger()


@app.callback(invoke_without_command=True)
def init(
    ctx: typer.Context,
    template: str = typer.Option(
        "default",
        "--template",
        "-t",
        help="Template to use for initialization.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration.",
    ),
) -> None:
    """Initialize system control configuration in ~/.config/ops/."""
    if ctx.invoked_subcommand is not None:
        return

    logger.info("Initializing config", path=str(CONFIG_FILE), template=template)

    # Create config directory if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_FILE.exists() and not force:
        console.print(f"[yellow]Configuration already exists at {CONFIG_FILE}[/yellow]")
        console.print("Use --force to overwrite.")
        raise typer.Exit(code=1)

    # Create validated default configuration
    config = SystemConfig()
    CONFIG_FILE.write_text(config.to_yaml())

    console.print(
        Panel(
            f"[green]Configuration initialized successfully![/green]\n\n"
            f"Configuration created at: {CONFIG_FILE}\n\n"
            f"Next steps:\n"
            f"  1. Edit {CONFIG_FILE} to customize your configuration\n"
            f"  2. Run [bold]ops status[/bold] to verify setup",
            title="ops init",
            border_style="green",
        )
    )

    logger.info("Configuration initialized", config_file=str(CONFIG_FILE))
