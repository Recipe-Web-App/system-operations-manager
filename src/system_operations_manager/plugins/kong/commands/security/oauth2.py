"""OAuth2 authentication commands for Kong Gateway.

Provides CLI commands for configuring OAuth 2.0 authentication
using Kong's oauth2 plugin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.security.base import (
    OAUTH2_COLUMNS,
    OutputOption,
    ServiceScopeOption,
    console,
    get_formatter,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat

if TYPE_CHECKING:
    from system_operations_manager.services.kong.consumer_manager import ConsumerManager
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


def register_oauth2_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
    get_consumer_manager: Callable[[], ConsumerManager],
) -> None:
    """Register OAuth2 subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
        get_consumer_manager: Factory function that returns a ConsumerManager instance.
    """
    oauth2_app = typer.Typer(
        name="oauth2",
        help="OAuth2 authentication management",
        no_args_is_help=True,
    )

    @oauth2_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        scopes: Annotated[
            list[str] | None,
            typer.Option(
                "--scope",
                help="Available scopes (can be repeated)",
            ),
        ] = None,
        mandatory_scope: Annotated[
            bool,
            typer.Option(
                "--mandatory-scope/--optional-scope",
                help="Require scope parameter in authorization",
            ),
        ] = False,
        provision_key: Annotated[
            str | None,
            typer.Option(
                "--provision-key",
                help="Key for /oauth2/token endpoint. Auto-generated if not provided.",
            ),
        ] = None,
        token_expiration: Annotated[
            int,
            typer.Option(
                "--token-expiration",
                help="Access token TTL in seconds",
            ),
        ] = 7200,
        refresh_token_ttl: Annotated[
            int,
            typer.Option(
                "--refresh-token-ttl",
                help="Refresh token TTL in seconds (0 = no expiry)",
            ),
        ] = 1209600,
        enable_authorization_code: Annotated[
            bool,
            typer.Option(
                "--enable-authorization-code/--disable-authorization-code",
                help="Enable authorization code grant",
            ),
        ] = True,
        enable_client_credentials: Annotated[
            bool,
            typer.Option(
                "--enable-client-credentials/--disable-client-credentials",
                help="Enable client credentials grant",
            ),
        ] = False,
        enable_implicit_grant: Annotated[
            bool,
            typer.Option(
                "--enable-implicit-grant/--disable-implicit-grant",
                help="Enable implicit grant",
            ),
        ] = False,
        enable_password_grant: Annotated[
            bool,
            typer.Option(
                "--enable-password-grant/--disable-password-grant",
                help="Enable password grant (resource owner)",
            ),
        ] = False,
        accept_http_if_already_terminated: Annotated[
            bool,
            typer.Option(
                "--accept-http/--require-https",
                help="Accept HTTP if TLS terminated upstream",
            ),
        ] = False,
        anonymous: Annotated[
            str | None,
            typer.Option(
                "--anonymous",
                help="Consumer ID for anonymous access on auth failure",
            ),
        ] = None,
        global_credentials: Annotated[
            bool,
            typer.Option(
                "--global-credentials/--service-credentials",
                help="Allow credentials across services",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable OAuth2 plugin on a service.

        Configure OAuth 2.0 authentication with various grant types.

        Examples:
            ops kong security oauth2 enable --service my-api
            ops kong security oauth2 enable --service my-api --scope read --scope write --mandatory-scope
            ops kong security oauth2 enable --service my-api --enable-client-credentials --token-expiration 3600
        """
        if not service:
            console.print("[red]Error:[/red] --service is required for OAuth2 plugin")
            raise typer.Exit(1)

        # Build plugin configuration
        config: dict[str, Any] = {
            "mandatory_scope": mandatory_scope,
            "token_expiration": token_expiration,
            "refresh_token_ttl": refresh_token_ttl,
            "enable_authorization_code": enable_authorization_code,
            "enable_client_credentials": enable_client_credentials,
            "enable_implicit_grant": enable_implicit_grant,
            "enable_password_grant": enable_password_grant,
            "accept_http_if_already_terminated": accept_http_if_already_terminated,
            "global_credentials": global_credentials,
        }
        if scopes:
            config["scopes"] = scopes
        if provision_key:
            config["provision_key"] = provision_key
        if anonymous:
            config["anonymous"] = anonymous

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "oauth2",
                service=service,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]OAuth2 plugin enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="OAuth2 Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @oauth2_app.command("create-app")
    def create_app(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        name: Annotated[
            str,
            typer.Option(
                "--name",
                "-n",
                help="Application name",
            ),
        ],
        redirect_uri: Annotated[
            list[str],
            typer.Option(
                "--redirect-uri",
                "-r",
                help="Redirect URI(s) (can be repeated)",
            ),
        ],
        client_id: Annotated[
            str | None,
            typer.Option(
                "--client-id",
                help="Client ID (auto-generated if not provided)",
            ),
        ] = None,
        client_secret: Annotated[
            str | None,
            typer.Option(
                "--client-secret",
                help="Client secret (auto-generated if not provided)",
            ),
        ] = None,
        hash_secret: Annotated[
            bool,
            typer.Option(
                "--hash-secret/--no-hash-secret",
                help="Hash the client secret",
            ),
        ] = False,
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
        """Create an OAuth2 application for a consumer.

        Creates OAuth2 credentials that can be used to obtain access tokens.

        Examples:
            ops kong security oauth2 create-app my-user --name "My App" --redirect-uri "https://app.example.com/callback"
            ops kong security oauth2 create-app my-user --name "Mobile App" --redirect-uri "myapp://callback" --client-id "mobile-client"
        """
        data: dict[str, Any] = {
            "name": name,
            "redirect_uris": redirect_uri,
            "hash_secret": hash_secret,
        }
        if client_id:
            data["client_id"] = client_id
        if client_secret:
            data["client_secret"] = client_secret
        if tags:
            data["tags"] = tags

        try:
            manager = get_consumer_manager()
            credential = manager.add_credential(consumer, "oauth2", data)

            formatter = get_formatter(output, console)
            console.print("[green]OAuth2 application created successfully[/green]\n")
            formatter.format_entity(credential, title="OAuth2 Application")

            # Note about secret visibility
            if not hash_secret:
                console.print(
                    "\n[yellow]Note:[/yellow] The client_secret is shown above. "
                    "Store it securely - it won't be fully visible again."
                )

        except KongAPIError as e:
            handle_kong_error(e)

    @oauth2_app.command("list-apps")
    def list_apps(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List OAuth2 applications for a consumer.

        Examples:
            ops kong security oauth2 list-apps my-user
            ops kong security oauth2 list-apps my-user --output json
        """
        try:
            manager = get_consumer_manager()
            credentials = manager.list_credentials(consumer, "oauth2")

            formatter = get_formatter(output, console)
            formatter.format_list(
                credentials,
                OAUTH2_COLUMNS,
                title=f"OAuth2 Applications for: {consumer}",
            )

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(oauth2_app, name="oauth2")
