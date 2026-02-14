"""Installation commands for system-operations-cli using pipx."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()

MIN_PYTHON_VERSION = (3, 14)
PACKAGE_NAME = "system-operations-cli"

# Legacy markers from the old PATH-injection approach
_LEGACY_MARKER_START = "# system-operations-cli PATH"
_LEGACY_MARKER_END = "# system-operations-cli PATH END"


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


def _find_pipx() -> str | None:
    """Find the pipx executable."""
    pipx_path = shutil.which("pipx")
    if pipx_path:
        console.print(f"[green]OK:[/green] Found pipx at {pipx_path}")
        return pipx_path
    console.print("[red]ERROR:[/red] pipx is not installed or not in PATH")
    console.print(
        "\n[yellow]Install pipx with:[/yellow]\n"
        "  python3 -m pip install --user pipx\n"
        "  python3 -m pipx ensurepath\n"
    )
    return None


def _find_python_for_pipx() -> str | None:
    """Find a Python >= 3.14 interpreter path for pipx to use."""
    for candidate in ["python3.14", "python3"]:
        path = shutil.which(candidate)
        if path:
            try:
                result = subprocess.run(
                    [
                        path,
                        "-c",
                        "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                major, minor = result.stdout.strip().split(".")
                if (int(major), int(minor)) >= MIN_PYTHON_VERSION:
                    return path
            except subprocess.CalledProcessError, ValueError:
                continue
    return None


def _get_project_path() -> Path:
    """Get the project root path (directory containing pyproject.toml)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path.cwd()


def _is_installed_via_pipx() -> bool:
    """Check if the package is already installed via pipx."""
    try:
        result = subprocess.run(
            ["pipx", "list", "--short"],
            capture_output=True,
            text=True,
            check=True,
        )
        return PACKAGE_NAME in result.stdout
    except subprocess.CalledProcessError, FileNotFoundError:
        return False


def _cleanup_legacy_path_entry() -> None:
    """Remove legacy PATH entries from shell RC files if present."""
    for rc_file in [Path.home() / ".zshrc", Path.home() / ".bashrc"]:
        if not rc_file.exists():
            continue
        content = rc_file.read_text()
        if _LEGACY_MARKER_START in content:
            pattern = rf"\n?{re.escape(_LEGACY_MARKER_START)}.*?{re.escape(_LEGACY_MARKER_END)}\n?"
            cleaned = re.sub(pattern, "", content, flags=re.DOTALL)
            rc_file.write_text(cleaned)
            console.print(f"[green]OK:[/green] Removed legacy PATH entry from {rc_file}")


def _install_shell_completion() -> bool:
    """Install shell completion using Typer's built-in support."""
    ops_path = shutil.which("ops")
    if not ops_path:
        console.print("[yellow]WARN:[/yellow] ops not found on PATH; skipping shell completion")
        console.print("  You can manually run: ops --install-completion")
        return False

    shell = os.environ.get("SHELL", "")
    shell_name = Path(shell).name if shell else ""

    if shell_name not in ("zsh", "bash", "fish"):
        console.print(
            f"[yellow]WARN:[/yellow] Unsupported shell '{shell_name}' for auto-completion"
        )
        console.print("  You can manually run: ops --install-completion")
        return False

    try:
        result = subprocess.run(
            [ops_path, "--install-completion", shell_name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print(f"[green]OK:[/green] Shell completion installed for {shell_name}")
            return True
        if "already" in (result.stderr + result.stdout).lower():
            console.print(f"[green]OK:[/green] Shell completion already installed for {shell_name}")
            return True
        console.print(f"[yellow]WARN:[/yellow] Could not install shell completion: {result.stderr}")
        return False
    except Exception as e:
        console.print(f"[yellow]WARN:[/yellow] Could not install shell completion: {e}")
        return False


def install(
    editable: bool = typer.Option(
        False, "--editable", "-e", help="Install in editable/development mode."
    ),
    extras: str = typer.Option(
        "", "--extras", help="Comma-separated extras to install (e.g. 'kubernetes,monitoring')."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force reinstall if already installed."
    ),
    python: str = typer.Option("", "--python", help="Path to Python interpreter for pipx venv."),
) -> None:
    """Install system-operations-cli globally using pipx."""
    console.print("\n[bold]Installing system-operations-cli via pipx...[/bold]\n")

    # Step 1: Check Python version
    if not _check_python_version():
        raise typer.Exit(1)

    # Step 2: Clean up any legacy PATH entries
    _cleanup_legacy_path_entry()

    # Step 3: Verify pipx is available
    pipx_path = _find_pipx()
    if not pipx_path:
        raise typer.Exit(1)

    # Step 4: Check if already installed
    if _is_installed_via_pipx() and not force:
        console.print(f"[yellow]{PACKAGE_NAME} is already installed via pipx.[/yellow]")
        console.print("Use --force to reinstall, or run: pipx upgrade system-operations-cli")
        raise typer.Exit(0)

    # Step 5: Find Python >= 3.14 for pipx
    python_path = python or _find_python_for_pipx()
    if not python_path:
        console.print("[red]ERROR:[/red] Could not find Python >= 3.14 interpreter")
        console.print("Specify one with --python /path/to/python3.14")
        raise typer.Exit(1)
    console.print(f"[green]OK:[/green] Using Python interpreter: {python_path}")

    # Step 6: Build the pipx install command
    project_path = _get_project_path()
    package_spec = str(project_path)
    if extras:
        package_spec = f"{project_path}[{extras}]"

    cmd = [pipx_path, "install", package_spec, "--python", python_path]
    if editable:
        cmd.append("--editable")
    if force:
        cmd.append("--force")

    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")

    # Step 7: Run pipx install
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as err:
        console.print("\n[red]ERROR:[/red] pipx install failed. See output above.")
        raise typer.Exit(1) from err

    # Step 8: Install shell completion
    _install_shell_completion()

    # Success message
    console.print("\n[bold green]Installation complete![/bold green]\n")
    console.print("The 'ops' command is now available globally.")
    console.print("Verify with: [cyan]ops --version[/cyan]")
    console.print("Tab completion: [cyan]ops <TAB>[/cyan]\n")
    if editable:
        console.print(
            "[dim]Installed in editable mode -- code changes take effect immediately.[/dim]\n"
        )


def uninstall() -> None:
    """Uninstall system-operations-cli via pipx."""
    console.print("\n[bold]Uninstalling system-operations-cli via pipx...[/bold]\n")

    pipx_path = _find_pipx()
    if not pipx_path:
        raise typer.Exit(1)

    if not _is_installed_via_pipx():
        console.print(f"[yellow]{PACKAGE_NAME} is not installed via pipx.[/yellow]")
        console.print("Nothing to uninstall.")
        return

    try:
        subprocess.run([pipx_path, "uninstall", PACKAGE_NAME], check=True)
    except subprocess.CalledProcessError as err:
        console.print("\n[red]ERROR:[/red] pipx uninstall failed.")
        raise typer.Exit(1) from err

    console.print("\n[bold green]Uninstallation complete![/bold green]\n")
    console.print("The 'ops' command has been removed.")


if __name__ == "__main__":
    install()
