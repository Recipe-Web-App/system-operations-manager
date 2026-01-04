"""mTLS commands for Kong Gateway.

Provides CLI commands for configuring mutual TLS authentication
using Kong's mtls-auth plugin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

import typer

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.commands.security.base import (
    MTLS_COLUMNS,
    ForceOption,
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


# Revocation check modes
REVOCATION_CHECK_MODES = ["SKIP", "IGNORE_CA_ERROR", "STRICT"]


def register_mtls_commands(
    app: typer.Typer,
    get_plugin_manager: Callable[[], KongPluginManager],
    get_consumer_manager: Callable[[], ConsumerManager],
) -> None:
    """Register mTLS subcommands.

    Args:
        app: Typer app to register commands on.
        get_plugin_manager: Factory function that returns a KongPluginManager instance.
        get_consumer_manager: Factory function that returns a ConsumerManager instance.
    """
    mtls_app = typer.Typer(
        name="mtls",
        help="Mutual TLS authentication",
        no_args_is_help=True,
    )

    @mtls_app.command("enable")
    def enable(
        service: ServiceScopeOption = None,
        route: RouteScopeOption = None,
        ca_certificates: Annotated[
            list[str] | None,
            typer.Option(
                "--ca-certificate",
                "-c",
                help="CA certificate ID or @/path/to/file (can be repeated)",
            ),
        ] = None,
        skip_consumer_lookup: Annotated[
            bool,
            typer.Option(
                "--skip-consumer-lookup/--require-consumer",
                help="Skip consumer lookup (validate cert only)",
            ),
        ] = False,
        authenticated_group_by: Annotated[
            str | None,
            typer.Option(
                "--authenticated-group-by",
                help="Certificate field for group: CN or DN",
            ),
        ] = None,
        revocation_check_mode: Annotated[
            str,
            typer.Option(
                "--revocation-check-mode",
                help=f"CRL/OCSP check mode: {', '.join(REVOCATION_CHECK_MODES)}",
            ),
        ] = "IGNORE_CA_ERROR",
        http_timeout: Annotated[
            int | None,
            typer.Option(
                "--http-timeout",
                help="Timeout for OCSP/CRL requests in milliseconds",
            ),
        ] = None,
        cert_cache_ttl: Annotated[
            int | None,
            typer.Option(
                "--cert-cache-ttl",
                help="Cache TTL for parsed certificates in seconds",
            ),
        ] = None,
        allow_partial_chain: Annotated[
            bool,
            typer.Option(
                "--allow-partial-chain/--require-full-chain",
                help="Allow incomplete certificate chains",
            ),
        ] = False,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Enable mTLS plugin on a service or route.

        Configure mutual TLS authentication to require valid client
        certificates for accessing protected endpoints.

        Note: CA certificates should be uploaded to Kong first using
        'ops kong certificates' commands, then referenced by ID here.

        Examples:
            ops kong security mtls enable --service my-api --ca-certificate ca-cert-id
            ops kong security mtls enable --service my-api --ca-certificate ca-cert-id --skip-consumer-lookup
            ops kong security mtls enable --service my-api --ca-certificate ca-cert-id --revocation-check-mode STRICT
        """
        if not service and not route:
            console.print("[red]Error:[/red] Either --service or --route is required")
            raise typer.Exit(1)

        if revocation_check_mode not in REVOCATION_CHECK_MODES:
            console.print(
                f"[red]Error:[/red] Invalid revocation check mode. "
                f"Must be one of: {', '.join(REVOCATION_CHECK_MODES)}"
            )
            raise typer.Exit(1)

        # Build plugin configuration
        config: dict[str, Any] = {
            "skip_consumer_lookup": skip_consumer_lookup,
            "revocation_check_mode": revocation_check_mode,
            "allow_partial_chain": allow_partial_chain,
        }

        if ca_certificates:
            # Process CA certificates - could be IDs or file paths
            processed_certs = []
            for cert in ca_certificates:
                if cert.startswith("@"):
                    # It's a file path - read the content
                    # Note: In production, you'd upload this to Kong first
                    console.print(
                        "[yellow]Warning:[/yellow] File-based CA certificates should be "
                        "uploaded to Kong first. Use the certificate ID instead."
                    )
                    processed_certs.append(read_file_or_value(cert))
                else:
                    # It's an ID reference
                    processed_certs.append(cert)
            config["ca_certificates"] = processed_certs

        if authenticated_group_by:
            config["authenticated_group_by"] = authenticated_group_by
        if http_timeout is not None:
            config["http_timeout"] = http_timeout
        if cert_cache_ttl is not None:
            config["cert_cache_ttl"] = cert_cache_ttl

        try:
            manager = get_plugin_manager()
            plugin = manager.enable(
                "mtls-auth",
                service=service,
                route=route,
                config=config,
            )

            formatter = get_formatter(output, console)
            console.print("[green]mTLS plugin enabled successfully[/green]\n")
            formatter.format_entity(plugin, title="mTLS Plugin")

        except KongAPIError as e:
            handle_kong_error(e)

    @mtls_app.command("add-cert")
    def add_cert(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        subject_name: Annotated[
            str | None,
            typer.Option(
                "--subject-name",
                "-s",
                help="Certificate subject distinguished name",
            ),
        ] = None,
        ca_certificate: Annotated[
            str | None,
            typer.Option(
                "--ca-certificate",
                "-c",
                help="CA certificate ID for validation",
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
        """Add mTLS credential to a consumer.

        Associates a client certificate subject with a consumer for
        authentication purposes.

        Examples:
            ops kong security mtls add-cert my-user --subject-name "CN=client,O=MyOrg"
            ops kong security mtls add-cert my-user --subject-name "CN=app-client" --ca-certificate ca-cert-id
        """
        data: dict[str, Any] = {}
        if subject_name:
            data["subject_name"] = subject_name
        if ca_certificate:
            data["ca_certificate"] = {"id": ca_certificate}
        if tags:
            data["tags"] = tags

        try:
            manager = get_consumer_manager()
            credential = manager.add_credential(consumer, "mtls-auth", data)

            formatter = get_formatter(output, console)
            console.print("[green]mTLS credential created successfully[/green]\n")
            formatter.format_entity(credential, title="mTLS Credential")

        except KongAPIError as e:
            handle_kong_error(e)

    @mtls_app.command("list-certs")
    def list_certs(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List mTLS credentials for a consumer.

        Examples:
            ops kong security mtls list-certs my-user
            ops kong security mtls list-certs my-user --output json
        """
        try:
            manager = get_consumer_manager()
            credentials = manager.list_credentials(consumer, "mtls-auth")

            formatter = get_formatter(output, console)
            formatter.format_list(
                credentials,
                MTLS_COLUMNS,
                title=f"mTLS Credentials for: {consumer}",
            )

        except KongAPIError as e:
            handle_kong_error(e)

    @mtls_app.command("revoke-cert")
    def revoke_cert(
        consumer: Annotated[str, typer.Argument(help="Consumer username or ID")],
        cert_id: Annotated[str, typer.Argument(help="mTLS credential ID to revoke")],
        force: ForceOption = False,
    ) -> None:
        """Revoke an mTLS credential.

        Examples:
            ops kong security mtls revoke-cert my-user abc-123-cert-id
            ops kong security mtls revoke-cert my-user abc-123-cert-id --force
        """
        try:
            manager = get_consumer_manager()

            if not force and not typer.confirm(
                f"Are you sure you want to revoke mTLS credential '{cert_id}'?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

            manager.delete_credential(consumer, "mtls-auth", cert_id)
            console.print(f"[green]mTLS credential '{cert_id}' revoked successfully[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    app.add_typer(mtls_app, name="mtls")
