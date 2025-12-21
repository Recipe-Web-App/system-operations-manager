"""Installation commands for system-operations-cli."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()

SHELL_RC = Path.home() / ".zshrc"
PATH_MARKER_START = "# system-operations-cli PATH"
PATH_MARKER_END = "# system-operations-cli PATH END"
MIN_PYTHON_VERSION = (3, 14)


def _check_python_version() -> bool:
    """Check if Python version meets minimum requirements."""
    current = sys.version_info[:2]
    if current < MIN_PYTHON_VERSION:
        console.print(
            f"[red]ERROR:[/red] Python >= {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} "
            f"required, found {current[0]}.{current[1]}"
        )
        return False
    console.print(f"[green]OK:[/green] Python version {current[0]}.{current[1]}")
    return True


def _get_venv_bin_path() -> Path | None:
    """Get the virtual environment bin path from Poetry."""
    try:
        result = subprocess.run(
            ["poetry", "env", "info", "--path"],
            capture_output=True,
            text=True,
            check=True,
        )
        venv_path = Path(result.stdout.strip())
        bin_path = venv_path / "bin"
        if bin_path.exists():
            console.print(f"[green]OK:[/green] Found venv bin at {bin_path}")
            return bin_path
        console.print(f"[red]ERROR:[/red] Venv bin directory not found at {bin_path}")
        return None
    except subprocess.CalledProcessError as e:
        console.print(f"[red]ERROR:[/red] Failed to get Poetry env info: {e.stderr}")
        return None
    except FileNotFoundError:
        console.print("[red]ERROR:[/red] Poetry is not installed or not in PATH")
        return None


def _read_shell_rc() -> str:
    """Read the shell RC file contents."""
    if SHELL_RC.exists():
        return SHELL_RC.read_text()
    return ""


def _write_shell_rc(content: str) -> None:
    """Write content to shell RC file."""
    SHELL_RC.write_text(content)


def _remove_existing_path_entry(content: str) -> str:
    """Remove existing PATH entry if present."""
    pattern = rf"\n?{re.escape(PATH_MARKER_START)}.*?{re.escape(PATH_MARKER_END)}\n?"
    return re.sub(pattern, "", content, flags=re.DOTALL)


def _add_path_entry(venv_bin: Path) -> bool:
    """Add venv bin to PATH in shell RC file."""
    content = _read_shell_rc()

    # Remove existing entry if present (idempotent)
    content = _remove_existing_path_entry(content)

    # Add new PATH entry
    path_block = f"""
{PATH_MARKER_START}
export PATH="{venv_bin}:$PATH"
{PATH_MARKER_END}
"""
    content = content.rstrip() + path_block

    _write_shell_rc(content)
    console.print(f"[green]OK:[/green] Added PATH entry to {SHELL_RC}")
    return True


def _verify_ops_executable(venv_bin: Path) -> bool:
    """Verify the ops executable exists."""
    ops_path = venv_bin / "ops"
    if ops_path.exists():
        console.print(f"[green]OK:[/green] Found ops executable at {ops_path}")
        return True
    console.print(f"[red]ERROR:[/red] ops executable not found at {ops_path}")
    return False


def install() -> None:
    """Install system-operations-cli and add to PATH."""
    console.print("\n[bold]Installing system-operations-cli...[/bold]\n")

    # Step 1: Check Python version
    if not _check_python_version():
        raise typer.Exit(1)

    # Step 2: Get venv bin path
    venv_bin = _get_venv_bin_path()
    if not venv_bin:
        raise typer.Exit(1)

    # Step 3: Verify ops executable exists
    if not _verify_ops_executable(venv_bin):
        console.print(
            "\n[yellow]Hint:[/yellow] Run 'poetry install' first to install dependencies."
        )
        raise typer.Exit(1)

    # Step 4: Add to PATH
    if not _add_path_entry(venv_bin):
        raise typer.Exit(1)

    # Success message
    console.print("\n[bold green]Installation complete![/bold green]\n")
    console.print("To start using 'ops', either:")
    console.print(f"  1. Run: [cyan]source {SHELL_RC}[/cyan]")
    console.print("  2. Open a new terminal window\n")
    console.print("Then verify with: [cyan]ops --version[/cyan]\n")


def uninstall() -> None:
    """Remove system-operations-cli from PATH."""
    console.print("\n[bold]Uninstalling system-operations-cli...[/bold]\n")

    content = _read_shell_rc()

    if PATH_MARKER_START not in content:
        console.print(f"[yellow]No PATH entry found in {SHELL_RC}[/yellow]")
        console.print("Nothing to uninstall.")
        return

    # Remove PATH entry
    content = _remove_existing_path_entry(content)
    _write_shell_rc(content)

    console.print(f"[green]OK:[/green] Removed PATH entry from {SHELL_RC}")
    console.print("\n[bold green]Uninstallation complete![/bold green]\n")
    console.print("To apply changes, either:")
    console.print(f"  1. Run: [cyan]source {SHELL_RC}[/cyan]")
    console.print("  2. Open a new terminal window\n")


if __name__ == "__main__":
    install()
