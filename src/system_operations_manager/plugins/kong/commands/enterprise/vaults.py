"""Vault commands for Kong Enterprise.

Provides CLI commands for managing Kong Enterprise secret vaults.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer
from rich.console import Console

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.enterprise import (
    AWSSecretsConfig,
    AzureVaultConfig,
    EnvVaultConfig,
    GCPSecretsConfig,
    HashiCorpVaultConfig,
)
from system_operations_manager.plugins.kong.commands.base import (
    ForceOption,
    LimitOption,
    OutputOption,
    handle_kong_error,
)
from system_operations_manager.plugins.kong.formatters import OutputFormat, get_formatter
from system_operations_manager.services.kong.vault_manager import VaultManager

console = Console()

# Column definitions
VAULT_COLUMNS = [
    ("name", "Name"),
    ("prefix", "Prefix"),
    ("description", "Description"),
]


def register_vault_commands(
    app: typer.Typer,
    get_vault_manager: Callable[[], VaultManager],
) -> None:
    """Register vault commands with the enterprise app.

    Args:
        app: Typer app to register commands on.
        get_vault_manager: Factory function for VaultManager.
    """
    vaults_app = typer.Typer(
        name="vaults",
        help="Secret vault management",
        no_args_is_help=True,
    )

    @vaults_app.command("list")
    def list_vaults(
        limit: LimitOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List all configured vaults."""
        try:
            manager = get_vault_manager()
            vaults, _ = manager.list(limit=limit)

            if not vaults:
                console.print("[dim]No vaults configured[/dim]")
                return

            # Add vault type to display
            for vault in vaults:
                vault_type = manager.get_vault_type(vault)
                # Store type in config for display
                vault.config["_type"] = vault_type

            formatter = get_formatter(output, console)
            formatter.format_list(vaults, VAULT_COLUMNS, title="Kong Vaults")

        except KongAPIError as e:
            handle_kong_error(e)

    @vaults_app.command("get")
    def get_vault(
        name: Annotated[str, typer.Argument(help="Vault name or ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a specific vault."""
        try:
            manager = get_vault_manager()
            vault = manager.get(name)
            vault_type = manager.get_vault_type(vault)

            formatter = get_formatter(output, console)
            formatter.format_entity(vault, title=f"Vault: {vault.name} ({vault_type})")

            # Show usage hint
            console.print()
            console.print("[bold]Usage:[/bold]")
            console.print(f"  Reference secrets using: {{vault://{vault.prefix}/path/to/secret}}")

        except KongAPIError as e:
            handle_kong_error(e)

    @vaults_app.command("delete")
    def delete_vault(
        name: Annotated[str, typer.Argument(help="Vault name or ID")],
        force: ForceOption = False,
    ) -> None:
        """Delete a vault configuration."""
        try:
            manager = get_vault_manager()
            vault = manager.get(name)

            if not force:
                console.print("[yellow]Warning:[/yellow] Deleting this vault may break")
                console.print("plugins that reference secrets from it.")
                confirm = typer.confirm(f"Delete vault '{vault.name}'?")
                if not confirm:
                    console.print("[dim]Cancelled[/dim]")
                    raise typer.Exit(0)

            manager.delete(name)
            console.print(f"[green]Vault '{vault.name}' deleted[/green]")

        except KongAPIError as e:
            handle_kong_error(e)

    # =========================================================================
    # Configure Sub-commands
    # =========================================================================

    configure_app = typer.Typer(
        name="configure",
        help="Configure vault integrations",
        no_args_is_help=True,
    )

    @configure_app.command("hcv")
    def configure_hcv(
        name: Annotated[str, typer.Argument(help="Vault name")],
        host: Annotated[str, typer.Option("--host", "-h", help="Vault server hostname")],
        port: Annotated[int, typer.Option("--port", "-p", help="Vault server port")] = 8200,
        protocol: Annotated[
            str, typer.Option("--protocol", help="Protocol (http/https)")
        ] = "https",
        mount: Annotated[
            str, typer.Option("--mount", "-m", help="Secret engine mount path")
        ] = "secret",
        kv_version: Annotated[str, typer.Option("--kv", help="KV engine version (v1/v2)")] = "v2",
        token: Annotated[str | None, typer.Option("--token", "-t", help="Auth token")] = None,
        namespace: Annotated[
            str | None, typer.Option("--namespace", "-n", help="Vault namespace")
        ] = None,
        prefix: Annotated[str | None, typer.Option("--prefix", help="Custom vault prefix")] = None,
        description: Annotated[
            str | None, typer.Option("--description", "-d", help="Description")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Configure HashiCorp Vault integration."""
        try:
            manager = get_vault_manager()

            config = HashiCorpVaultConfig(
                host=host,
                port=port,
                protocol=protocol,  # type: ignore[arg-type]
                mount=mount,
                kv=kv_version,  # type: ignore[arg-type]
                token=token,
                namespace=namespace,
            )

            vault = manager.configure_hcv(name, config, prefix=prefix, description=description)

            console.print(f"[green]HashiCorp Vault '{vault.name}' configured[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(vault, title=f"Vault: {vault.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @configure_app.command("aws")
    def configure_aws(
        name: Annotated[str, typer.Argument(help="Vault name")],
        region: Annotated[str, typer.Option("--region", "-r", help="AWS region")],
        endpoint_url: Annotated[
            str | None, typer.Option("--endpoint-url", help="Custom endpoint URL")
        ] = None,
        role_arn: Annotated[
            str | None, typer.Option("--role-arn", help="IAM role ARN to assume")
        ] = None,
        prefix: Annotated[str | None, typer.Option("--prefix", help="Custom vault prefix")] = None,
        description: Annotated[
            str | None, typer.Option("--description", "-d", help="Description")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Configure AWS Secrets Manager integration."""
        try:
            manager = get_vault_manager()

            config = AWSSecretsConfig(
                region=region,
                endpoint_url=endpoint_url,
                role_arn=role_arn,
            )

            vault = manager.configure_aws(name, config, prefix=prefix, description=description)

            console.print(f"[green]AWS Secrets Manager vault '{vault.name}' configured[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(vault, title=f"Vault: {vault.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @configure_app.command("gcp")
    def configure_gcp(
        name: Annotated[str, typer.Argument(help="Vault name")],
        project_id: Annotated[str, typer.Option("--project-id", "-p", help="GCP project ID")],
        prefix: Annotated[str | None, typer.Option("--prefix", help="Custom vault prefix")] = None,
        description: Annotated[
            str | None, typer.Option("--description", "-d", help="Description")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Configure GCP Secret Manager integration."""
        try:
            manager = get_vault_manager()

            config = GCPSecretsConfig(project_id=project_id)

            vault = manager.configure_gcp(name, config, prefix=prefix, description=description)

            console.print(f"[green]GCP Secret Manager vault '{vault.name}' configured[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(vault, title=f"Vault: {vault.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @configure_app.command("azure")
    def configure_azure(
        name: Annotated[str, typer.Argument(help="Vault name")],
        vault_uri: Annotated[str, typer.Option("--vault-uri", "-u", help="Azure Key Vault URI")],
        client_id: Annotated[
            str | None, typer.Option("--client-id", help="Azure AD app ID")
        ] = None,
        tenant_id: Annotated[
            str | None, typer.Option("--tenant-id", help="Azure AD tenant ID")
        ] = None,
        prefix: Annotated[str | None, typer.Option("--prefix", help="Custom vault prefix")] = None,
        description: Annotated[
            str | None, typer.Option("--description", "-d", help="Description")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Configure Azure Key Vault integration."""
        try:
            manager = get_vault_manager()

            config = AzureVaultConfig(
                vault_uri=vault_uri,
                client_id=client_id,
                tenant_id=tenant_id,
            )

            vault = manager.configure_azure(name, config, prefix=prefix, description=description)

            console.print(f"[green]Azure Key Vault '{vault.name}' configured[/green]")
            formatter = get_formatter(output, console)
            formatter.format_entity(vault, title=f"Vault: {vault.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    @configure_app.command("env")
    def configure_env(
        name: Annotated[str, typer.Argument(help="Vault name")],
        env_prefix: Annotated[
            str, typer.Option("--env-prefix", "-e", help="Environment variable prefix")
        ] = "KONG_",
        prefix: Annotated[str | None, typer.Option("--prefix", help="Custom vault prefix")] = None,
        description: Annotated[
            str | None, typer.Option("--description", "-d", help="Description")
        ] = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Configure environment variable vault."""
        try:
            manager = get_vault_manager()

            config = EnvVaultConfig(prefix=env_prefix)

            vault = manager.configure_env(name, config, prefix=prefix, description=description)

            console.print(f"[green]Environment vault '{vault.name}' configured[/green]")
            console.print(
                f"[dim]Secrets will be read from env vars with prefix: {env_prefix}[/dim]"
            )
            formatter = get_formatter(output, console)
            formatter.format_entity(vault, title=f"Vault: {vault.name}")

        except KongAPIError as e:
            handle_kong_error(e)

    vaults_app.add_typer(configure_app, name="configure")

    app.add_typer(vaults_app, name="vaults")
