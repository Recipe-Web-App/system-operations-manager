"""Developer Portal commands for Kong Enterprise.

Provides CLI commands for managing Kong Enterprise Developer Portal.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    LimitOption,
    OutputOption,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter
from system_operations_manager.services.kong.portal_manager import PortalManager

console = Console()

# Column definitions
SPEC_COLUMNS = [
    ("name", "Name"),
    ("path", "Path"),
]

DEVELOPER_COLUMNS = [
    ("email", "Email"),
    ("id", "ID"),
    ("status", "Status"),
]


def register_portal_commands(
    app: typer.Typer,
    get_portal_manager: Callable[[], PortalManager],
) -> None:
    """Register portal commands with the enterprise app.

    Args:
        app: Typer app to register commands on.
        get_portal_manager: Factory function for PortalManager.
    """
    portal_app = typer.Typer(
        name="portal",
        help="Developer Portal management",
        no_args_is_help=True,
    )

    @portal_app.command("status")
    def portal_status() -> None:
        """Show Developer Portal status."""
        try:
            manager = get_portal_manager()
            status = manager.get_status()

            table = Table(title="Developer Portal Status", show_header=False)
            table.add_column("Property", style="bold")
            table.add_column("Value")

            enabled_str = "[green]Enabled[/green]" if status.enabled else "[dim]Disabled[/dim]"
            table.add_row("Status", enabled_str)

            if status.portal_gui_host:
                table.add_row("Portal URL", status.portal_gui_host)
            if status.portal_api_uri:
                table.add_row("API URI", status.portal_api_uri)
            if status.portal_auth:
                table.add_row("Authentication", status.portal_auth)

            auto_approve = "[green]Yes[/green]" if status.portal_auto_approve else "[dim]No[/dim]"
            table.add_row("Auto-Approve", auto_approve)

            console.print(table)

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # Specs Sub-commands
    # =========================================================================

    specs_app = typer.Typer(
        name="specs",
        help="Manage API specifications",
        no_args_is_help=True,
    )

    @specs_app.command("list")
    def list_specs(
        limit: LimitOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List published API specifications."""
        try:
            manager = get_portal_manager()
            specs, _ = manager.list_specs(limit=limit)

            if not specs:
                console.print("[dim]No specifications published[/dim]")
                return

            formatter = get_formatter(output, console)
            formatter.format_list(specs, SPEC_COLUMNS, title="API Specifications")

        except KongAPIError as e:
            handle_kong_error(e)

    @specs_app.command("get")
    def get_spec(
        path: Annotated[str, typer.Argument(help="Specification path")],
        output: OutputOption = OutputFormat.TABLE,
        show_contents: Annotated[
            bool, typer.Option("--contents", "-c", help="Show spec contents")
        ] = False,
    ) -> None:
        """Get details of a specification."""
        try:
            manager = get_portal_manager()
            spec = manager.get_spec(path)

            formatter = get_formatter(output, console)
            formatter.format_entity(spec, title=f"Specification: {spec.name}")

            if show_contents and spec.contents:
                console.print()
                console.print("[bold]Contents:[/bold]")
                console.print(spec.contents[:2000])  # Truncate for display
                if len(spec.contents) > 2000:
                    console.print("[dim]... (truncated)[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @specs_app.command("publish")
    def publish_spec(
        file: Annotated[Path, typer.Argument(help="OpenAPI/Swagger spec file (YAML or JSON)")],
        name: Annotated[
            str | None, typer.Option("--name", "-n", help="Spec name (default: filename)")
        ] = None,
        path: Annotated[
            str | None, typer.Option("--path", "-p", help="Custom path in portal")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Publish an API specification to the portal."""
        try:
            if not file.exists():
                console.print(f"[red]Error:[/red] File not found: {file}")
                raise typer.Exit(1)

            contents = file.read_text()
            spec_name = name or file.stem

            manager = get_portal_manager()
            spec = manager.publish_spec(spec_name, contents, path=path)

            console.print(f"[green]Specification '{spec.name}' published[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(spec, title=f"Specification: {spec.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @specs_app.command("update")
    def update_spec(
        path: Annotated[str, typer.Argument(help="Specification path in portal")],
        file: Annotated[Path, typer.Argument(help="Updated spec file")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update an existing specification."""
        try:
            if not file.exists():
                console.print(f"[red]Error:[/red] File not found: {file}")
                raise typer.Exit(1)

            contents = file.read_text()

            manager = get_portal_manager()
            spec = manager.update_spec(path, contents)

            console.print("[green]Specification updated[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(spec, title=f"Specification: {spec.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @specs_app.command("delete")
    def delete_spec(
        path: Annotated[str, typer.Argument(help="Specification path")],
        force: ForceOption = False,
    ) -> None:
        """Delete a specification from the portal."""
        try:
            manager = get_portal_manager()

            if not force:
                confirm = typer.confirm(f"Delete specification at '{path}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            manager.delete_spec(path)
            console.print("[green]Specification deleted[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    portal_app.add_typer(specs_app, name="specs")

    # =========================================================================
    # Developers Sub-commands
    # =========================================================================

    developers_app = typer.Typer(
        name="developers",
        help="Manage registered developers",
        no_args_is_help=True,
    )

    @developers_app.command("list")
    def list_developers(
        status: Annotated[
            str | None,
            typer.Option(
                "--status", "-s", help="Filter by status (approved, pending, rejected, revoked)"
            ),
        ] = None,
        limit: LimitOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List registered developers."""
        try:
            manager = get_portal_manager()
            developers, _ = manager.list_developers(status=status, limit=limit)

            if not developers:
                console.print("[dim]No developers found[/dim]")
                return

            formatter = get_formatter(output, console)
            formatter.format_list(developers, DEVELOPER_COLUMNS, title="Developers")

        except KongAPIError as e:
            handle_kong_error(e)

    @developers_app.command("get")
    def get_developer(
        email: Annotated[str, typer.Argument(help="Developer email or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a developer."""
        try:
            manager = get_portal_manager()
            developer = manager.get_developer(email)

            formatter = get_formatter(output, console)
            formatter.format_entity(developer, title=f"Developer: {developer.email}")

        except KongAPIError as e:
            handle_kong_error(e)

    @developers_app.command("approve")
    def approve_developer(
        email: Annotated[str, typer.Argument(help="Developer email or ID")],
    ) -> None:
        """Approve a pending developer."""
        try:
            manager = get_portal_manager()
            developer = manager.approve_developer(email)
            console.print(f"[green]Developer '{developer.email}' approved[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @developers_app.command("reject")
    def reject_developer(
        email: Annotated[str, typer.Argument(help="Developer email or ID")],
        force: ForceOption = False,
    ) -> None:
        """Reject a pending developer."""
        try:
            manager = get_portal_manager()

            if not force:
                confirm = typer.confirm(f"Reject developer '{email}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            developer = manager.reject_developer(email)
            console.print(f"[yellow]Developer '{developer.email}' rejected[/yellow]")

        except KongAPIError as e:
            handle_kong_error(e)

    @developers_app.command("revoke")
    def revoke_developer(
        email: Annotated[str, typer.Argument(help="Developer email or ID")],
        force: ForceOption = False,
    ) -> None:
        """Revoke access for an approved developer."""
        try:
            manager = get_portal_manager()

            if not force:
                confirm = typer.confirm(f"Revoke developer '{email}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            developer = manager.revoke_developer(email)
            console.print(f"[yellow]Developer '{developer.email}' access revoked[/yellow]")

        except KongAPIError as e:
            handle_kong_error(e)

    @developers_app.command("delete")
    def delete_developer(
        email: Annotated[str, typer.Argument(help="Developer email or ID")],
        force: ForceOption = False,
    ) -> None:
        """Delete a developer."""
        try:
            manager = get_portal_manager()

            if not force:
                confirm = typer.confirm(f"Delete developer '{email}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            manager.delete_developer(email)
            console.print("[green]Developer deleted[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    portal_app.add_typer(developers_app, name="developers")

    app.add_typer(portal_app, name="portal")
