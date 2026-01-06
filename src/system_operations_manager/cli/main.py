"""Main CLI entry point using Typer."""

from __future__ import annotations

import typer
from rich.console import Console

from system_operations_manager import __version__
from system_operations_manager.cli.commands import init, status
from system_operations_manager.core.plugins.manager import PluginManager
from system_operations_manager.logging.config import configure_logging

app = typer.Typer(
    name="ops",
    help="System Control CLI for managing distributed systems.",
    add_completion=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"ops version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode.",
    ),
) -> None:
    """System Control CLI - Manage distributed systems with ease."""
    configure_logging(verbose=verbose, debug=debug)


# Register subcommands
app.add_typer(init.app, name="init")
app.command()(status.status)

# Plugin manager instance
plugin_manager = PluginManager()


def _load_plugins() -> None:
    """Discover and load all available plugins."""
    discovered = plugin_manager.discover_plugins()
    for name in discovered:
        plugin_manager.load_plugin(name)
    plugin_manager.initialize_all({})
    plugin_manager.register_commands(app)


# Load plugins at module initialization
_load_plugins()


def cli() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli()
