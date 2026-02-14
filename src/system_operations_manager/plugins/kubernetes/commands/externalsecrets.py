"""CLI commands for External Secrets Operator resources.

Provides commands for managing ExternalSecrets, SecretStores,
ClusterSecretStores, and ESO operator status via the
ExternalSecretsManager service.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.plugins.kubernetes.commands.base import (
    ForceOption,
    LabelSelectorOption,
    NamespaceOption,
    OutputOption,
    confirm_delete,
    console,
    handle_k8s_error,
)
from system_operations_manager.plugins.kubernetes.formatters import OutputFormat, get_formatter

if TYPE_CHECKING:
    from system_operations_manager.services.kubernetes.externalsecrets_manager import (
        ExternalSecretsManager,
    )

# =============================================================================
# Column Definitions
# =============================================================================

SECRET_STORE_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("provider_type", "Provider"),
    ("ready", "Ready"),
    ("message", "Message"),
    ("age", "Age"),
]

CLUSTER_SECRET_STORE_COLUMNS = [
    ("name", "Name"),
    ("provider_type", "Provider"),
    ("ready", "Ready"),
    ("message", "Message"),
    ("age", "Age"),
]

EXTERNAL_SECRET_COLUMNS = [
    ("name", "Name"),
    ("namespace", "Namespace"),
    ("store_name", "Store"),
    ("store_kind", "Store Kind"),
    ("refresh_interval", "Refresh"),
    ("data_count", "Keys"),
    ("ready", "Ready"),
    ("age", "Age"),
]


# =============================================================================
# Helpers
# =============================================================================


def _parse_labels(labels: list[str] | None) -> dict[str, str] | None:
    """Parse key=value label strings into a dict."""
    if not labels:
        return None
    result: dict[str, str] = {}
    for label in labels:
        key, sep, value = label.partition("=")
        if not sep:
            console.print(f"[red]Error:[/red] Invalid label format '{label}', expected key=value")
            raise typer.Exit(1)
        result[key] = value
    return result


def _parse_provider_config(config_str: str) -> dict[str, object]:
    """Parse a JSON provider config string into a dict."""
    try:
        config = json.loads(config_str)
        if not isinstance(config, dict):
            console.print("[red]Error:[/red] Provider config must be a JSON object")
            raise typer.Exit(1)
        return config
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON provider config: {e}")
        raise typer.Exit(1) from None


def _parse_data_refs(data_strings: list[str] | None) -> list[dict[str, object]] | None:
    """Parse JSON data ref strings into a list of dicts."""
    if not data_strings:
        return None
    refs: list[dict[str, object]] = []
    for data_str in data_strings:
        try:
            refs.append(json.loads(data_str))
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON data ref: {e}")
            raise typer.Exit(1) from None
    return refs


# =============================================================================
# Command Registration
# =============================================================================


def register_external_secrets_commands(
    app: typer.Typer,
    get_manager: Callable[[], ExternalSecretsManager],
) -> None:
    """Register External Secrets Operator CLI commands."""

    # -------------------------------------------------------------------------
    # SecretStores (namespaced)
    # -------------------------------------------------------------------------

    ss_app = typer.Typer(
        name="secret-stores",
        help="Manage External Secrets SecretStores",
        no_args_is_help=True,
    )
    app.add_typer(ss_app, name="secret-stores")

    @ss_app.command("list")
    def list_secret_stores(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List SecretStores in a namespace.

        Examples:
            ops k8s secret-stores list
            ops k8s secret-stores list -n production
            ops k8s secret-stores list -l provider=vault -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_secret_stores(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, SECRET_STORE_COLUMNS, title="Secret Stores")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ss_app.command("get")
    def get_secret_store(
        name: str = typer.Argument(help="SecretStore name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a SecretStore.

        Examples:
            ops k8s secret-stores get vault-store
            ops k8s secret-stores get vault-store -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_secret_store(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"SecretStore: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ss_app.command("create")
    def create_secret_store(
        name: str = typer.Argument(help="SecretStore name"),
        namespace: NamespaceOption = None,
        provider_config: str = typer.Option(
            ...,
            "--provider-config",
            help='Provider config as JSON (e.g. \'{"vault":{"server":"https://vault.example.com"}}\')',
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a SecretStore.

        Examples:
            ops k8s secret-stores create vault-store \\
                --provider-config '{"vault":{"server":"https://vault.example.com","path":"secret","version":"v2","auth":{"kubernetes":{"mountPath":"kubernetes","role":"my-role"}}}}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            config = _parse_provider_config(provider_config)

            resource = manager.create_secret_store(
                name,
                namespace=namespace,
                provider_config=config,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created SecretStore: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @ss_app.command("delete")
    def delete_secret_store(
        name: str = typer.Argument(help="SecretStore name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete a SecretStore.

        Examples:
            ops k8s secret-stores delete vault-store
            ops k8s secret-stores delete vault-store -n production --force
        """
        try:
            if not force and not confirm_delete("SecretStore", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_secret_store(name, namespace=namespace)
            console.print(f"[green]SecretStore '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # ClusterSecretStores (cluster-scoped)
    # -------------------------------------------------------------------------

    css_app = typer.Typer(
        name="cluster-secret-stores",
        help="Manage External Secrets ClusterSecretStores",
        no_args_is_help=True,
    )
    app.add_typer(css_app, name="cluster-secret-stores")

    @css_app.command("list")
    def list_cluster_secret_stores(
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ClusterSecretStores.

        Examples:
            ops k8s cluster-secret-stores list
            ops k8s cluster-secret-stores list -l provider=aws -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_cluster_secret_stores(label_selector=label_selector)
            formatter = get_formatter(output, console)
            formatter.format_list(
                resources,
                CLUSTER_SECRET_STORE_COLUMNS,
                title="Cluster Secret Stores",
            )
        except KubernetesError as e:
            handle_k8s_error(e)

    @css_app.command("get")
    def get_cluster_secret_store(
        name: str = typer.Argument(help="ClusterSecretStore name"),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of a ClusterSecretStore.

        Examples:
            ops k8s cluster-secret-stores get aws-store
            ops k8s cluster-secret-stores get aws-store -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_cluster_secret_store(name)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ClusterSecretStore: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @css_app.command("create")
    def create_cluster_secret_store(
        name: str = typer.Argument(help="ClusterSecretStore name"),
        provider_config: str = typer.Option(
            ...,
            "--provider-config",
            help='Provider config as JSON (e.g. \'{"aws":{"service":"SecretsManager","region":"us-east-1"}}\')',
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create a ClusterSecretStore.

        Examples:
            ops k8s cluster-secret-stores create aws-store \\
                --provider-config '{"aws":{"service":"SecretsManager","region":"us-east-1"}}'
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            config = _parse_provider_config(provider_config)

            resource = manager.create_cluster_secret_store(
                name,
                provider_config=config,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ClusterSecretStore: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @css_app.command("delete")
    def delete_cluster_secret_store(
        name: str = typer.Argument(help="ClusterSecretStore name"),
        force: ForceOption = False,
    ) -> None:
        """Delete a ClusterSecretStore.

        Examples:
            ops k8s cluster-secret-stores delete aws-store
            ops k8s cluster-secret-stores delete aws-store --force
        """
        try:
            if not force and not confirm_delete("ClusterSecretStore", name):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_cluster_secret_store(name)
            console.print(f"[green]ClusterSecretStore '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # ExternalSecrets (namespaced)
    # -------------------------------------------------------------------------

    es_app = typer.Typer(
        name="external-secrets",
        help="Manage External Secrets",
        no_args_is_help=True,
    )
    app.add_typer(es_app, name="external-secrets")

    @es_app.command("list")
    def list_external_secrets(
        namespace: NamespaceOption = None,
        label_selector: LabelSelectorOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """List ExternalSecrets in a namespace.

        Examples:
            ops k8s external-secrets list
            ops k8s external-secrets list -n production
            ops k8s external-secrets list -o json
        """
        try:
            manager = get_manager()
            resources = manager.list_external_secrets(
                namespace=namespace,
                label_selector=label_selector,
            )
            formatter = get_formatter(output, console)
            formatter.format_list(resources, EXTERNAL_SECRET_COLUMNS, title="External Secrets")
        except KubernetesError as e:
            handle_k8s_error(e)

    @es_app.command("get")
    def get_external_secret(
        name: str = typer.Argument(help="ExternalSecret name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get details of an ExternalSecret.

        Examples:
            ops k8s external-secrets get my-secret
            ops k8s external-secrets get my-secret -n production -o yaml
        """
        try:
            manager = get_manager()
            resource = manager.get_external_secret(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"ExternalSecret: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @es_app.command("create")
    def create_external_secret(
        name: str = typer.Argument(help="ExternalSecret name"),
        namespace: NamespaceOption = None,
        store: str = typer.Option(..., "--store", help="SecretStore or ClusterSecretStore name"),
        store_kind: str = typer.Option(
            "SecretStore",
            "--store-kind",
            help="Store kind: SecretStore or ClusterSecretStore",
        ),
        data: list[str] | None = typer.Option(
            None,
            "--data",
            help='Data mapping as JSON (e.g. \'{"secretKey":"password","remoteRef":{"key":"my/secret","property":"password"}}\', repeatable)',
        ),
        target_name: str | None = typer.Option(
            None,
            "--target-name",
            help="Override target K8s Secret name (defaults to ExternalSecret name)",
        ),
        refresh_interval: str = typer.Option(
            "1h", "--refresh-interval", help="Sync refresh interval (e.g. 1h, 30m, 15s)"
        ),
        label: list[str] | None = typer.Option(
            None, "--label", "-l", help="Labels (key=value, repeatable)"
        ),
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Create an ExternalSecret.

        Examples:
            ops k8s external-secrets create my-secret --store vault-store \\
                --data '{"secretKey":"password","remoteRef":{"key":"secret/data/myapp","property":"password"}}'
            ops k8s external-secrets create my-secret --store aws-store \\
                --store-kind ClusterSecretStore --refresh-interval 30m
        """
        try:
            manager = get_manager()
            labels = _parse_labels(label)
            data_refs = _parse_data_refs(data)

            resource = manager.create_external_secret(
                name,
                namespace=namespace,
                store_name=store,
                store_kind=store_kind,
                data=data_refs,
                target_name=target_name,
                refresh_interval=refresh_interval,
                labels=labels,
            )
            formatter = get_formatter(output, console)
            formatter.format_resource(resource, title=f"Created ExternalSecret: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    @es_app.command("delete")
    def delete_external_secret(
        name: str = typer.Argument(help="ExternalSecret name"),
        namespace: NamespaceOption = None,
        force: ForceOption = False,
    ) -> None:
        """Delete an ExternalSecret.

        Examples:
            ops k8s external-secrets delete my-secret
            ops k8s external-secrets delete my-secret -n production --force
        """
        try:
            if not force and not confirm_delete("ExternalSecret", name, namespace):
                raise typer.Abort()
            manager = get_manager()
            manager.delete_external_secret(name, namespace=namespace)
            console.print(f"[green]ExternalSecret '{name}' deleted[/green]")
        except KubernetesError as e:
            handle_k8s_error(e)

    @es_app.command("sync-status")
    def sync_status(
        name: str = typer.Argument(help="ExternalSecret name"),
        namespace: NamespaceOption = None,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show sync status for an ExternalSecret.

        Examples:
            ops k8s external-secrets sync-status my-secret
            ops k8s external-secrets sync-status my-secret -n production -o json
        """
        try:
            manager = get_manager()
            status = manager.get_sync_status(name, namespace=namespace)
            formatter = get_formatter(output, console)
            formatter.format_dict(status, title=f"Sync Status: {name}")
        except KubernetesError as e:
            handle_k8s_error(e)

    # -------------------------------------------------------------------------
    # ESO Operator Status
    # -------------------------------------------------------------------------

    eso_app = typer.Typer(
        name="eso",
        help="External Secrets Operator status",
        no_args_is_help=True,
    )
    app.add_typer(eso_app, name="eso")

    @eso_app.command("status")
    def eso_status(
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show External Secrets Operator status.

        Checks if ESO pods are running in the external-secrets namespace.

        Examples:
            ops k8s eso status
            ops k8s eso status -o json
        """
        try:
            manager = get_manager()
            status = manager.get_operator_status()
            formatter = get_formatter(output, console)
            formatter.format_dict(status, title="External Secrets Operator")
        except KubernetesError as e:
            handle_k8s_error(e)
