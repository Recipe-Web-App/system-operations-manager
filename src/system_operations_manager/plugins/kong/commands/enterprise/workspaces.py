"""Workspace commands for Kong Enterprise.

Provides CLI commands for managing Kong Enterprise workspaces (multi-tenancy).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.enterprise import Workspace
from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    LimitOption,
    OutputOption,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter
from system_operations_manager.services.kong.workspace_manager import WorkspaceManager

console = Console()

# Column definitions for workspace tables
WORKSPACE_COLUMNS = [
    ("name", "Name"),
    ("id", "ID"),
    ("comment", "Comment"),
]


def register_workspace_commands(
    app: typer.Typer,
    get_workspace_manager: Callable[[], WorkspaceManager],
) -> None:
    """Register workspace commands with the enterprise app.

    Args:
        app: Typer app to register commands on.
        get_workspace_manager: Factory function for WorkspaceManager.
    """
    workspaces_app = typer.Typer(
        name="workspaces",
        help="Manage Kong Enterprise workspaces (multi-tenancy)",
        no_args_is_help=True,
    )

    @workspaces_app.command("list")
    def list_workspaces(
        limit: LimitOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List all workspaces."""
        try:
            manager = get_workspace_manager()
            workspaces, _ = manager.list(limit=limit)

            if not workspaces:
                console.print("[dim]No workspaces found[/dim]")
                return

            formatter = get_formatter(output, console)
            formatter.format_list(workspaces, WORKSPACE_COLUMNS, title="Kong Workspaces")

        except KongAPIError as e:
            handle_kong_error(e)

    @workspaces_app.command("get")
    def get_workspace(
        name: Annotated[str, typer.Argument(help="Workspace name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a specific workspace."""
        try:
            manager = get_workspace_manager()
            workspace = manager.get(name)

            formatter = get_formatter(output, console)
            formatter.format_entity(workspace, title=f"Workspace: {workspace.name}")

            # Show entity counts if available
            counts = manager.get_entities_count(name)
            if counts:
                console.print()
                table = Table(title="Entity Counts", show_header=True)
                table.add_column("Entity Type")
                table.add_column("Count", justify="right")
                for entity_type, count in counts.items():
                    table.add_row(entity_type.title(), str(count))
                console.print(table)

        except KongAPIError as e:
            handle_kong_error(e)

    @workspaces_app.command("create")
    def create_workspace(
        name: Annotated[str, typer.Argument(help="Workspace name")],
        comment: Annotated[str | None, typer.Option("--comment", "-c", help="Description")] = None,
        portal: Annotated[
            bool, typer.Option("--portal/--no-portal", help="Enable Developer Portal")
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new workspace."""
        try:
            manager = get_workspace_manager()
            workspace = manager.create_with_config(name, comment=comment, portal_enabled=portal)

            console.print(f"[green]Workspace '{workspace.name}' created successfully[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(workspace, title=f"Workspace: {workspace.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @workspaces_app.command("use")
    def use_workspace(
        name: Annotated[str, typer.Argument(help="Workspace name to switch to")],
    ) -> None:
        """Switch to a different workspace context."""
        try:
            manager = get_workspace_manager()
            workspace = manager.switch_context(name)

            console.print(f"[green]Switched to workspace: {workspace.name}[/green]")
            if workspace.comment:
                console.print(f"[dim]{workspace.comment}[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @workspaces_app.command("current")
    def current_workspace(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show the current workspace context."""
        try:
            manager = get_workspace_manager()
            workspace = manager.get_current()

            console.print(f"Current workspace: [bold]{workspace.name}[/bold]")
            if workspace.comment:
                console.print(f"[dim]{workspace.comment}[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @workspaces_app.command("delete")
    def delete_workspace(
        name: Annotated[str, typer.Argument(help="Workspace name or ID")],
        force: ForceOption = False,
    ) -> None:
        """Delete a workspace."""
        try:
            manager = get_workspace_manager()

            # Get workspace first to confirm it exists
            workspace = manager.get(name)

            if not force:
                # Show entity counts as warning
                counts = manager.get_entities_count(name)
                if counts and any(v > 0 for v in counts.values()):
                    console.print("[yellow]Warning:[/yellow] This workspace contains:")
                    for entity_type, count in counts.items():
                        if count > 0:
                            console.print(f"  - {count} {entity_type}")
                    console.print()

                confirm = typer.confirm(f"Delete workspace '{workspace.name}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            manager.delete(name)
            console.print(f"[green]Workspace '{workspace.name}' deleted[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @workspaces_app.command("update")
    def update_workspace(
        name: Annotated[str, typer.Argument(help="Workspace name or ID")],
        comment: Annotated[
            str | None, typer.Option("--comment", "-c", help="New description")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update a workspace."""
        try:
            manager = get_workspace_manager()

            update_data = Workspace(name=name, comment=comment)
            workspace = manager.update(name, update_data)

            console.print(f"[green]Workspace '{workspace.name}' updated[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(workspace, title=f"Workspace: {workspace.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(workspaces_app, name="workspaces")
