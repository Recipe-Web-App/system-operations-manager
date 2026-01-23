"""CLI commands for Kong Consumers.

This module provides commands for managing Kong Consumer entities
and their credentials:
- list: List all consumers
- get: Get consumer details
- create: Create a new consumer
- update: Update an existing consumer
- delete: Delete a consumer
- credentials list/add/delete: Manage consumer credentials
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.plugins.kong.commands.base import (
    DataPlaneOnlyOption,
    ForceOption,
    LimitOption,
    OffsetOption,
    OutputOption,
    TagsOption,
    confirm_delete,
    console,
    handle_kong_error,
    parse_config_options,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kong.consumer_manager import ConsumerManager
    from system_operations_manager.services.kong.dual_write import DualWriteService
    from system_operations_manager.services.kong.unified_query import UnifiedQueryService


# Column definitions for consumer listings
CONSUMER_COLUMNS = [
    ("username", "Username"),
    ("id", "ID"),
    ("custom_id", "Custom ID"),
    ("tags", "Tags"),
]

# Column definitions for credential listings
CREDENTIAL_COLUMNS = {
    "key-auth": [
        ("id", "ID"),
        ("key", "Key"),
        ("ttl", "TTL"),
    ],
    "basic-auth": [
        ("id", "ID"),
        ("username", "Username"),
    ],
    "hmac-auth": [
        ("id", "ID"),
        ("username", "Username"),
    ],
    "jwt": [
        ("id", "ID"),
        ("key", "Key"),
        ("algorithm", "Algorithm"),
    ],
    "oauth2": [
        ("id", "ID"),
        ("name", "Name"),
        ("client_id", "Client ID"),
    ],
}

ACL_COLUMNS = [
    ("id", "ID"),
    ("group", "Group"),
    ("tags", "Tags"),
]


def register_consumer_commands(
    app: typer.Typer,
    get_manager: Callable[[], ConsumerManager],
    get_unified_query_service: Callable[[], UnifiedQueryService | None] | None = None,
    get_dual_write_service: Callable[[], DualWriteService[Any]] | None = None,
) -> None:
    """Register consumer commands with the Kong app.

    Args:
        app: Typer app to register commands on.
        get_manager: Factory function that returns a ConsumerManager instance.
        get_unified_query_service: Optional factory that returns a UnifiedQueryService
            for querying both Gateway and Konnect.
        get_dual_write_service: Optional factory that returns a DualWriteService
            for writing to both Gateway and Konnect.
    """
    consumers_app = typer.Typer(
        name="consumers",
        help="Manage Kong Consumers and credentials",
        no_args_is_help=True,
    )

    # =========================================================================
    # Consumer CRUD Commands
    # =========================================================================

    @consumers_app.command("list")
    def list_consumers(
        output: OutputOption = OutputFormat.TABLE,
        tags: TagsOption = None,
        limit: LimitOption = None,
        offset: OffsetOption = None,
        source: Annotated[
            str | None,
            typer.Option(
                "--source",
                "-s",
                help="Filter by source: gateway, konnect (only when Konnect is configured)",
            ),
        ] = None,
        compare: Annotated[
            bool,
            typer.Option(
                "--compare",
                help="Show drift details between Gateway and Konnect",
            ),
        ] = False,
    ) -> None:
        """List all consumers.

        When Konnect is configured, shows consumers from both Gateway and Konnect
        with a Source column indicating where each consumer exists.

        Examples:
            ops kong consumers list
            ops kong consumers list --tag production
            ops kong consumers list --output json
            ops kong consumers list --source gateway
            ops kong consumers list --compare
        """
        formatter = get_formatter(output, console)

        # Try unified query first if available
        unified_service = get_unified_query_service() if get_unified_query_service else None

        if unified_service is not None:
            try:
                results = unified_service.list_consumers(tags=tags)

                # Filter by source if specified
                if source:
                    results = results.filter_by_source(source)

                formatter.format_unified_list(
                    results,
                    CONSUMER_COLUMNS,
                    title="Kong Consumers",
                    show_drift=compare,
                )
                return
            except Exception as e:
                # Fall back to gateway-only if unified query fails
                console.print(
                    f"[dim]Note: Unified query unavailable ({e}), showing gateway only[/dim]\n"
                )

        # Fall back to gateway-only query
        if source == "konnect":
            console.print(
                "[yellow]Konnect not configured. Use 'ops kong konnect login' to configure.[/yellow]"
            )
            raise typer.Exit(1)

        try:
            manager = get_manager()
            consumers, next_offset = manager.list(tags=tags, limit=limit, offset=offset)

            formatter.format_list(consumers, CONSUMER_COLUMNS, title="Kong Consumers")

            if next_offset:
                console.print(f"\n[dim]More results available. Use --offset {next_offset}[/dim]")

        except KongAPIError as e:
            handle_kong_error(e)

    @consumers_app.command("get")
    def get_consumer(
        username_or_id: Annotated[str, typer.Argument(help="Consumer username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a consumer by username or ID.

        Examples:
            ops kong consumers get my-user
            ops kong consumers get my-user --output json
        """
        try:
            manager = get_manager()
            consumer = manager.get(username_or_id)

            formatter = get_formatter(output, console)
            title = f"Consumer: {consumer.username or consumer.id}"
            formatter.format_entity(consumer, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @consumers_app.command("create")
    def create_consumer(
        username: Annotated[
            str | None,
            typer.Option("--username", "-u", help="Consumer username (unique)"),
        ] = None,
        custom_id: Annotated[
            str | None,
            typer.Option("--custom-id", "-c", help="Custom identifier (unique)"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (can be repeated)"),
        ] = None,
        data_plane_only: DataPlaneOnlyOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a new consumer.

        At least one of --username or --custom-id must be provided. By default,
        creates the consumer in both Gateway and Konnect (if configured).

        Examples:
            ops kong consumers create --username my-user
            ops kong consumers create --custom-id user-123
            ops kong consumers create --username my-user --custom-id user-123 --tag production
            ops kong consumers create --username test-user --data-plane-only
        """
        if not username and not custom_id:
            console.print("[red]Error:[/red] At least one of --username or --custom-id is required")
            raise typer.Exit(1)

        try:
            consumer = Consumer(
                username=username,
                custom_id=custom_id,
                tags=tags,
            )

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.create(consumer, data_plane_only=data_plane_only)

                formatter = get_formatter(output, console)
                console.print("[green]Consumer created successfully[/green]\n")
                title = f"Consumer: {result.gateway_result.username or result.gateway_result.id}"
                formatter.format_entity(result.gateway_result, title=title)

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("\n[green]✓ Synced to Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"\n[yellow]⚠ Konnect sync failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("\n[dim]Konnect sync skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("\n[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager = get_manager()
                created = manager.create(consumer)

                formatter = get_formatter(output, console)
                console.print("[green]Consumer created successfully[/green]\n")
                title = f"Consumer: {created.username or created.id}"
                formatter.format_entity(created, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @consumers_app.command("update")
    def update_consumer(
        username_or_id: Annotated[str, typer.Argument(help="Consumer username or ID to update")],
        username: Annotated[
            str | None,
            typer.Option("--username", "-u", help="New username"),
        ] = None,
        custom_id: Annotated[
            str | None,
            typer.Option("--custom-id", "-c", help="New custom ID"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags (replaces existing)"),
        ] = None,
        data_plane_only: DataPlaneOnlyOption = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Update an existing consumer.

        Only specified fields will be updated. By default, updates the consumer
        in both Gateway and Konnect (if configured).

        Examples:
            ops kong consumers update my-user --username new-username
            ops kong consumers update my-user --custom-id new-custom-id
            ops kong consumers update my-user --tag staging
            ops kong consumers update my-user --username test --data-plane-only
        """
        update_data: dict[str, Any] = {}
        if username is not None:
            update_data["username"] = username
        if custom_id is not None:
            update_data["custom_id"] = custom_id
        if tags is not None:
            update_data["tags"] = tags

        if not update_data:
            console.print("[yellow]No updates specified[/yellow]")
            raise typer.Exit(0)

        try:
            consumer = Consumer(**update_data)

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.update(
                    username_or_id, consumer, data_plane_only=data_plane_only
                )

                formatter = get_formatter(output, console)
                console.print("[green]Consumer updated successfully[/green]\n")
                title = f"Consumer: {result.gateway_result.username or result.gateway_result.id}"
                formatter.format_entity(result.gateway_result, title=title)

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("\n[green]✓ Synced to Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"\n[yellow]⚠ Konnect sync failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("\n[dim]Konnect sync skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("\n[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager = get_manager()
                updated = manager.update(username_or_id, consumer)

                formatter = get_formatter(output, console)
                console.print("[green]Consumer updated successfully[/green]\n")
                title = f"Consumer: {updated.username or updated.id}"
                formatter.format_entity(updated, title=title)

        except KongAPIError as e:
            handle_kong_error(e)

    @consumers_app.command("delete")
    def delete_consumer(
        username_or_id: Annotated[str, typer.Argument(help="Consumer username or ID to delete")],
        force: ForceOption = False,
        data_plane_only: DataPlaneOnlyOption = False,
    ) -> None:
        """Delete a consumer.

        This will also delete all associated credentials. By default, deletes
        from both Gateway and Konnect (if configured).

        Examples:
            ops kong consumers delete my-user
            ops kong consumers delete my-user --force
            ops kong consumers delete my-user --data-plane-only
        """
        try:
            manager = get_manager()

            # Verify consumer exists
            consumer = manager.get(username_or_id)
            display_name = consumer.username or consumer.id or username_or_id

            if not force and not confirm_delete("consumer", display_name):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            # Use dual-write service if available
            if get_dual_write_service is not None:
                dual_write = get_dual_write_service()
                result = dual_write.delete(username_or_id, data_plane_only=data_plane_only)

                console.print(f"[green]Consumer '{display_name}' deleted successfully[/green]")

                # Show Konnect sync status
                if result.is_fully_synced:
                    console.print("[green]✓ Deleted from Konnect[/green]")
                elif result.partial_success:
                    console.print(
                        f"[yellow]⚠ Konnect delete failed: {result.konnect_error}[/yellow]"
                    )
                    console.print("[dim]Run 'ops kong sync push' to retry[/dim]")
                elif result.konnect_skipped:
                    console.print("[dim]Konnect delete skipped (--data-plane-only)[/dim]")
                elif result.konnect_not_configured:
                    console.print("[dim]Konnect not configured[/dim]")
            else:
                # Fallback to gateway-only (legacy behavior)
                manager.delete(username_or_id)
                console.print(f"[green]Consumer '{display_name}' deleted successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # Credential Management Commands (nested under consumers)
    # =========================================================================

    credentials_app = typer.Typer(
        name="credentials",
        help="Manage consumer credentials",
        no_args_is_help=True,
    )

    @credentials_app.command("list")
    def list_credentials(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        credential_type: Annotated[
            str,
            typer.Option(
                "--type",
                "-t",
                help="Credential type: key-auth, basic-auth, hmac-auth, jwt, oauth2",
            ),
        ] = "key-auth",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List credentials for a consumer.

        Examples:
            ops kong consumers credentials list my-user
            ops kong consumers credentials list my-user --type jwt
            ops kong consumers credentials list my-user --type basic-auth --output json
        """
        try:
            manager = get_manager()
            credentials = manager.list_credentials(consumer, credential_type)

            columns = CREDENTIAL_COLUMNS.get(
                credential_type,
                [("id", "ID")],
            )

            formatter = get_formatter(output, console)
            formatter.format_list(
                credentials,
                columns,
                title=f"{credential_type} credentials for: {consumer}",
            )

        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KongAPIError as e:
            handle_kong_error(e)

    @credentials_app.command("add")
    def add_credential(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        credential_type: Annotated[
            str,
            typer.Option(
                "--type",
                "-t",
                help="Credential type: key-auth, basic-auth, hmac-auth, jwt, oauth2",
            ),
        ] = "key-auth",
        config: Annotated[
            list[str] | None,
            typer.Option(
                "--config",
                "-c",
                help="Credential config as key=value (can be repeated)",
            ),
        ] = None,
        config_json: Annotated[
            str | None,
            typer.Option(
                "--config-json",
                help="Credential config as JSON string",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Add a credential to a consumer.

        Examples:
            ops kong consumers credentials add my-user --type key-auth
            ops kong consumers credentials add my-user --type key-auth --config key=my-api-key
            ops kong consumers credentials add my-user --type basic-auth --config username=foo --config password=bar
            ops kong consumers credentials add my-user --type jwt --config-json '{"key": "my-key", "algorithm": "RS256"}'
        """
        # Build credential data
        data: dict[str, Any] = {}

        if config:
            data.update(parse_config_options(config))

        if config_json:
            try:
                json_data = json.loads(config_json)
                data.update(json_data)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error:[/red] Invalid JSON: {e}")
                raise typer.Exit(1) from None

        try:
            manager = get_manager()
            credential = manager.add_credential(consumer, credential_type, data)

            formatter = get_formatter(output, console)
            console.print("[green]Credential created successfully[/green]\n")
            formatter.format_entity(
                credential,
                title=f"{credential_type} credential",
            )

        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KongAPIError as e:
            handle_kong_error(e)

    @credentials_app.command("delete")
    def delete_credential(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        credential_id: Annotated[str, typer.Argument(help="Credential ID to delete")],
        credential_type: Annotated[
            str,
            typer.Option(
                "--type",
                "-t",
                help="Credential type: key-auth, basic-auth, hmac-auth, jwt, oauth2",
            ),
        ] = "key-auth",
        force: ForceOption = False,
    ) -> None:
        """Delete a credential from a consumer.

        Examples:
            ops kong consumers credentials delete my-user abc-123
            ops kong consumers credentials delete my-user abc-123 --type jwt
            ops kong consumers credentials delete my-user abc-123 --force
        """
        try:
            manager = get_manager()

            if not force and not confirm_delete(f"{credential_type} credential", credential_id):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.delete_credential(consumer, credential_type, credential_id)
            console.print(f"[green]Credential '{credential_id}' deleted successfully[/green]")

        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except KongAPIError as e:
            handle_kong_error(e)

    consumers_app.add_typer(credentials_app, name="credentials")

    # =========================================================================
    # ACL Group Commands
    # =========================================================================

    acl_app = typer.Typer(
        name="acls",
        help="Manage consumer ACL group memberships",
        no_args_is_help=True,
    )

    @acl_app.command("list")
    def list_acl_groups(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ACL groups for a consumer.

        Examples:
            ops kong consumers acls list my-user
        """
        try:
            manager = get_manager()
            groups = manager.list_acl_groups(consumer)

            formatter = get_formatter(output, console)
            formatter.format_list(
                groups,
                ACL_COLUMNS,
                title=f"ACL groups for: {consumer}",
            )

        except KongAPIError as e:
            handle_kong_error(e)

    @acl_app.command("add")
    def add_to_acl_group(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        group: Annotated[str, typer.Argument(help="ACL group name")],
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", "-t", help="Tags"),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Add a consumer to an ACL group.

        Examples:
            ops kong consumers acls add my-user admin-group
            ops kong consumers acls add my-user read-only --tag production
        """
        try:
            manager = get_manager()
            acl = manager.add_to_acl_group(consumer, group, tags)

            formatter = get_formatter(output, console)
            console.print(f"[green]Consumer added to group '{group}' successfully[/green]\n")
            formatter.format_entity(acl, title="ACL membership")

        except KongAPIError as e:
            handle_kong_error(e)

    @acl_app.command("remove")
    def remove_from_acl_group(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        acl_id: Annotated[str, typer.Argument(help="ACL entry ID to remove")],
        force: ForceOption = False,
    ) -> None:
        """Remove a consumer from an ACL group.

        Examples:
            ops kong consumers acls remove my-user abc-123
            ops kong consumers acls remove my-user abc-123 --force
        """
        try:
            manager = get_manager()

            if not force and not confirm_delete("ACL membership", acl_id):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.remove_from_acl_group(consumer, acl_id)
            console.print("[green]Consumer removed from ACL group successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    consumers_app.add_typer(acl_app, name="acls")

    app.add_typer(consumers_app, name="consumers")
