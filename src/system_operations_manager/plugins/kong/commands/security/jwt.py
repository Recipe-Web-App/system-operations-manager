"""JWT authentication commands for Kong Gateway.

Provides CLI commands for configuring JSON Web Token authentication
using Kong's jwt plugin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.security.base import (
    JWT_COLUMNS,
    OutputOption,
    RouteScopeOption,
    ServiceScopeOption,
    console,
    get_formatter,
    handle_kong_error,
    read_file_or_value,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat

if TYPE_CHECKING:
    from system_operations_manager.services.kong.consumer_manager import ConsumerManager
    from system_operations_manager.services.kong.plugin_manager import KongPluginManager


# Supported JWT algorithms
JWT_ALGORITHMS = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]


def register_jwt_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
    get_consumer_manager: Callable[[], ConsumerManager],
) -> None:
    """Register JWT subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
        get_consumer_manager: Factory function that returns a ConsumerManager instance.
    """
    jwt_app = typer.Typer(
        name="jwt",
        help="JWT authentication management",
        no_args_is_help=True,
    )

    @jwt_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        claims_to_verify: Annotated[
            list[str] | None,
            typer.Option(
                "--claim",
                "-c",
                help="Claims to verify: exp, nbf (can be repeated)",
            ),
        ] = None,
        key_claim_name: Annotated[
            str,
            typer.Option(
                "--key-claim",
                help="Claim containing the key identifier",
            ),
        ] = "iss",
        secret_is_base64: Annotated[
            bool,
            typer.Option(
                "--secret-is-base64/--secret-is-plain",
                help="Whether secrets are base64 encoded",
            ),
        ] = False,
        run_on_preflight: Annotated[
            bool,
            typer.Option(
                "--run-on-preflight/--skip-preflight",
                help="Validate JWT on preflight OPTIONS requests",
            ),
        ] = True,
        header_names: Annotated[
            list[str] | None,
            typer.Option(
                "--header-name",
                help="Header names to check for JWT (can be repeated)",
            ),
        ] = None,
        uri_param_names: Annotated[
            list[str] | None,
            typer.Option(
                "--uri-param",
                help="URI param names to check for JWT (can be repeated)",
            ),
        ] = None,
        cookie_names: Annotated[
            list[str] | None,
            typer.Option(
                "--cookie-name",
                help="Cookie names to check for JWT (can be repeated)",
            ),
        ] = None,
        maximum_expiration: Annotated[
            int | None,
            typer.Option(
                "--max-expiration",
                help="Maximum allowed expiration time in seconds",
            ),
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable JWT plugin on a service or route.

        Configure JWT authentication to validate JSON Web Tokens
        for accessing protected endpoints.

        Examples:
            ops kong security jwt enable --service my-api
            ops kong security jwt enable --service my-api --claim exp --claim nbf
            ops kong security jwt enable --service my-api --key-claim iss --max-expiration 86400
        """
        if not service and not route:
            console.print("[red]Error:[/red] Either --service or --route is required")
            raise typer.Exit(1)

        # Build plugin configuration
        config: dict[str, Any] = {
            "key_claim_name": key_claim_name,
            "secret_is_base64": secret_is_base64,
            "run_on_preflight": run_on_preflight,
        }
        if claims_to_verify:
            config["claims_to_verify"] = claims_to_verify
        if header_names:
            config["header_names"] = header_names
        if uri_param_names:
            config["uri_param_names"] = uri_param_names
        if cookie_names:
            config["cookie_names"] = cookie_names
        if maximum_expiration is not None:
            config["maximum_expiration"] = maximum_expiration

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "jwt",
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]JWT plugin enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="JWT Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @jwt_app.command("add-credential")
    def add_credential(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        key: Annotated[
            str | None,
            typer.Option(
                "--key",
                "-k",
                help="JWT key (iss claim value). Auto-generated if not provided.",
            ),
        ] = None,
        algorithm: Annotated[
            str,
            typer.Option(
                "--algorithm",
                "-a",
                help=f"Signing algorithm: {', '.join(JWT_ALGORITHMS)}",
            ),
        ] = "HS256",
        secret: Annotated[
            str | None,
            typer.Option(
                "--secret",
                "-s",
                help="Secret for HS* algorithms",
            ),
        ] = None,
        rsa_public_key: Annotated[
            str | None,
            typer.Option(
                "--rsa-public-key",
                help="RSA public key for RS*/ES* algorithms. Use @/path/to/file for file.",
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
        """Add JWT credential to a consumer.

        For HS* algorithms (HS256, HS384, HS512), provide --secret.
        For RS*/ES* algorithms (RS256, RS384, RS512, ES256, ES384, ES512),
        provide --rsa-public-key.

        Examples:
            ops kong security jwt add-credential my-user --algorithm HS256 --secret "my-secret"
            ops kong security jwt add-credential my-user --key "jwt-issuer" --algorithm RS256 --rsa-public-key @/path/to/public.pem
            ops kong security jwt add-credential my-user --algorithm HS256 --secret "my-secret" --tag production
        """
        if algorithm not in JWT_ALGORITHMS:
            console.print(
                f"[red]Error:[/red] Invalid algorithm. Must be one of: {', '.join(JWT_ALGORITHMS)}"
            )
            raise typer.Exit(1)

        # Validate algorithm/key requirements
        is_symmetric = algorithm.startswith("HS")
        if is_symmetric and not secret:
            console.print(f"[red]Error:[/red] --secret is required for {algorithm} algorithm")
            raise typer.Exit(1)
        if not is_symmetric and not rsa_public_key:
            console.print(
                f"[red]Error:[/red] --rsa-public-key is required for {algorithm} algorithm"
            )
            raise typer.Exit(1)

        data: dict[str, Any] = {"algorithm": algorithm}
        if key:
            data["key"] = key
        if secret:
            data["secret"] = secret
        if rsa_public_key:
            data["rsa_public_key"] = read_file_or_value(rsa_public_key)
        if tags:
            data["tags"] = tags

        try:
            manager = get_consumer_manager()
            credential = manager.add_credential(consumer, "jwt", data)

            formatter = get_formatter(output, console)
            console.print("[green]JWT credential created successfully[/green]\n")
            formatter.format_entity(credential, title="JWT Credential")

        except KongAPIError as e:
            handle_kong_error(e)

    @jwt_app.command("list-credentials")
    def list_credentials(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List JWT credentials for a consumer.

        Examples:
            ops kong security jwt list-credentials my-user
            ops kong security jwt list-credentials my-user --output json
        """
        try:
            manager = get_consumer_manager()
            credentials = manager.list_credentials(consumer, "jwt")

            formatter = get_formatter(output, console)
            formatter.format_list(
                credentials,
                JWT_COLUMNS,
                title=f"JWT Credentials for: {consumer}",
            )

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(jwt_app, name="jwt")
