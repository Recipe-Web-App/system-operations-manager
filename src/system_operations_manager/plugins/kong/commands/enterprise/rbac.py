"""RBAC commands for Kong Enterprise.

Provides CLI commands for managing Kong Enterprise Role-Based Access Control.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer
from rich.console import Console

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.enterprise import (
    RBACEndpointPermission,
    RBACRole,
    RBACUser,
)
from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    LimitOption,
    OutputOption,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter
from system_operations_manager.services.kong.rbac_manager import RBACManager

console = Console()

# Column definitions
ROLE_COLUMNS = [
    ("name", "Name"),
    ("id", "ID"),
    ("comment", "Comment"),
    ("is_default", "Default"),
]

USER_COLUMNS = [
    ("username", "Username"),
    ("id", "ID"),
    ("email", "Email"),
    ("status", "Status"),
]

PERMISSION_COLUMNS = [
    ("endpoint", "Endpoint"),
    ("actions", "Actions"),
    ("negative", "Deny"),
]


def register_rbac_commands(
    app: typer.Typer,
    get_rbac_manager: Callable[[], RBACManager],
) -> None:
    """Register RBAC commands with the enterprise app.

    Args:
        app: Typer app to register commands on.
        get_rbac_manager: Factory function for RBACManager.
    """
    rbac_app = typer.Typer(
        name="rbac",
        help="Role-Based Access Control management",
        no_args_is_help=True,
    )

    # =========================================================================
    # Roles Sub-commands
    # =========================================================================

    roles_app = typer.Typer(
        name="roles",
        help="Manage RBAC roles",
        no_args_is_help=True,
    )

    @roles_app.command("list")
    def list_roles(
        limit: LimitOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List all RBAC roles."""
        try:
            manager = get_rbac_manager()
            roles, _ = manager.list_roles(limit=limit)

            if not roles:
                console.print("[dim]No roles found[/dim]")
                return

            formatter = get_formatter(output, console)
            formatter.format_list(roles, ROLE_COLUMNS, title="RBAC Roles")

        except KongAPIError as e:
            handle_kong_error(e)

    @roles_app.command("get")
    def get_role(
        name: Annotated[str, typer.Argument(help="Role name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a specific role."""
        try:
            manager = get_rbac_manager()
            role = manager.get_role(name)

            formatter = get_formatter(output, console)
            formatter.format_entity(role, title=f"Role: {role.name}")

            # Show permissions
            permissions = manager.list_role_permissions(name)
            if permissions:
                console.print()
                console.print("[bold]Permissions:[/bold]")
                for perm in permissions:
                    actions = ", ".join(perm.actions) if perm.actions else "none"
                    prefix = "[red]DENY[/red]" if perm.negative else "[green]ALLOW[/green]"
                    console.print(f"  {prefix} {perm.endpoint}: {actions}")

        except KongAPIError as e:
            handle_kong_error(e)

    @roles_app.command("create")
    def create_role(
        name: Annotated[str, typer.Argument(help="Role name")],
        comment: Annotated[str | None, typer.Option("--comment", "-c", help="Description")] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new RBAC role."""
        try:
            manager = get_rbac_manager()
            role = RBACRole(name=name, comment=comment)
            created = manager.create_role(role)

            console.print(f"[green]Role '{created.name}' created successfully[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(created, title=f"Role: {created.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @roles_app.command("delete")
    def delete_role(
        name: Annotated[str, typer.Argument(help="Role name or ID")],
        force: ForceOption = False,
    ) -> None:
        """Delete an RBAC role."""
        try:
            manager = get_rbac_manager()
            role = manager.get_role(name)

            if not force:
                confirm = typer.confirm(f"Delete role '{role.name}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            manager.delete_role(name)
            console.print(f"[green]Role '{role.name}' deleted[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @roles_app.command("add-permission")
    def add_permission(
        role: Annotated[str, typer.Argument(help="Role name or ID")],
        endpoint: Annotated[
            str, typer.Option("--endpoint", "-e", help="API endpoint pattern (e.g., /services/*)")
        ],
        actions: Annotated[
            list[str],
            typer.Option(
                "--action", "-a", help="Action: read, create, update, delete (can repeat)"
            ),
        ],
        deny: Annotated[bool, typer.Option("--deny", help="Make this a deny permission")] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Add a permission to a role."""
        try:
            manager = get_rbac_manager()

            # Validate actions
            valid_actions = {"read", "create", "update", "delete"}
            for action in actions:
                if action not in valid_actions:
                    console.print(f"[red]Error:[/red] Invalid action '{action}'")
                    console.print(f"Valid actions: {', '.join(sorted(valid_actions))}")
                    raise typer.Exit(1)

            permission = RBACEndpointPermission(
                endpoint=endpoint,
                actions=actions,
                negative=deny,
            )
            created = manager.add_role_permission(role, permission)

            action_type = "deny" if deny else "allow"
            console.print(f"[green]Added {action_type} permission for '{endpoint}'[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(created, title="Permission")

        except KongAPIError as e:
            handle_kong_error(e)

    @roles_app.command("list-permissions")
    def list_permissions(
        role: Annotated[str, typer.Argument(help="Role name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List permissions for a role."""
        try:
            manager = get_rbac_manager()
            permissions = manager.list_role_permissions(role)

            if not permissions:
                console.print(f"[dim]No permissions found for role '{role}'[/dim]")
                return

            formatter = get_formatter(output, console)
            formatter.format_list(permissions, PERMISSION_COLUMNS, title=f"Permissions for {role}")

        except KongAPIError as e:
            handle_kong_error(e)

    rbac_app.add_typer(roles_app, name="roles")

    # =========================================================================
    # Users Sub-commands
    # =========================================================================

    users_app = typer.Typer(
        name="users",
        help="Manage RBAC admin users",
        no_args_is_help=True,
    )

    @users_app.command("list")
    def list_users(
        limit: LimitOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List all admin users."""
        try:
            manager = get_rbac_manager()
            users, _ = manager.list_users(limit=limit)

            if not users:
                console.print("[dim]No users found[/dim]")
                return

            formatter = get_formatter(output, console)
            formatter.format_list(users, USER_COLUMNS, title="RBAC Users")

        except KongAPIError as e:
            handle_kong_error(e)

    @users_app.command("get")
    def get_user(
        username: Annotated[str, typer.Argument(help="Username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a specific user."""
        try:
            manager = get_rbac_manager()
            user = manager.get_user(username)

            formatter = get_formatter(output, console)
            formatter.format_entity(user, title=f"User: {user.username}")

            # Show assigned roles
            roles = manager.list_user_roles(username)
            if roles:
                console.print()
                console.print("[bold]Assigned Roles:[/bold]")
                for role in roles:
                    console.print(f"  - {role.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @users_app.command("create")
    def create_user(
        username: Annotated[str, typer.Argument(help="Username")],
        email: Annotated[str | None, typer.Option("--email", "-e", help="Email address")] = None,
        comment: Annotated[str | None, typer.Option("--comment", "-c", help="Description")] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new admin user."""
        try:
            manager = get_rbac_manager()
            user = RBACUser(username=username, email=email, comment=comment)
            created = manager.create_user(user)

            console.print(f"[green]User '{created.username}' created successfully[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(created, title=f"User: {created.username}")

        except KongAPIError as e:
            handle_kong_error(e)

    @users_app.command("delete")
    def delete_user(
        username: Annotated[str, typer.Argument(help="Username or ID")],
        force: ForceOption = False,
    ) -> None:
        """Delete an admin user."""
        try:
            manager = get_rbac_manager()
            user = manager.get_user(username)

            if not force:
                confirm = typer.confirm(f"Delete user '{user.username}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            manager.delete_user(username)
            console.print(f"[green]User '{user.username}' deleted[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @users_app.command("assign-role")
    def assign_role(
        username: Annotated[str, typer.Argument(help="Username or ID")],
        role: Annotated[str, typer.Argument(help="Role name or ID to assign")],
    ) -> None:
        """Assign a role to a user."""
        try:
            manager = get_rbac_manager()
            manager.assign_role(username, role)
            console.print(f"[green]Role '{role}' assigned to user '{username}'[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @users_app.command("revoke-role")
    def revoke_role(
        username: Annotated[str, typer.Argument(help="Username or ID")],
        role: Annotated[str, typer.Argument(help="Role name or ID to revoke")],
        force: ForceOption = False,
    ) -> None:
        """Revoke a role from a user."""
        try:
            manager = get_rbac_manager()

            if not force:
                confirm = typer.confirm(f"Revoke role '{role}' from user '{username}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            manager.revoke_role(username, role)
            console.print(f"[green]Role '{role}' revoked from user '{username}'[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    @users_app.command("list-roles")
    def list_user_roles(
        username: Annotated[str, typer.Argument(help="Username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List roles assigned to a user."""
        try:
            manager = get_rbac_manager()
            roles = manager.list_user_roles(username)

            if not roles:
                console.print(f"[dim]No roles assigned to user '{username}'[/dim]")
                return

            formatter = get_formatter(output, console)
            formatter.format_list(roles, ROLE_COLUMNS, title=f"Roles for {username}")

        except KongAPIError as e:
            handle_kong_error(e)

    rbac_app.add_typer(users_app, name="users")

    app.add_typer(rbac_app, name="rbac")
