"""Key authentication commands for Kong Gateway.

Provides CLI commands for configuring API key authentication
using Kong's key-auth plugin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.security.base import (
    KEY_AUTH_COLUMNS,
    ForceOption,
    HideCredentialsOption,
    OutputOption,
    RouteScopeOption,
    ServiceScopeOption,
    console,
    get_formatter,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat

if TYPE_CHECKING:
    from system_operations_manager.services.kong.consumer_manager import ConsumerManager
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


def register_key_auth_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
    get_consumer_manager: Callable[[], ConsumerManager],
) -> None:
    """Register key-auth subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
        get_consumer_manager: Factory function that returns a ConsumerManager instance.
    """
    key_auth_app = typer.Typer(
        name="key-auth",
        help="Key authentication management",
        no_args_is_help=True,
    )

    @key_auth_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        key_names: Annotated[
            list[str] | None,
            typer.Option(
                "--key-name",
                "-k",
                help="Header/query param names for the API key (can be repeated)",
            ),
        ] = None,
        hide_credentials: HideCredentialsOption = False,
        key_in_header: Annotated[
            bool,
            typer.Option(
                "--key-in-header/--no-key-in-header",
                help="Accept API key in request header",
            ),
        ] = True,
        key_in_query: Annotated[
            bool,
            typer.Option(
                "--key-in-query/--no-key-in-query",
                help="Accept API key in query string",
            ),
        ] = True,
        key_in_body: Annotated[
            bool,
            typer.Option(
                "--key-in-body/--no-key-in-body",
                help="Accept API key in request body",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable key-auth plugin on a service or route.

        Configure API key authentication to require valid API keys
        for accessing protected endpoints.

        Examples:
            ops kong security key-auth enable --service my-api
            ops kong security key-auth enable --service my-api --key-name apikey --key-name x-api-key
            ops kong security key-auth enable --service my-api --hide-credentials --no-key-in-query
        """
        if not service and not route:
            console.print("[red]Error:[/red] Either --service or --route is required")
            raise typer.Exit(1)

        # Build plugin configuration
        config: dict[str, Any] = {
            "hide_credentials": hide_credentials,
            "key_in_header": key_in_header,
            "key_in_query": key_in_query,
            "key_in_body": key_in_body,
        }
        if key_names:
            config["key_names"] = key_names

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "key-auth",
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]Key-auth plugin enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="Key-Auth Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @key_auth_app.command("create-key")
    def create_key(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        key: Annotated[
            str | None,
            typer.Option(
                "--key",
                "-k",
                help="API key value (auto-generated if not provided)",
            ),
        ] = None,
        ttl: Annotated[
            int | None,
            typer.Option(
                "--ttl",
                help="Time-to-live in seconds (optional)",
            ),
        ] = None,
        tags: Annotated[
            list[str] | None,
            typer.Option(
                "--tag",
                "-t",
                help="Tags (can be repeated)",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create an API key for a consumer.

        If --key is not provided, Kong will auto-generate a secure key.

        Examples:
            ops kong security key-auth create-key my-user
            ops kong security key-auth create-key my-user --key "my-secret-api-key"
            ops kong security key-auth create-key my-user --ttl 86400 --tag production
        """
        data: dict[str, Any] = {}
        if key:
            data["key"] = key
        if ttl is not None:
            data["ttl"] = ttl
        if tags:
            data["tags"] = tags

        try:
            manager = get_consumer_manager()
            credential = manager.add_credential(consumer, "key-auth", data)

            formatter = get_formatter(output, console)
            console.print("[green]API key created successfully[/green]\n")
            formatter.format_entity(credential, title="API Key")

        except KongAPIError as e:
            handle_kong_error(e)

    @key_auth_app.command("list-keys")
    def list_keys(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List API keys for a consumer.

        Examples:
            ops kong security key-auth list-keys my-user
            ops kong security key-auth list-keys my-user --output json
        """
        try:
            manager = get_consumer_manager()
            credentials = manager.list_credentials(consumer, "key-auth")

            formatter = get_formatter(output, console)
            formatter.format_list(
                credentials,
                KEY_AUTH_COLUMNS,
                title=f"API Keys for: {consumer}",
            )

        except KongAPIError as e:
            handle_kong_error(e)

    @key_auth_app.command("revoke-key")
    def revoke_key(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        key_id: Annotated[str, typer.Argument(help="API key ID to revoke")],
        force: ForceOption = False,
    ) -> None:
        """Revoke an API key.

        Examples:
            ops kong security key-auth revoke-key my-user abc-123-key-id
            ops kong security key-auth revoke-key my-user abc-123-key-id --force
        """
        try:
            manager = get_consumer_manager()

            if not force and not typer.confirm(
                f"Are you sure you want to revoke API key '{key_id}'?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.delete_credential(consumer, "key-auth", key_id)
            console.print(f"[green]API key '{key_id}' revoked successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(key_auth_app, name="key-auth")
